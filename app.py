from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import datetime
import csv
import random
import pandas as pd
import cloudinary
import cloudinary.uploader
from flask_mail import Mail, Message

# --- Authentication Imports ---
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId

# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()

# --- Database Imports ---
from pymongo import MongoClient

# --- AI Model Specific Imports (for image classification) ---
from PIL import Image
# We will import torch and transformers lazily/safely below to prevent app crashes
# if they are not installed or have version conflicts.

# --- Groq API Specific Imports ---
from groq import Groq

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'uploads'
KNOWLEDGE_BASE_DIR = 'knowledge_base'

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# MongoDB Configuration
import certifi
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "Bioscout"

try:
    mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = mongo_client[DB_NAME]
    
    # Simple connectivity test
    print("Testing MongoDB connection...")
    db.command('ping')
    
    observations_collection = db["observations"]
    users_collection = db['users']
    print(f"Connected to MongoDB at {MONGO_URI} (Database: {DB_NAME})")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    db = None
    observations_collection = None
    users_collection = None

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key_here") # Required for session management

# --- Email Configuration ---
app.config['MAIL_SERVER'] = os.environ.get("EMAIL_HOST")
app.config['MAIL_PORT'] = int(os.environ.get("EMAIL_PORT", 587))
app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_HOST_USER")
app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_HOST_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get("EMAIL_FROM_NAME"), os.environ.get("EMAIL_HOST_USER"))

# Handle Port 465 (SSL) vs Port 587 (TLS) automatically
if app.config.get('MAIL_PORT') == 465:
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USE_TLS'] = False
else:
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USE_TLS'] = True

mail = Mail(app)

# --- Authentication Setup ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirect to login page if unauthorized

class User(UserMixin):
    def __init__(self, user_id, username, email):
        self.id = str(user_id)
        self.username = username
        self.email = email

    @staticmethod
    def get(user_id):
        if users_collection is None:
            return None
        user_data = users_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data['_id'], user_data['username'], user_data['email'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Configure Groq API Key ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY environment variable not set. "
          "AI Q&A functionality (general questions) will be limited or unavailable. "
          "Please set it for full functionality.")
    groq_client = None
else:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("Groq AI configured successfully.")
    except Exception as e:
        print(f"Error configuring Groq AI: {e}")
        groq_client = None

# --- Global AI Model Loading (for image classification) ---
processor = None
model = None
torch_lib = None # renamed to avoid conflict
AI_MODEL_NAME = "microsoft/resnet-50"
AI_CACHE_DIR = "./model_cache"  # Local cache directory

def get_ai_model():
    """Lazily load the AI model only when needed to save memory on startup."""
    global processor, model, torch_lib
    if model is not None and processor is not None:
        return processor, model, torch_lib
    
    try:
        print("Loading AI image classification model (lazy)...")
        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification
        
        torch_lib = torch
        os.makedirs(AI_CACHE_DIR, exist_ok=True)
        
        processor = AutoImageProcessor.from_pretrained(AI_MODEL_NAME, cache_dir=AI_CACHE_DIR)
        model = AutoModelForImageClassification.from_pretrained(AI_MODEL_NAME, cache_dir=AI_CACHE_DIR)
        print("AI image classification model loaded successfully!")
        return processor, model, torch_lib
    except Exception as e:
        print(f"Error loading AI image classification model: {e}")
        return None, None, None

# --- Knowledge Base / RAG Logic ---
import re
import math

knowledge_base_content = {}   # filename -> full text (kept for backward compat)
knowledge_base_chunks = []    # list of {"source": filename, "text": chunk, "text_lower": chunk.lower()}

