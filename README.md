# DocuMind AI — Intelligent Document Assistant

DocuMind AI is a Retrieval-Augmented Generation (RAG) application that lets users upload PDF documents, ask natural-language questions, generate executive summaries, and create study flashcards.

## Features
- Multi-PDF upload and text extraction with PyMuPDF.
- Semantic retrieval using Sentence Transformers (`all-MiniLM-L6-v2`).
- Context-grounded Q&A with retrieved source passages and page references.
- Executive summaries and structured flashcards.
- Ollama local LLM integration (no paid API key required).
- Built-in extractive/lexical fallback when Ollama or embedding model is unavailable.
- Streamlit user interface and FastAPI REST API with interactive Swagger documentation.

## Requirements
- Python 3.10 or newer (Python 3.11/3.12 recommended).
- Internet access for the first installation/model download.
- Optional: Ollama for stronger generated answers, summaries and flashcards.

## Setup (Windows PowerShell)
```powershell
# 1. Extract the ZIP and open the project folder
cd DocuMind_AI

# 2. Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# If PowerShell blocks activation, run this once in the current terminal:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Start the web application
streamlit run app.py
```
Open the local address printed in the terminal (usually http://localhost:8501).

## Optional: Enable local LLM generation with Ollama
1. Install Ollama from https://ollama.com/download.
2. Open a terminal and run:
```bash
ollama pull llama3.2
ollama serve
```
3. Keep Ollama running and launch DocuMind AI. Enter the installed model name in the Streamlit sidebar.

Without Ollama, the application still works: it retrieves relevant passages, creates extractive summaries and generates basic flashcards. For the strongest semantic retrieval, allow Sentence Transformers to download `all-MiniLM-L6-v2` on first use. If that model cannot load, a lexical retrieval fallback is used.

## Run the REST API
Open a second terminal in the project folder, activate the same virtual environment, then run:
```bash
uvicorn api:app --reload
```
- API root: http://127.0.0.1:8000/
- Swagger API documentation: http://127.0.0.1:8000/docs
- Alternative ReDoc: http://127.0.0.1:8000/redoc

### API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/documents/upload` | Upload one or more PDF files (multipart form field: `files`) |
| GET | `/documents` | List indexed document names and counts |
| POST | `/ask` | Semantic question answering |
| POST | `/summary` | Generate summary |
| POST | `/flashcards` | Generate flashcards |

Example request bodies:
```json
POST /ask
{"question":"What is the main objective of this paper?","top_k":4,"model":"llama3.2"}
```
```json
POST /summary
{"filename":null,"length":"Standard","model":"llama3.2"}
```
```json
POST /flashcards
{"filename":null,"count":8,"model":"llama3.2"}
```
`filename: null` means all indexed documents.

## GitHub upload
```bash
git init
git add .
git commit -m "Initial commit: DocuMind AI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/documind-ai.git
git push -u origin main
```
Create an empty repository on GitHub first and replace `YOUR_USERNAME` with your GitHub username. Do not commit `.venv`, large PDFs, secrets, or local model files.

## Project structure
```text
DocuMind_AI/
├── app.py                 # Streamlit UI
├── api.py                 # FastAPI endpoints
├── documind/
│   ├── __init__.py
│   └── core.py            # PDF parsing, chunking, retrieval, RAG and generation
├── docs/
│   └── API.md             # API reference
├── data/
│   └── README.md          # Sample data guidance
├── requirements.txt
├── .gitignore
└── README.md
```

## Important notes / limitations
- This starter version processes text-based PDFs. Scanned/image-only PDFs need OCR; those are detected and reported rather than silently treated as searchable.
- The first embedding-model download may take time and requires internet. There is a lexical fallback if the model is unavailable.
- The default in-memory index is cleared when the app/API process restarts. Re-upload documents after restarting.
- Ollama is optional. Without it, answers show retrieved source passages, summaries use extractive sentence selection, and flashcards use sentence-based fallback.
- Always verify critical facts, calculations, citations and decisions against the original PDF.

## Demo checklist
1. Upload a PDF in **Document library** and click **Process documents**.
2. Ask a question whose answer is present in the PDF.
3. Expand **View source passages** to show file and page references.
4. Generate an executive summary and download it.
5. Generate flashcards and download them.
6. Optionally show `/docs` for API documentation.
