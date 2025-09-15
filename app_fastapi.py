"""
FastAPI app for document entity extraction.
- Accepts text (or uploaded text file) at POST /extract
- Returns JSON with extracted persons and dates
- Stores results in a local SQLite DB (extractions.db)
"""
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import sqlite3, os, json, re

DB_PATH = "extractions.db"

def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS extractions (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, persons TEXT, dates TEXT, raw_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    conn.close()

# Try to import spaCy/dateparser; if not installed, we'll fallback
USE_SPACY = False
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    USE_SPACY = True
except Exception:
    USE_SPACY = False

try:
    import dateparser
    HAVE_DATEPARSER = True
except:
    HAVE_DATEPARSER = False

def fallback_extract(text):
    # Simple heuristics for demo purposes
    person_pattern = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|Prof)?\.?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b') 
    persons = set(m.strip() for m in person_pattern.findall(text))
    month_names = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
        r'\b' + month_names + r'\s+\d{1,2}(?:,\s*\d{4})?\b',
        r'\b\d{1,2}\s+' + month_names + r'(?:\s+\d{4})?\b'
    ]
    dates = set()
    for pat in date_patterns:
        for m in re.findall(pat, text, flags=re.IGNORECASE):
            if isinstance(m, tuple):
                m = " ".join([x for x in m if x])
            dates.add(m.strip())
    # normalize dates if dateparser available
    norm_dates = []
    if HAVE_DATEPARSER:
        import dateparser
        for d in dates:
            dt = dateparser.parse(d)
            norm_dates.append(dt.strftime("%Y-%m-%d") if dt else d)
    else:
        norm_dates = list(dates)
    return list(persons), norm_dates

def extract_entities(text):
    if USE_SPACY:
        doc = nlp(text)
        persons = list({ent.text for ent in doc.ents if ent.label_ == "PERSON"})
        dates = list({ent.text for ent in doc.ents if ent.label_ == "DATE"})
        if HAVE_DATEPARSER:
            import dateparser
            nd = []
            for d in dates:
                p = dateparser.parse(d)
                nd.append(p.strftime("%Y-%m-%d") if p else d)
            dates = nd
        return persons, dates
    else:
        return fallback_extract(text)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    ensure_db()

@app.post("/extract")
async def extract_text(text: str = Form(None), file: UploadFile = File(None)):
    if file is not None:
        content = await file.read()
        try:
            text = content.decode('utf-8')
        except:
            text = content.decode('latin-1', errors='ignore')
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    persons, dates = extract_entities(text)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO extractions (filename, persons, dates, raw_text) VALUES (?,?,?,?)",
              (getattr(file, "filename", None) or "inline_text", json.dumps(persons), json.dumps(dates), text[:4000]))
    conn.commit()
    conn.close()
    return {"persons": persons, "dates": dates}