# ── Comprehensive synonym / taxonomy map ──
# Maps common query terms → list of alternate forms the user or KB might use.
# Checked bi-directionally: query terms expand into these, AND these map back.
SYNONYM_MAP = {
    # Mammals
    "leopard":    ["leopard", "panthera pardus", "panther", "big cat", "wild cat", "common leopard"],
    "pangolin":   ["pangolin", "manis crassicaudata", "scaly anteater", "indian pangolin"],
    "macaque":    ["macaque", "rhesus macaque", "macaca mulatta", "monkey", "monkeys", "bandar"],
    "fox":        ["fox", "red fox", "vulpes vulpes"],
    "porcupine":  ["porcupine", "hystrix indica", "indian porcupine"],
    "boar":       ["boar", "wild boar", "sus scrofa", "pig"],
    "jackal":     ["jackal", "golden jackal", "canis aureus"],
    "mongoose":   ["mongoose", "indian grey mongoose", "herpestes edwardsii"],
    "civet":      ["civet", "palm civet", "viverridae"],
    "deer":       ["deer", "barking deer", "muntjac", "muntiacus"],
    # Birds
    "eagle":      ["eagle", "serpent eagle", "steppe eagle", "crested serpent eagle", "aquila nipalensis", "spilornis cheela", "raptor"],
    "pheasant":   ["pheasant", "khalij pheasant", "lophura leucomelanos"],
    "flycatcher": ["flycatcher", "paradise flycatcher", "terpsiphone paradisi"],
    "bulbul":     ["bulbul", "yellow-vented bulbul", "pycnonotus"],
    "kite":       ["kite", "black kite", "milvus migrans"],
    "crow":       ["crow", "house crow", "corvus splendens"],
    "myna":       ["myna", "common myna", "acridotheres tristis"],
    "parakeet":   ["parakeet", "rose-ringed parakeet", "psittacula krameri"],
    "oriole":     ["oriole", "golden oriole", "oriolus oriolus"],
    "falcon":     ["falcon", "peregrine falcon", "falco peregrinus"],
    "francolin":  ["francolin", "grey francolin", "francolinus pondicerianus"],
    "bird":       ["bird", "birds", "avian", "avifauna", "birdwatching", "birding"],
    "monal":      ["monal", "himalayan monal", "lophophorus impejanus"],
    # Reptiles
    "cobra":      ["cobra", "indian cobra", "naja naja", "snake", "venomous snake"],
    "viper":      ["viper", "russell's viper", "daboia russelii", "russell viper"],
    "monitor":    ["monitor", "monitor lizard", "varanus bengalensis"],
    "skink":      ["skink", "common skink", "mabuya macularia"],
    "snake":      ["snake", "snakes", "serpent", "cobra", "viper", "rat snake"],
    "lizard":     ["lizard", "lizards", "gecko", "skink", "monitor lizard"],
    "reptile":    ["reptile", "reptiles", "snake", "lizard", "turtle"],
    # Plants
    "pine":       ["pine", "chir pine", "pinus roxburghii"],
    "phulai":     ["phulai", "acacia modesta", "acacia"],
    "olive":      ["olive", "wild olive", "olea ferruginea", "kahu"],
    "sanatha":    ["sanatha", "dodonaea viscosa", "dodonaea"],
    "lantana":    ["lantana", "lantana camara", "invasive"],
    "plant":      ["plant", "plants", "flora", "tree", "shrub", "vegetation", "flower"],
    "tree":       ["tree", "trees", "pine", "phulai", "olive", "acacia"],
    # Locations
    "margalla":   ["margalla", "margalla hills", "mhnp", "margalla hills national park", "margalla ridge"],
    "islamabad":  ["islamabad", "capital territory", "capital city", "isb"],
    "trail 3":    ["trail 3", "trail three", "trail-3"],
    "trail 5":    ["trail 5", "trail five", "trail-5"],
    "trail 6":    ["trail 6", "trail six", "trail-6"],
    "daman-e-koh":["daman-e-koh", "daman e koh", "damaneekoh", "viewpoint"],
    "pir sohawa": ["pir sohawa", "pirsohawa", "pir sohawa road"],
    "rawal lake":  ["rawal lake", "rawal dam", "rawallake"],
    "faisal mosque":["faisal mosque", "faisal masjid"],
    "saidpur":    ["saidpur", "saidpur village"],
    # Topics
    "conservation":["conservation", "conservation efforts", "protect", "endangered", "threatened", "iwmb", "wwf"],
    "endangered":  ["endangered", "critically endangered", "threatened", "near threatened", "iucn", "conservation status"],
    "migration":   ["migration", "migratory", "migrant", "seasonal"],
    "nocturnal":   ["nocturnal", "night", "nighttime", "after dark"],
    "habitat":     ["habitat", "ecosystem", "environment", "forest", "scrubland"],
    "sighting":    ["sighting", "sightings", "spotted", "seen", "observed", "last seen", "recent"],
    "mammal":      ["mammal", "mammals", "fauna", "animal", "animals", "wildlife"],
}

# Build a reverse lookup: token → set of canonical keys
_REVERSE_SYNONYM = {}
for canonical, variants in SYNONYM_MAP.items():
    for v in variants:
        for token in v.lower().split():
            _REVERSE_SYNONYM.setdefault(token, set()).add(canonical)

STOP_WORDS = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'in', 'on', 'at', 'of', 'for', 'to', 'and', 'or', 'but', 'not', 'no',
    'do', 'does', 'did', 'has', 'have', 'had', 'will', 'would', 'shall',
    'should', 'may', 'might', 'must', 'can', 'could',
    'i', 'me', 'my', 'you', 'your', 'he', 'she', 'it', 'we', 'they',
    'this', 'that', 'these', 'those', 'there', 'here',
    'what', 'where', 'when', 'how', 'who', 'why', 'which',
    'about', 'with', 'from', 'by', 'up', 'out', 'if', 'as', 'so',
    'very', 'just', 'also', 'any', 'some', 'all', 'more', 'most',
    'tell', 'give', 'know', 'find', 'show', 'please', 'thank', 'thanks',
})


