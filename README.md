<div align="center">

# 🌿 BioScout

### *Digitizing Biodiversity, One Sighting at a Time*

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-BioScout-00c853?style=for-the-badge)](https://bioscout-wj0y.onrender.com/landing)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![PyTorch](https://img.shields.io/badge/PyTorch-ResNet50-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](Dockerfile)

<br/>

> **BioScout** is a citizen-science platform that empowers communities to document the rich
> biodiversity of **Islamabad & the Margalla Hills** through AI-powered wildlife identification,
> interactive mapping, and an intelligent Q&A assistant — turning every smartphone into
> a field research tool.

<br/>

[Explore Demo »](https://bioscout-wj0y.onrender.com/landing) · [Report Bug](https://github.com/yourusername/bioscout/issues) · [Request Feature](https://github.com/yourusername/bioscout/issues)

---

</div>

<br/>

## 📸 Screenshots

<!--
<div align="center">
<table>
  <tr>
    <td align="center"><b>🏠 Landing Page</b></td>
    <td align="center"><b>🔍 AI Identification</b></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/landing.png" alt="Landing Page" width="400"/></td>
    <td><img src="docs/screenshots/identification.png" alt="AI Identification" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>🗺️ Sighting Map</b></td>
    <td align="center"><b>📊 Dashboard</b></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/map.png" alt="Sighting Map" width="400"/></td>
    <td><img src="docs/screenshots/dashboard.png" alt="Dashboard" width="400"/></td>
  </tr>
</table>

<sub><i>Replace with actual screenshots from your deployment</i></sub>
</div>
-->

<div align="center">
<em>Screenshots coming soon</em>
</div>

<br/>

---

## 🧬 Why BioScout?

The **Margalla Hills National Park** harbors over **600 plant species**, **250+ bird species**, and
dozens of mammal and reptile species — yet much of this biodiversity remains undocumented in
accessible digital formats. Traditional field surveys are expensive, slow, and limited in scale.

**BioScout bridges this gap by:**

| Problem | BioScout's Solution |
|---|---|
| Manual species identification requires expert knowledge | 🤖 AI-powered instant classification via fine-tuned ResNet-50 |
| Biodiversity data is scattered and inaccessible | 🗺️ Centralized, filterable observation database with GPS mapping |
| Citizens lack tools to contribute to conservation | 📱 Simple upload-and-identify workflow from any device |
| Species information is hard to find | 💬 RAG-powered Q&A assistant with curated local knowledge |

---

## ✨ Features

### 🔍 AI-Powered Species Identification
Upload any photo of local flora or fauna — our **fine-tuned ResNet-50** deep learning model
classifies it instantly with confidence scores. Trained specifically on species found in the
Islamabad Capital Territory and surrounding regions.

### 🤖 Intelligent Q&A Assistant
Ask natural-language questions like *"What birds migrate through Margalla Hills in winter?"*
Our **RAG (Retrieval-Augmented Generation)** pipeline retrieves relevant context from a curated
knowledge base of local ecology text files and generates accurate answers via the **Groq API**.

### 🗺️ Interactive Sighting Map
Every observation is pinned on a custom **SVG-based map of Pakistan** with GPS coordinates.
Explore biodiversity hotspots, filter by species or date, and discover patterns in wildlife
distribution across the region.

### 📍 Precision Location Services
Automatic **GPS coordinate capture** from the browser's Geolocation API ensures precise
data logging. A city-based fallback system handles entries from devices without GPS access.

### 📊 Community Observation Dashboard
Browse, search, and filter the growing database of community sightings. Sort by **date**,
**species**, **location**, or **observer** — all rendered in a responsive, paginated interface.

### 📱 Glassmorphism UI
A modern, dark-themed interface built with **vanilla CSS** — no heavy frameworks.
Features include scroll-driven animations, frosted-glass card effects, and a fully
responsive layout optimized for mobile fieldwork.

---

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────────────┐
│ CLIENT (Browser) │
│ ┌──────────┐ ┌──────────────┐ ┌───────────┐ ┌───────────┐ │
│ │ Landing │ │ Upload + │ │ Sighting │ │ Q&A │ │
│ │ Page │ │ Identify │ │ Map │ │ Assistant │ │
│ └────┬─────┘ └──────┬───────┘ └─────┬─────┘ └─────┬─────┘ │
│ │ │ │ │ │
│ │ GPS Coords + Image │ User Query │
└───────┼───────────────┼───────────────┼───────────────┼─────────┘
│ │ │ │
▼ ▼ ▼ ▼
┌─────────────────────────────────────────────────────────────────┐
│ FLASK BACKEND (Python) │
│ │
│ ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐ │
│ │ Jinja2 │ │ Route │ │ RAG Pipeline │ │
│ │ Templating │ │ Handlers │ │ ┌──────────────────┐ │ │
│ └──────────────┘ └──────┬───────┘ │ │ Text Chunking │ │ │
│ │ │ │ + Embedding │ │ │
│ ┌──────┴───────┐ │ │ + Retrieval │ │ │
│ │ ResNet-50 │ │ │ + Groq LLM Call │ │ │
│ │ Inference │ │ └──────────────────┘ │ │
│ │ (PyTorch) │ └────────────────────────┘ │
│ └──────┬───────┘ │
└───────────────────────────┼─────────────────────────────────────┘
│
┌─────────────┼─────────────┐
▼ ▼ ▼
┌──────────────┐ ┌──────────┐ ┌───────────┐
│ MongoDB │ │Cloudinary│ │ Groq │
│ Atlas │ │ (CDN) │ │ API │
│ (Database) │ │ (Images)│ │ (LLM) │
└──────────────┘ └──────────┘ └───────────┘

---

## 📁 Project Structure

```text
bioscout/
├── app.py                  # Flask application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container configuration
├── .env                    # Environment variables (create from template)
│
├── knowledge_base/         # Curated text files on local species
│   ├── birds_of_margalla.txt
│   ├── common_mammals.txt
│   ├── conservation_tips.txt
│   ├── plant_species.txt
│   └── reptiles.txt
│
├── static/
│   ├── css/
│   │   └── index1_style.css # Main stylesheet
│   └── images/              # Static images + frames
│
└── templates/
    ├── index.html          # Main landing/app page
    ├── landing.html        # Landing page
    ├── login.html          # Authentication page
    ├── observations.html   # Observation listing
    └── qa.html             # Q&A assistant page
```

> **Note:** This structure reflects the core components of the application.

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology | Purpose |
|:---:|:---|:---|
| **Frontend** | HTML5 · CSS3 · Vanilla JS · Jinja2 | Responsive glassmorphism UI with scroll animations |
| **Backend** | Python · Flask | RESTful routes, templating, business logic |
| **Database** | MongoDB Atlas | NoSQL document store for observations + users |
| **AI / ML** | PyTorch · ResNet-50 | Fine-tuned image classification model |
| **LLM** | Groq API · RAG Pipeline | Intelligent species Q&A with retrieved context |
| **Storage** | Cloudinary | Cloud-based image CDN + transformations |
| **DevOps** | Docker · Render | Containerized deployment |

</div>

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Minimum Version | Required? |
|:---|:---|:---:|
| Python | 3.10+ | ✅ |
| MongoDB Atlas Account | — | ✅ |
| Cloudinary Account | — | ✅ |
| Groq API Key | — | ⚠️ Optional (for Q&A) |
| Docker | 20.10+ | ⚠️ Optional |

### ⚡ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/bioscout.git
cd bioscout

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your actual credentials (see below)

# 5. Launch the application
python app.py
```

Then open http://localhost:5000 in your browser. 🎉

<br/>

### 🔐 Environment Variables

Create a `.env` file in the project root:

```bash
# ── Flask ──────────────────────────────────
SECRET_KEY=your_super_secret_flask_key

# ── MongoDB ────────────────────────────────
MONGO_URI=mongodb+srv://<user>:<password>@cluster.xxxxx.mongodb.net/bioscout?retryWrites=true&w=majority

# ── Cloudinary ─────────────────────────────
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# ── Groq (Optional — enables Q&A) ─────────
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

<br/>

### 🐳 Docker Deployment

To build and run the application using Docker:

```bash
# Build the image
docker build -t bioscout .

# Run the container
docker run -d \
  --name bioscout \
  -p 5000:5000 \
  --env-file .env \
  bioscout
```

**Deploy to Render (production):**
1. Push your repo to GitHub
2. Connect the repo on Render
3. Set environment variables in the Render dashboard
4. Deploy as a Web Service with Docker runtime

<br/>

### 🧪 Testing

Run the test suite to ensure everything is working correctly:

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=. --cov-report=html
```

---

## 🗺️ Roadmap

- [ ] AI-powered species identification (ResNet-50)
- [ ] Interactive sighting map with GPS
- [ ] RAG-based Q&A assistant
- [ ] Community observation dashboard
- [ ] User authentication & profiles
- [ ] Gamification (badges, leaderboards)
- [ ] Mobile-native app (React Native / Flutter)
- [ ] Multi-region expansion beyond Islamabad
- [ ] Export data in Darwin Core format for GBIF
- [ ] Real-time notifications for rare species sightings

---

## 🤝 Contributing

Contributions make the open-source community an incredible place to learn, inspire, and create.
Any contribution you make is **greatly appreciated**.

1. **Fork the repository**
2. **Create your feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit your changes**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
4. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

> 💡 **First time contributing?** Check out issues tagged with `good first issue`.

**Contribution Ideas:**
* Add more species to the training dataset
* Expand the RAG knowledge base with new text files
* Improve model accuracy with data augmentation
* Add new map layers (elevation, vegetation zones)
* Write tests for uncovered routes

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.

> MIT License · Copyright (c) 2025 BioScout Contributors

---

## 🙏 Acknowledgments

* **Margalla Hills National Park** — for inspiring this project
* **PyTorch** — deep learning framework
* **Groq** — blazing-fast LLM inference
* **MongoDB Atlas** — managed database
* **Cloudinary** — image management
* **Render** — deployment platform
<div align="center">
Built with 💚 for the wildlife of Pakistan

⭐ Star this repo if you found it useful — it helps others discover BioScout!

<br/>
GitHub Stars
GitHub Forks

</div> ```