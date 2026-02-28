# BioScout 🌿🦅

**BioScout** is a citizen science initiative and web platform designed to digitize and document the rich biodiversity of **Islamabad and the Margalla Hills**. It empowers users to upload wildlife observations, which are automatically identified using deep learning, and visualizes this data to aid conservation awareness.

🔗 **Live Demo:** [Add your deployment link here]

## ✨ Key Features

*   **🔍 AI-Powered Identification:** Uses a fine-tuned **ResNet-50** model to instantly classify uploaded images of flora and fauna.
*   **🤖 Intelligent Q&A Assistant:** A RAG (Retrieval-Augmented Generation) system powered by **Groq API** that answers user queries about local species using a curated knowledge base of text files.
*   **🗺️ Interactive Sighting Map:** Visualizes observation hotspots across Pakistan with a custom SVG map and GPS coordinate tracking.
*   **📍 Location Services:** Capturing exact GPS coordinates for precise data logging, with a city-based fallback for non-GPS entries.
*   **📱 Responsive Glassmorphism UI:** A modern, dark-themed interface built with vanilla CSS, featuring scroll-driven animations and a premium aesthetic.
*   **📊 Observation Dashboard:** Filterable database of community sightings by date, species, and location.

## 🛠️ Tech Stack

*   **Frontend:** HTML5, CSS3 (Glassmorphism), JavaScript (Vanilla), Jinja2 Templates
*   **Backend:** Python, Flask
*   **Database:** MongoDB Atlas (NoSQL)
*   **AI & ML:** PyTorch, Transformers (Hugging Face), Groq API (LLM)
*   **Storage:** Cloudinary (Image CDN)
*   **Deployment:** Docker / Render

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   MongoDB Atlas Account
*   Cloudinary Account
*   Groq API Key (Optional, for Q&A)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/bioscout.git
    cd bioscout
    ```

2.  **Set up Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory:
    ```env
    MONGO_URI=your_mongodb_connection_string
    CLOUDINARY_CLOUD_NAME=your_cloud_name
    CLOUDINARY_API_KEY=your_api_key
    CLOUDINARY_API_SECRET=your_api_secret
    GROQ_API_KEY=your_groq_key
    SECRET_KEY=your_flask_secret_key
    ```

5.  **Run the Application**
    ```bash
    python app.py
    ```
    Visit `http://localhost:5000` in your browser.

## 🐳 Docker Support

To run via Docker:
```bash
docker build -t bioscout .
docker run -p 5000:5000 --env-file .env bioscout
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

This project is licensed under the MIT License.