def load_knowledge_base():
    """Loads all text files from the knowledge_base directory into memory AND chunks them."""
    global knowledge_base_content, knowledge_base_chunks
    knowledge_base_content = {}
    knowledge_base_chunks = []

    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"Warning: Knowledge base directory '{KNOWLEDGE_BASE_DIR}' not found.")
        return

    for filename in os.listdir(KNOWLEDGE_BASE_DIR):
        if filename.endswith(".txt") and not filename.endswith(".bak"):
            filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                knowledge_base_content[filename] = text
                print(f"Loaded knowledge base file: {filename}")

                # ── Chunk by markdown sections (## headings) ──
                sections = re.split(r'\n(?=## )', text)
                for sec in sections:
                    sec = sec.strip()
                    if len(sec) < 20:       # skip tiny fragments
                        continue
                    knowledge_base_chunks.append({
                        "source": filename,
                        "text": sec,
                        "text_lower": sec.lower(),
                    })
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    print(f"Knowledge base loaded: {len(knowledge_base_content)} files → {len(knowledge_base_chunks)} chunks")


# Initial load on startup
load_knowledge_base()


def expand_query_keywords(query):
    """
    Extract meaningful keywords from a query, expand them via the synonym map,
    and return (primary_keywords, expanded_keywords).
    primary_keywords  = the user's actual cleaned tokens  (for scoring weight)
    expanded_keywords = additional synonym terms           (for broader recall)
    """
    tokens = re.findall(r"[a-z0-9'-]+", query.lower())
    primary = set()
    expanded = set()

    for tok in tokens:
        if tok in STOP_WORDS or len(tok) < 2:
            continue
        primary.add(tok)

        # Direct match in synonym map
        if tok in SYNONYM_MAP:
            for syn in SYNONYM_MAP[tok]:
                for st in syn.lower().split():
                    expanded.add(st)

        # Reverse lookup  (e.g. "pardus" → "leopard" group)
        if tok in _REVERSE_SYNONYM:
            for canonical in _REVERSE_SYNONYM[tok]:
                for syn in SYNONYM_MAP[canonical]:
                    for st in syn.lower().split():
                        expanded.add(st)

    # Also check bigrams  ("trail 5", "pir sohawa", "wild olive", etc.)
    lowered = query.lower()
    for canonical, variants in SYNONYM_MAP.items():
        for phrase in variants:
            if len(phrase.split()) > 1 and phrase in lowered:
                primary.add(canonical)
                for syn in SYNONYM_MAP[canonical]:
                    for st in syn.lower().split():
                        expanded.add(st)

    expanded -= primary   # don't double-count
    expanded -= STOP_WORDS
    return primary, expanded


def retrieve_relevant_context(query):
    """
    Chunk-level retrieval with TF-IDF-inspired scoring.
    Returns top chunks as a concatenated string for the LLM prompt.
    """
    if not knowledge_base_chunks:
        return ""

    primary, expanded = expand_query_keywords(query)
    if not primary and not expanded:
        return ""

    scored = []
    for chunk in knowledge_base_chunks:
        cl = chunk["text_lower"]
        score = 0.0

        # Primary keywords score 3× per occurrence
        for kw in primary:
            count = cl.count(kw)
            if count > 0:
                score += 3.0 * math.log2(1 + count)

        # Expanded synonyms score 1× per occurrence
        for kw in expanded:
            count = cl.count(kw)
            if count > 0:
                score += 1.0 * math.log2(1 + count)

        # Bonus: chunk from a file whose name matches a primary keyword
        fname = chunk["source"].lower()
        for kw in primary:
            if kw in fname:
                score += 4.0

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top 6 chunks (more granular → fits token budget better)
    top = scored[:6]

    parts = []
    seen_text = set()
    for sc, ch in top:
        # De-duplicate near-identical content
        sig = ch["text"][:80]
        if sig in seen_text:
            continue
        seen_text.add(sig)
        parts.append(f"[Source: {ch['source']}]\n{ch['text']}\n")

    return "\n".join(parts)


# --- Synonym Helper Function (kept for backward compat, now uses SYNONYM_MAP) ---
def get_synonyms(term):
    """Return a list of synonyms for the given term."""
    return SYNONYM_MAP.get(term.lower(), [term.lower()])

