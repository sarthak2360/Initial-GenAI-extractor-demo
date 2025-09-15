import re, json, sqlite3, csv, os
from datetime import datetime

IN = "example1.txt"
OUT_JSON = "results.json"
OUT_CSV = "results.csv"
DB = "extractions.db"

with open(IN, "r") as f:
    text = f.read()

# simple person detection
person_pattern = re.compile(r'(?:(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})')
persons = list({m[0].strip() for m in person_pattern.findall(text)})

month_names = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
date_patterns = [
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
    r'\b' + month_names + r'\s+\d{1,2}(?:,\s*\d{4})?\b',
    r'\b\d{1,2}\s+' + month_names + r'(?:\s+\d{1,4})?\b'
]
dates = set()
for pat in date_patterns:
    for m in re.findall(pat, text, flags=re.IGNORECASE):
        if isinstance(m, tuple):
            m = " ".join([x for x in m if x])
        dates.add(m.strip())

results = {'persons': persons, 'dates': list(dates), 'source': IN}
with open(OUT_JSON, 'w') as f:
    json.dump(results, f, indent=2)

# CSV
with open(OUT_CSV, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['source','persons','dates','created_at'])
    writer.writerow([IN, ';'.join(persons), ';'.join(dates), datetime.utcnow().isoformat()])

# SQLite
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS extractions (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, persons TEXT, dates TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
c.execute('INSERT INTO extractions (filename, persons, dates) VALUES (?,?,?)', (IN, json.dumps(persons), json.dumps(list(dates))))
conn.commit()
conn.close()

print('Wrote', OUT_JSON, OUT_CSV, DB)
print('Results preview:', results)
