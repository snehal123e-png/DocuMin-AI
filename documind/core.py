from __future__ import annotations
import io, re, os, json, math
from typing import List, Dict, Optional
import fitz
import numpy as np
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

def ollama_status():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if r.ok:
            return True, "Ollama connected"
    except requests.RequestException:
        pass
    return False, "Ollama not detected — local fallback enabled"

def call_ollama(prompt: str, model: str = "llama3.2") -> Optional[str]:
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate",
                          json={"model": model, "prompt": prompt, "stream": False},
                          timeout=180)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.RequestException:
        return None

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def split_chunks(text: str, chunk_size: int = 900, overlap: int = 140) -> List[str]:
    words = text.split()
    if not words: return []
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words): break
        start = max(end - overlap, start + 1)
    return chunks

class DocumentAssistant:
    def __init__(self):
        self.records: List[Dict] = []
        self.doc_pages: Dict[str, int] = {}
        self._model = None
        self._vectors = None

    def _embedder(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def add_pdfs(self, uploads):
        added = []
        for upload in uploads:
            raw = upload.getvalue()
            doc = fitz.open(stream=raw, filetype="pdf")
            name = getattr(upload, "name", "uploaded.pdf")
            page_count = len(doc)
            extracted = 0
            new_records = []
            for page_no, page in enumerate(doc, start=1):
                text = clean_text(page.get_text("text"))
                if not text: continue
                extracted += 1
                for chunk in split_chunks(text):
                    new_records.append({"file": name, "page": page_no, "text": chunk})
            doc.close()
            # Replace any earlier upload with the same filename.
            self.records = [r for r in self.records if r["file"] != name]
            self.records.extend(new_records)
            self.doc_pages[name] = page_count
            added.append({"name": name, "pages": extracted, "chunks": len(new_records)})
        self._rebuild_index()
        return added

    def _rebuild_index(self):
        self._vectors = None
        if not self.records: return
        try:
            texts = [r["text"] for r in self.records]
            self._vectors = self._embedder().encode(texts, normalize_embeddings=True, show_progress_bar=False)
        except Exception:
            self._vectors = None

    def has_documents(self):
        return bool(self.records)

    def document_names(self):
        return sorted(self.doc_pages.keys())

    def stats(self):
        return {"documents":len(self.doc_pages), "pages":sum(self.doc_pages.values()),
                "chunks":len(self.records), "files":self.document_names()}

    def _retrieve(self, query: str, top_k: int = 4, filename: Optional[str] = None):
        pool = [(i,r) for i,r in enumerate(self.records) if filename is None or r["file"] == filename]
        if not pool: return []
        try:
            model = self._embedder()
            qv = model.encode([query], normalize_embeddings=True)[0]
            vectors = self._vectors
            scored = [(float(np.dot(qv, vectors[i])), r) for i,r in pool]
        except Exception:
            # Lightweight lexical fallback if embedding model cannot be downloaded/loaded.
            terms = set(re.findall(r"\w+", query.lower()))
            scored = []
            for _, r in pool:
                words = set(re.findall(r"\w+", r["text"].lower()))
                score = len(terms & words) / max(1, len(terms | words))
                scored.append((score, r))
        scored.sort(key=lambda x:x[0], reverse=True)
        return [{"file":r["file"],"page":r["page"],"text":r["text"],"score":s} for s,r in scored[:top_k]]

    def answer(self, question: str, model="llama3.2", top_k=4):
        sources = self._retrieve(question, top_k)
        if not sources:
            return {"answer":"I could not find relevant text in the uploaded documents. Try rephrasing your question or uploading a text-based PDF.","sources":[]}
        context = "\n\n".join(f"[{s['file']}, page {s['page']}] {s['text']}" for s in sources)
        prompt = f"""Answer the question using ONLY the context below. If the context does not contain the answer, say so. Be concise and cite source filename and page number.\n\nCONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"""
        answer = call_ollama(prompt, model)
        if not answer:
            best = sources[:2]
            answer = "I couldn't connect to Ollama, so here are the most relevant passages retrieved from your documents:\n\n" + "\n\n".join(f"**{s['file']} — page {s['page']}**\n{s['text']}" for s in best)
        return {"answer":answer, "sources":sources}

    def _all_text(self, filename=None):
        return "\n".join(r["text"] for r in self.records if filename is None or r["file"] == filename)

    def summarize(self, filename=None, length="Standard", model="llama3.2"):
        text = self._all_text(filename)
        if not text: return "No document text is available."
        target = {"Brief":"about 5 bullet points","Standard":"a concise executive summary with headings and key findings","Detailed":"a detailed structured summary with overview, key concepts, findings and conclusion"}.get(length, "a concise summary")
        prompt = f"Create {target} from the document text below. Preserve important facts and do not invent information.\n\nDOCUMENT:\n{text[:24000]}"
        result = call_ollama(prompt, model)
        if result: return result
        sentences = re.split(r"(?<=[.!?])\s+", text)
        # Extractive fallback: rank sentences by informative word frequency.
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        freq = {}
        for w in words: freq[w] = freq.get(w,0)+1
        ranked = []
        for i,s in enumerate(sentences):
            terms = re.findall(r"\b[a-zA-Z]{4,}\b", s.lower())
            score = sum(freq.get(w,0) for w in terms) / max(1, len(terms))
            if len(s.split()) > 7: ranked.append((score, i, s.strip()))
        chosen = sorted(sorted(ranked, reverse=True)[:8], key=lambda x:x[1])
        return "**Extractive summary** (Ollama was unavailable; key sentences selected from the source):\n\n" + "\n\n".join(f"- {x[2]}" for x in chosen)

    def flashcards(self, filename=None, count=8, model="llama3.2"):
        text = self._all_text(filename)
        if not text: return []
        prompt = f"""Create exactly {count} useful study flashcards from this document. Return ONLY valid JSON array with objects having question and answer string fields. Avoid duplicate questions. Document:\n{text[:20000]}"""
        result = call_ollama(prompt, model)
        if result:
            try:
                match = re.search(r"\[.*\]", result, re.S)
                cards = json.loads(match.group(0) if match else result)
                return [{"question":str(c["question"]), "answer":str(c["answer"])} for c in cards[:count] if "question" in c and "answer" in c]
            except (ValueError, TypeError, KeyError):
                pass
        # Fallback cards from informative sentences.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 9]
        cards = []
        for sentence in sentences:
            if len(cards) >= count: break
            words = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", sentence)
            key = words[0] if words else sentence.split()[0]
            cards.append({"question":f"What does the document explain about: {key}?",
                          "answer":sentence})
        return cards