# --- Nature-image validation keywords ---
NATURE_KEYWORDS = frozenset({
    'animal', 'bird', 'fish', 'insect', 'reptile', 'amphibian', 'mammal',
    'snake', 'lizard', 'turtle', 'frog', 'toad', 'salamander',
    'eagle', 'hawk', 'falcon', 'owl', 'parrot', 'sparrow', 'crow',
    'robin', 'pigeon', 'dove', 'heron', 'pelican', 'flamingo', 'penguin',
    'duck', 'goose', 'swan', 'stork', 'vulture', 'kite', 'woodpecker',
    'hummingbird', 'peacock', 'pheasant', 'quail', 'crane', 'albatross',
    'dog', 'cat', 'horse', 'cow', 'sheep', 'goat', 'pig', 'deer',
    'bear', 'wolf', 'fox', 'rabbit', 'squirrel', 'mouse', 'rat',
    'elephant', 'giraffe', 'zebra', 'lion', 'tiger', 'leopard',
    'cheetah', 'panther', 'jaguar', 'monkey', 'gorilla', 'chimpanzee',
    'orangutan', 'panda', 'koala', 'kangaroo', 'camel', 'buffalo',
    'rhinoceros', 'hippopotamus', 'whale', 'dolphin', 'shark', 'seal',
    'otter', 'beaver', 'porcupine', 'hedgehog', 'bat', 'mongoose',
    'badger', 'raccoon', 'skunk', 'weasel', 'mink', 'ferret',
    'tree', 'plant', 'flower', 'forest', 'leaf', 'grass', 'bush',
    'shrub', 'vine', 'fern', 'moss', 'mushroom', 'fungus', 'lichen',
    'coral', 'reef', 'seaweed', 'algae', 'cactus', 'succulent',
    'butterfly', 'moth', 'bee', 'wasp', 'ant', 'beetle', 'dragonfly',
    'grasshopper', 'cricket', 'caterpillar', 'ladybug', 'spider',
    'scorpion', 'crab', 'lobster', 'shrimp', 'snail', 'slug', 'worm',
    'jellyfish', 'octopus', 'starfish', 'sea', 'ocean', 'river',
    'lake', 'mountain', 'valley', 'meadow', 'prairie', 'savanna',
    'jungle', 'rainforest', 'wetland', 'marsh', 'swamp', 'pond',
    'landscape', 'nature', 'wildlife', 'wilderness', 'garden', 'park',
    'trail', 'cliff', 'waterfall', 'stream', 'creek', 'hill',
    'macaque', 'langur', 'monal', 'jackal', 'civet', 'boar',
    'pangolin', 'monitor', 'skink', 'cobra', 'viper', 'python',
    'chameleon', 'iguana', 'gecko', 'newt', 'crocodile', 'alligator',
})


def is_nature_image(predicted_species_str):
    """Check if AI predictions contain any nature-related keywords."""
    if not predicted_species_str:
        return False
    pred_lower = predicted_species_str.lower()
    return any(kw in pred_lower for kw in NATURE_KEYWORDS)

# --- Groq Helper Function for General Biodiversity Questions ---
def query_groq_for_islamabad_biodiversity(question):
    """
    Queries Groq's language model for general biodiversity information,
    specifically focusing on animals in Islamabad.
    """
    if not groq_client:
        return "I'm sorry, the AI assistant (Groq) is not configured. Please ensure GROQ_API_KEY is set."

    try:
        # 1. Retrieve relevant context from our customized Knowledge Base
        relevant_context = retrieve_relevant_context(question)
        
        # 2. Construct the system prompt
        system_instructions = (
            "You are an expert AI assistant for 'BioScout', an application focused on the biodiversity of Islamabad and the Margalla Hills. "
            "Your goal is to answer user questions about local flora, fauna, and conservation efforts. "
            "If the retrieved context below contains the answer, prioritize it. "
            "If the context is not sufficient, use your general knowledge about Islamabad's ecosystem. "
            "If the question is completely unrelated to nature or Islamabad, politely decline to answer."
        )

        if relevant_context:
            system_instructions += f"\n\n--- RELEVANT CONTEXT FROM KNOWLEDGE BASE ---\n{relevant_context}\n--------------------------------------------"

        # Create the system prompt and user message
        messages = [
            {
                "role": "system",
                "content": system_instructions
            },
            {
                "role": "user",
                "content": question
            }
        ]

        # Make the API call to Groq
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",  # Updated to use a currently supported model
            temperature=0.7,
            max_tokens=1000
        )

        return chat_completion.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Groq API Error: {e}")
        return f"I'm sorry, I encountered an error communicating with the AI. ({e}). Please try again later."

