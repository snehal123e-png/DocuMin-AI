from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from documind.core import DocumentAssistant

app = FastAPI(title="DocuMind AI API", version="1.0.0",
              description="PDF ingestion, semantic question answering, summaries and flashcards.")
assistant = DocumentAssistant()

class AskRequest(BaseModel):
    question: str
    top_k: int = 4
    model: str = "llama3.2"

class SummaryRequest(BaseModel):
    filename: Optional[str] = None
    length: str = "Standard"
    model: str = "llama3.2"

class FlashcardRequest(BaseModel):
    filename: Optional[str] = None
    count: int = 8
    model: str = "llama3.2"

@app.get("/")
def root():
    return {"name":"DocuMind AI API","docs":"/docs","status":"ready"}

@app.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    results = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"{f.filename}: only PDF files are supported")
        content = await f.read()
        class Upload:
            name = f.filename
            def getvalue(self): return content
        results.extend(assistant.add_pdfs([Upload()]))
    return {"processed":results, "stats":assistant.stats()}

@app.get("/documents")
def list_documents():
    return assistant.stats()

@app.post("/ask")
def ask(req: AskRequest):
    if not assistant.has_documents(): raise HTTPException(400, "Upload a PDF first")
    return assistant.answer(req.question, req.model, max(1,min(req.top_k,10)))

@app.post("/summary")
def summary(req: SummaryRequest):
    if not assistant.has_documents(): raise HTTPException(400, "Upload a PDF first")
    return {"summary":assistant.summarize(req.filename, req.length, req.model)}

@app.post("/flashcards")
def flashcards(req: FlashcardRequest):
    if not assistant.has_documents(): raise HTTPException(400, "Upload a PDF first")
    return {"flashcards":assistant.flashcards(req.filename, max(1,min(req.count,30)), req.model)}