def send_welcome_email(user_email, username):
    try:
        msg = Message("Welcome to BioScout!", recipients=[user_email])
        msg.body = f"Hello {username},\n\nWelcome to BioScout! We are excited to have you on board. Start exploring and documenting the biodiversity of Islamabad.\n\nBest Regards,\nThe BioScout Team"
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #2ecc71;">Welcome to BioScout!</h2>
            <p>Hello <strong>{username}</strong>,</p>
            <p>Welcome to BioScout! We are excited to have you on board.</p>
            <p>Start exploring and documenting the biodiversity of Islamabad.</p>
            <br>
            <p>Best Regards,</p>
            <p><strong>The BioScout Team</strong></p>
        </div>
        """
        mail.send(msg)
        print(f"Welcome email sent to {user_email}")
    except Exception as e:
        print(f"Error sending welcome email: {e}")

def send_otp_email(user_email, otp_code):
    """Send OTP verification code to user's email."""
    try:
        msg = Message("BioScout - Email Verification Code", recipients=[user_email])
        msg.body = f"Your BioScout verification code is: {otp_code}\n\nThis code expires in 5 minutes."
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; color: #333; max-width: 400px; margin: auto;">
            <h2 style="color: #2ecc71;">BioScout Verification</h2>
            <p>Your verification code is:</p>
            <div style="font-size: 2rem; font-weight: bold; letter-spacing: 8px; color: #2ecc71; 
                        background: #f0f0f0; padding: 15px; border-radius: 10px; text-align: center;">
                {otp_code}
            </div>
            <p style="margin-top: 15px; color: #999;">This code expires in 5 minutes.</p>
        </div>
        """
        mail.send(msg)
        print(f"OTP sent to {user_email}")
        return True
    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False

# --- Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            if users_collection is None:
                flash('Database connection error. Please try again later.', 'error')
                return redirect(url_for('signup'))
                
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            if not username or not email or not password:
                flash('Please fill out all fields.', 'error')
                return redirect(url_for('signup'))

            if users_collection.find_one({"email": email}):
                flash('Email already exists. Please login instead.', 'error')
                return redirect(url_for('signup'))

            # ── Password validation ──
            pw_errors = []
            if len(password) < 8:
                pw_errors.append('at least 8 characters')
            if not re.search(r'[A-Z]', password):
                pw_errors.append('one uppercase letter')
            if not re.search(r'[a-z]', password):
                pw_errors.append('one lowercase letter')
            if not re.search(r'[0-9]', password):
                pw_errors.append('one digit')
            if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
                pw_errors.append('one special character')
            if pw_errors:
                flash('Password must contain: ' + ', '.join(pw_errors) + '.', 'error')
                return redirect(url_for('signup'))

            # Generate OTP and store pending signup in session
            otp_code = str(random.randint(100000, 999999))
            session['pending_signup'] = {
                'username': username,
                'email': email,
                'password': password,
                'otp': otp_code,
                'created_at': datetime.datetime.now().isoformat()
            }

            if send_otp_email(email, otp_code):
                flash('A verification code has been sent to your email.', 'success')
                return redirect(url_for('verify_otp'))
            else:
                flash('Failed to send verification email. Please try again.', 'error')
                return redirect(url_for('signup'))

        except Exception as e:
            print(f"Error during signup: {e}")
            import traceback
            traceback.print_exc()
            flash('An unexpected error occurred during signup. Please try again.', 'error')
            return redirect(url_for('signup'))
    
    return render_template('login.html', mode='signup')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    pending = session.get('pending_signup')
    if not pending:
        flash('No pending signup. Please sign up first.', 'error')
        return redirect(url_for('signup'))

    if request.method == 'POST':
        try:
            entered_otp = request.form.get('otp', '').strip()
            
            # Check OTP expiry (5 minutes)
            created_at = datetime.datetime.fromisoformat(pending['created_at'])
            if (datetime.datetime.now() - created_at).total_seconds() > 300:
                session.pop('pending_signup', None)
                flash('Verification code has expired. Please sign up again.', 'error')
                return redirect(url_for('signup'))

            if entered_otp == pending['otp']:
                # OTP verified — create the account
                hashed_password = bcrypt.generate_password_hash(pending['password']).decode('utf-8')
                user_data = {
                    "username": pending['username'],
                    "email": pending['email'],
                    "password": hashed_password,
                    "email_verified": True,
                    "created_at": datetime.datetime.now()
                }
                users_collection.insert_one(user_data)
                
                # Send Welcome Email
                send_welcome_email(pending['email'], pending['username'])
                session.pop('pending_signup', None)
                
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Invalid verification code. Please try again.', 'error')
                return redirect(url_for('verify_otp'))
        except Exception as e:
            print(f"Error during OTP verification: {e}")
            import traceback
            traceback.print_exc()
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('signup'))

    return render_template('verify_otp.html', email=pending['email'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            if users_collection is None:
                flash('Database connection error. Please try again later.', 'error')
                return redirect(url_for('login'))

            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                flash('Please fill out all fields.', 'error')
                return redirect(url_for('login'))

            user_data = users_collection.find_one({"email": email})

            if user_data and bcrypt.check_password_hash(user_data['password'], password):
                user = User(user_data['_id'], user_data['username'], user_data['email'])
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('landing'))
            else:
                flash('Login Unsuccessful. Please check email and password.', 'error')
                return redirect(url_for('login'))
        except Exception as e:
            print(f"Error during login: {e}")
            import traceback
            traceback.print_exc()
            flash('An unexpected error occurred during login. Please try again.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html', mode='login')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- Flask Routes ---

@app.route('/landing')
@login_required
def landing():
    """Scrollytelling landing page shown after login."""
    return render_template('landing.html')

@app.route('/')
def serve_form():
    """Serves the main observation form page."""
    return render_template('index.html')

@app.route('/observations')
def view_observations():
    """Reads and displays stored biodiversity observations with filtering from MongoDB."""
    
    # Get filters from query parameters
    # Note: request.args returns '' for missing keys, so .get(key, '') is redundant but safe
    filter_species = request.args.get('species', '').strip() # Preserve case for display
    filter_species_lower = filter_species.lower()
    
    filter_location = request.args.get('location', '').strip()
    filter_location_lower = filter_location.lower()
    
    filter_date_start = request.args.get('start_date', '')
    filter_date_end = request.args.get('end_date', '')

    query = {}

    # 1. Species Filter (Case-insensitive regex search)
    if filter_species:
        query["$or"] = [
            {"species_name": {"$regex": filter_species, "$options": "i"}},
            {"common_name": {"$regex": filter_species, "$options": "i"}}
        ]

    # 2. Location Filter (Case-insensitive regex search)
    if filter_location:
         query["location"] = {"$regex": filter_location, "$options": "i"}

    # 3. Date Range Filter
    # MongoDB stores dates as strings in YYYY-MM-DD format (from HTML5 input type=date)
    # String comparison works for ISO dates: "2023-01-01" < "2023-01-02"
    if filter_date_start or filter_date_end:
        date_query = {}
        if filter_date_start:
            date_query["$gte"] = filter_date_start
        if filter_date_end:
            date_query["$lte"] = filter_date_end
        
        if date_query:
            query["date_observed"] = date_query

    observations = []
    try:
        # Query MongoDB
        cursor = observations_collection.find(query)
        observations = list(cursor)
        
    except Exception as e:
        print(f"Error querying MongoDB: {e}")
        # Return empty list on error
        pass

    # Pass current filter values back to template to repopulate the form
    return render_template('observations.html', 
                           observations=observations,
                           filter_species=filter_species, 
                           filter_location=filter_location,
                           filter_date_start=filter_date_start,
                           filter_date_end=filter_date_end,
                           page_title="All Observations")

@app.route('/my_observations')
@login_required
def my_observations():
    """Reads and displays stored biodiversity observations for the current user."""
    
    # Get filters from query parameters
    filter_species = request.args.get('species', '').strip()
    filter_location = request.args.get('location', '').strip()
    filter_date_start = request.args.get('start_date', '')
    filter_date_end = request.args.get('end_date', '')

    # Base query: Only show current user's observations
    query = {"user_id": current_user.id}

    # 1. Species Filter (Case-insensitive regex search)
    if filter_species:
        # Use $and if we need to combine with user_id query which is already in 'query'
        # But 'query' is a dict, so we can just add keys.
        # However, $or and top-level user_id might conflict if not careful.
        # MongoDB: { user_id: 123, $or: [...] } is valid.
        query["$or"] = [
            {"species_name": {"$regex": filter_species, "$options": "i"}},
            {"common_name": {"$regex": filter_species, "$options": "i"}}
        ]

    # 2. Location Filter
    if filter_location:
         query["location"] = {"$regex": filter_location, "$options": "i"}

    # 3. Date Range Filter
    if filter_date_start or filter_date_end:
        date_query = {}
        if filter_date_start:
            date_query["$gte"] = filter_date_start
        if filter_date_end:
            date_query["$lte"] = filter_date_end
        
        if date_query:
            query["date_observed"] = date_query

    observations = []
    try:
        # Query MongoDB
        cursor = observations_collection.find(query)
        observations = list(cursor)
        
    except Exception as e:
        print(f"Error querying MongoDB: {e}")
        pass

    return render_template('observations.html', 
                           observations=observations,
                           filter_species=filter_species, 
                           filter_location=filter_location,
                           filter_date_start=filter_date_start,
                           filter_date_end=filter_date_end,
                           page_title="My Observations")

@app.route('/test')
def test():
    """A simple test endpoint to verify the server is running."""
    return "Server is running correctly!"

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handles the submission of a new biodiversity observation."""
    try:
        print("Upload endpoint hit!")

        species_name = request.form.get('species', '').strip()
        common_name = request.form.get('common_name', '').strip()
        date_observed = request.form.get('date', '')
        location = request.form.get('location', '').strip()
        notes = request.form.get('notes', '').strip()
        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()
        city_raw = request.form.get('city', '').strip()
        city_custom = request.form.get('city_custom', '').strip()
        city = city_custom if city_raw == 'Other' else city_raw

        print(f"Form data: {species_name}, {date_observed}, {location}")

        observation_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

        predicted_species = None
        image_relative_path = None

        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            filename = secure_filename(file.filename)
            timestamp_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_filename = f"{timestamp_file}_{filename}"
            image_path_absolute = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
            file.save(image_path_absolute)
            image_relative_path = saved_filename

            print(f"File saved at {image_path_absolute}")
            
            # --- Upload to Cloudinary ---
            try:
                print("Uploading to Cloudinary...")
                upload_result = cloudinary.uploader.upload(image_path_absolute)
                image_relative_path = upload_result['secure_url'] # Use Secure URL
                print(f"Uploaded to Cloudinary: {image_relative_path}")
            except Exception as cloud_err:
                print(f"Cloudinary upload failed: {cloud_err}")
                # Fallback to local path if upload fails
                # Keep image_relative_path as saved_filename

            # --- AI Image Classification Logic ---
            try:
                # Use the lazy loader to get the model only when a user uploads
                curr_processor, curr_model, curr_torch = get_ai_model()

                if curr_model and curr_processor:
                    image = Image.open(image_path_absolute).convert('RGB')
                    inputs = curr_processor(images=image, return_tensors="pt")
                    outputs = curr_model(**inputs)
                    logits = outputs.logits

                    # Use curr_torch (lazy loaded) for processing
                    probabilities = curr_torch.nn.functional.softmax(logits, dim=1)[0]
                    top5_prob, top5_indices = curr_torch.topk(probabilities, 5)
                    predicted_species_list = []
                    for i in range(top5_indices.size(0)):
                        label = curr_model.config.id2label[top5_indices[i].item()]
                        prob = top5_prob[i].item() * 100
                        predicted_species_list.append(f"{label} ({prob:.2f}%)")

                    predicted_species = "; ".join(predicted_species_list)
                    print(f"Top 5 AI predictions: {predicted_species}")

                    # ── Nature-image validation ──
                    if not is_nature_image(predicted_species):
                        return jsonify({
                            'success': False,
                            'message': '⚠️ This image does not appear to contain wildlife. Please upload a clear photo of an animal, plant, or natural landscape and try again.'
                        }), 400
                else:
                    predicted_species = "Cheetah (Demo Prediction - AI Model Not Loaded)"
            except Exception as e:
                print(f"Image classification error: {e}")
                predicted_species = "AI Prediction Failed (Error during classification)"
        else:
            predicted_species = "No image provided for prediction"

        if not species_name and predicted_species and "Demo Prediction" not in predicted_species and "AI Prediction Failed" not in predicted_species and "No image provided" not in predicted_species:
            if ";" in predicted_species:
                species_name = predicted_species.split(';')[0].split('(')[0].strip()
            else:
                species_name = predicted_species.split('(')[0].strip()
        elif not species_name:
            species_name = "Unknown Species"

        if not common_name:
            common_name = species_name

            # --- Save to MongoDB ---
        try:
            observation_data = {
                "user_id": current_user.id,
                "username": current_user.username,
                "observation_id": observation_id,
                "species_name": species_name,
                "common_name": common_name,
                "date_observed": date_observed,
                "location": location,
                "city": city,
                "latitude": float(latitude) if latitude else None,
                "longitude": float(longitude) if longitude else None,
                "image_path": image_relative_path, # URL if Cloudinary succeeded, local filename if failed
                "notes": notes,
                "predicted_species": predicted_species,
                "timestamp": datetime.datetime.now()
            }
            inserted_result = observations_collection.insert_one(observation_data)
            print(f"Observation ID {observation_id} saved to MongoDB. Object ID: {inserted_result.inserted_id}")
            
        except Exception as db_err:
             print(f"Error saving to MongoDB: {db_err}")
             # Optionally fall back to CSV if DB fails? For now, we'll just log it.

        return jsonify({
            'success': True,
            'message': 'Observation recorded successfully',
            'predicted_species': predicted_species
        })

    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error processing observation: {str(e)}'
        }), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serves uploaded image files from the UPLOAD_FOLDER."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/sighting-locations')
def sighting_locations():
    """Return lat/lng + species for all observations that have coordinates."""
    spots = []
    try:
        if observations_collection is not None:
            cursor = observations_collection.find(
                {},
                {"latitude": 1, "longitude": 1, "species_name": 1, "predicted_species": 1, "location": 1, "city": 1, "date_observed": 1, "_id": 0}
            )
            for doc in cursor:
                spots.append({
                    "lat": doc.get("latitude"),
                    "lng": doc.get("longitude"),
                    "species": doc.get("species_name", "Unknown"),
                    "predicted_species": doc.get("predicted_species", "Unknown"),
                    "location": doc.get("location", ""),
                    "city": doc.get("city", ""),
                    "date": doc.get("date_observed", "")
                })
    except Exception as e:
        print(f"Error fetching sighting locations: {e}")
    return jsonify(spots)


@app.route('/api/observation-stats')
def observation_stats():
    """Return aggregation stats: species counts, location counts, total."""
    stats = {"total": 0, "species": [], "locations": []}
    try:
        if observations_collection is not None:
            stats["total"] = observations_collection.count_documents({})
            # Top species
            species_agg = observations_collection.aggregate([
                {"$group": {"_id": "$species_name", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 15}
            ])
            stats["species"] = [{"name": s["_id"], "count": s["count"]} for s in species_agg if s["_id"]]
            # Top locations
            loc_agg = observations_collection.aggregate([
                {"$group": {"_id": "$location", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ])
            stats["locations"] = [{"name": l["_id"], "count": l["count"]} for l in loc_agg if l["_id"]]
    except Exception as e:
        print(f"Error fetching observation stats: {e}")
    return jsonify(stats)


@app.route('/qa')
def serve_qa_page():
    """Serves the Q&A system page."""
    return render_template('qa.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.json
        if not data:
            return jsonify({"answer": "No question received"}), 400

        question = data.get('question', '').strip()
        if not question:
            return jsonify({"answer": "Empty question received"}), 400

        print(f"\n{'='*60}")
        print(f"Q&A REQUEST: '{question}'")

        # ── Step 1: Extract & expand keywords ──
        primary_kw, expanded_kw = expand_query_keywords(question)
        all_keywords = primary_kw | expanded_kw
        print(f"  Primary keywords : {primary_kw}")
        print(f"  Expanded synonyms: {expanded_kw}")

        # ── Step 2: Query MongoDB for relevant observations ──
        db_observations = []
        db_context = ""
        if observations_collection is not None and all_keywords:
            try:
                # Build regex from ALL keywords (primary + expanded) for maximum recall
                search_terms = list(all_keywords)
                # Also include multi-word phrases from primary
                question_lower = question.lower()
                for canonical, variants in SYNONYM_MAP.items():
                    for phrase in variants:
                        if len(phrase.split()) > 1 and phrase in question_lower:
                            search_terms.append(phrase)

                regex_pattern = "|".join(re.escape(t) for t in search_terms if len(t) > 1)
                if regex_pattern:
                    pipeline_query = {
                        "$or": [
                            {"species_name":      {"$regex": regex_pattern, "$options": "i"}},
                            {"predicted_species":  {"$regex": regex_pattern, "$options": "i"}},
                            {"location":           {"$regex": regex_pattern, "$options": "i"}},
                            {"notes":              {"$regex": regex_pattern, "$options": "i"}},
                            {"category":           {"$regex": regex_pattern, "$options": "i"}},
                        ]
                    }
                    db_observations = list(
                        observations_collection.find(pipeline_query)
                        .sort("date_observed", -1)
                        .limit(8)  # up from 3 → 8 for richer context
                    )
                    print(f"  MongoDB matches  : {len(db_observations)} observations")

                    if db_observations:
                        db_context = "\n## Live Observation Database (user-submitted sightings)\n"
                        for i, obs in enumerate(db_observations, 1):
                            db_context += (
                                f"{i}. **{obs.get('species_name', 'Unknown')}** "
                                f"— {obs.get('location', 'Unknown location')} "
                                f"on {obs.get('date_observed', 'unknown date')}"
                            )
                            pred = obs.get('predicted_species')
                            if pred:
                                db_context += f" | AI Prediction: {pred}"
                            notes = obs.get('notes', '')
                            if notes:
                                db_context += f" | Notes: {notes}"
                            db_context += "\n"

            except Exception as e:
                print(f"  MongoDB query error: {e}")

        # ── Step 3: Aggregation stats for big-picture context ──
        total_observations = 0
        agg_context = ""
        try:
            if observations_collection is not None:
                total_observations = observations_collection.count_documents({})
                # Species counts
                species_agg = list(observations_collection.aggregate([
                    {"$group": {"_id": "$species_name", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 15}
                ]))
                # Location counts
                loc_agg = list(observations_collection.aggregate([
                    {"$group": {"_id": "$location", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]))
                if species_agg or loc_agg:
                    agg_context = "\n## Database Aggregate Statistics\n"
                    if species_agg:
                        agg_context += "**Species recorded (top 15):** "
                        agg_context += ", ".join(f"{s['_id']} ({s['count']})"
                                                   for s in species_agg if s['_id']) + "\n"
                    if loc_agg:
                        agg_context += "**Locations (top 10):** "
                        agg_context += ", ".join(f"{l['_id']} ({l['count']})"
                                                   for l in loc_agg if l['_id']) + "\n"
        except Exception:
            pass

        # ── Step 4: Retrieve relevant KB chunks ──
        kb_context = retrieve_relevant_context(question)
        print(f"  KB context length: {len(kb_context)} chars")

        # ── Step 5: Build full context & system prompt ──
        full_context = ""
        if kb_context:
            full_context += "## Knowledge Base (curated expert data)\n" + kb_context + "\n"
        if agg_context:
            full_context += agg_context + "\n"
        if db_context:
            full_context += db_context + "\n"

        system_prompt = f"""You are **BioScout AI**, a friendly and knowledgeable expert on the biodiversity of **Islamabad and the Margalla Hills National Park (MHNP)**.

## Your Data Sources
You have access to two authoritative sources that you must use to answer questions:

1. **Knowledge Base** — Curated expert information about local species, habitats, and conservation.
2. **Live Observation Database** — Real user-submitted wildlife sightings with species, location, date, and notes. Currently contains **{total_observations}** observations.

## Context
{full_context if full_context else "(No matching context found for this query.)"}

## Instructions
- **Always check if the context above contains the answer FIRST** before using general knowledge.
- When the context contains matching observations from the Live Database, cite them specifically (species, location, date).
- If multiple database records match, summarize the pattern (e.g., "There have been 3 sightings of X near Y since Z").
- For questions about "recent sightings", "has anyone seen", or "last spotted", the Live Database is your primary source.
- If the context doesn't contain relevant info, you may use general knowledge but clearly state: "Based on general knowledge (not from our database)..."
- Use markdown formatting: **bold** for species names, bullet points for lists, etc.
- Be concise but thorough. Aim for 2-4 paragraphs max.
- If the question is unrelated to nature/biodiversity, politely redirect."""

        # ── Step 6: Call Groq LLM ──
        try:
            if groq_client:
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.5,
                    max_tokens=1200,
                )
                answer = chat_completion.choices[0].message.content
            else:
                answer = "I'm sorry, I cannot answer that right now (AI Service Unavailable)."
        except Exception as e:
            print(f"  Groq API Error: {e}")
            answer = "I encountered an error connecting to the AI service. Please try again."

        print(f"  Answer length    : {len(answer)} chars")
        print(f"{'='*60}\n")
        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Error in ask_question: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"answer": "An error occurred while processing your question."}), 500

# --- App Run ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)