# Wie der Wert ermittelt wird - Schritt für Schritt

## 🎯 Überblick

Wenn der Nutzer auf den Button **"🔍 Web Search"** klickt, wird folgender Prozess ausgelöst:

```
USER KLICKT "🔍 Web Search"
           ↓
    [FRONTEND] Sendet Anfrage
           ↓
    [BACKEND] Sucht nach Marktdaten
           ↓
    [CLAUDE] Analysiert Preise
           ↓
    [DATABASE] Speichert neuen Wert
           ↓
    [FRONTEND] Zeigt Ergebnis
```

---

## 📱 SCHRITT 1: Frontend - User klickt Button

**Datei**: `frontend/src/components/VinylCard.tsx` (Zeile 158-200)

```typescript
const recheckValue = async () => {
  // ✓ Prüfe: Record_ID, Artist, Title vorhanden?
  if (!record?.record_id || !record?.artist || !record?.title) return
  
  // ✓ Zeige "Searching..." Animation
  setIsCheckingValue(true)
  setWebValue(null)
  
  try {
    // ✓ Log: Welcher Artikel wird gesucht?
    console.log('VinylCard: Requesting web-based value estimation for', 
                record.artist, '-', record.title)
    
    // ✓ Sende POST Request zum Backend
    const response = await fetch(`${API_BASE}/api/v1/estimate-value/${record.record_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
```

**Was passiert hier:**
- Button "🔍 Web Search" wird geklickt
- Record-ID wird mitgesendet (z.B. `abc123xyz`)
- Artist + Title sind erforderlich (z.B. "Nirvana - Nevermind")
- Loading-State wird angezeigt (🔄 Searching...)

---

## 🌐 SCHRITT 2: Frontend → Backend (HTTP POST)

**Request:**
```
POST http://localhost:8000/api/v1/estimate-value/abc123xyz

Body: (leer, alle Infos sind in der URL und Datenbank)
```

**Was wird gesendet:**
- Record-ID in der URL
- Content-Type: application/json Header
- Weiterleiten an Backend-Endpoint

---

## 🔍 SCHRITT 3: Backend - Datensatz abrufen

**Datei**: `backend/api/routes.py` (Zeile 864+)

```python
@router.post("/estimate-value/{record_id}")
async def estimate_value_with_websearch(
    record_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    
    # 1️⃣ Hole Vinyl-Record aus Datenbank
    vinyl_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
    
    if not vinyl_record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # 2️⃣ Prüfe: Artist + Title vorhanden?
    if not vinyl_record.artist or not vinyl_record.title:
        raise HTTPException(status_code=400, detail="Artist and title required")
    
    logger.info(f"Estimating value for {vinyl_record.artist} - {vinyl_record.title}")
```

**Was wurde gefunden:**
- Record aus DB: Artist, Title, Year, Label, Genres, etc.
- Aktueller Wert (z.B. €50.00)
- Confidence Level (z.B. 0.85 = 85%)

---

## 🔎 SCHRITT 4: Web Search - Marktdaten sammeln

**Still in Backend:**

```python
# 3️⃣ Erstelle Such-Query
search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
if vinyl_record.year:
    search_query += f" {vinyl_record.year}"

# Beispiel: "Nirvana Nevermind vinyl record price 1991"

# 4️⃣ Führe Web-Suche durch (Tavily API)
search_results = chat_tools.search_and_scrape(
    search_query,
    scrape_results=True
)
```

**Was passiert:**
- Tavily API wird aufgerufen (externe Suchmaschine)
- Sucht nach: "Nirvana Nevermind vinyl record price 1991"
- Findet Ergebnisse von:
  - eBay (aktuelle Verkaufspreise)
  - Discogs (Referenzpreise)
  - Vinted (Secondhand-Preise)
  - Musicbrainz
  - etc.

**Beispiel Suchergebnisse:**

```
Titel: "Nirvana - Nevermind Vinyl LP (1991)"
Content: "Current market price: €45-55. Original pressing highly sought after..."

Titel: "Nevermind - Nirvana | eBay Auction Results"
Content: "Recent sales show €48-52 range for good condition copies..."

Titel: "Discogs - Nirvana - Nevermind"
Content: "Median price: €48. Grades range from VG to M..."
```

---

## 🧠 SCHRITT 5: Claude AI - Analyse & Wertermittlung

**Still in Backend:**

```python
# 5️⃣ Baue Kontext für Claude
record_context = f"""
Vinyl Record Details:
- Artist: {vinyl_record.artist}
- Title: {vinyl_record.title}
- Year: {vinyl_record.year}
- Label: {vinyl_record.label}
- Condition: Based on image analysis (confidence: 85%)
"""

market_context = """
Market Research Results:
- Discogs: €45-55 range, stable market
- eBay recent sales: €48-52
- Vinted listings: €45-50
"""

# 6️⃣ Sende alles an Claude Haiku
valuation_prompt = f"""
Based on the web search results and record details,
estimate the fair market value of this vinyl record in EUR.

{market_context}
{record_context}

Please provide:
1. Estimated fair market value in EUR
2. Price range (min and max)
3. Key factors affecting the price
4. Market condition (strong/stable/weak)
5. Brief explanation

Format:
ESTIMATED_VALUE: €XX.XX
PRICE_RANGE: €XX.XX - €XX.XX
MARKET_CONDITION: [strong/stable/weak]
FACTORS: [list of factors]
EXPLANATION: [brief explanation]
"""

# 7️⃣ Claude antwortet
response = anthropic_client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=500,
    messages=[{"role": "user", "content": valuation_prompt}]
)

valuation_text = response.content[0].text
```

**Claude analysiert:**

**Input für Claude:**
```
Marktdaten: eBay zeigt €48-52, Discogs €45-55, Vinted €45-50
Record: Nirvana Nevermind 1991, Original Pressing, Guter Zustand (85% Confidence)

→ Frage: Was ist ein fairer Marktpreis?
```

**Claude antwortet (Beispiel):**
```
ESTIMATED_VALUE: €48.00
PRICE_RANGE: €45.00 - €52.00
MARKET_CONDITION: stable
FACTORS: [original 1991 pressing, good condition, normal demand, standard label]
EXPLANATION: The 1991 original pressing is very common. Market is stable 
at €45-52 range. Your copy appears to be in good condition based on the 
image analysis, suggesting the mid-range of €48 is appropriate.
```

---

## 📊 SCHRITT 6: Backend - Parse & Speicher

```python
# 8️⃣ Parse Claudes Antwort (regex Parsing)
for line in valuation_text.split('\n'):
    if line.startswith('ESTIMATED_VALUE:'):
        match = re.search(r'€?([\d.]+)', line)
        if match:
            estimated_value = float(match.group(1))  # €48.00 → 48.0
    
    if line.startswith('PRICE_RANGE:'):
        matches = re.findall(r'€?([\d.]+)', line)
        if len(matches) >= 2:
            price_range_min = float(matches[0])  # €45.00 → 45.0
            price_range_max = float(matches[1])  # €52.00 → 52.0
    
    if line.startswith('MARKET_CONDITION:'):
        market_condition = line.replace('MARKET_CONDITION:', '').strip()  # "stable"
    
    if line.startswith('FACTORS:'):
        factors = [f.strip() for f in line.split(',')]  # ["original pressing", "good condition", ...]
    
    if line.startswith('EXPLANATION:'):
        explanation = line.replace('EXPLANATION:', '').strip()

# 9️⃣ AKTUALISIERE Datensatz in Datenbank
vinyl_record.estimated_value_eur = estimated_value  # War: €50.00 → Jetzt: €48.00
vinyl_record.updated_at = datetime.utcnow()
db.commit()  # ✓ In DB speichern!

logger.info(f"Value updated: €{estimated_value} for {vinyl_record.artist}")
```

**Was wird gemacht:**
- Claudes Antwort wird zeilenweise geparst
- Zahlen werden mit Regex extrahiert (€ Zeichen entfernt)
- `estimated_value_eur` wird ERSETZT (nicht addiert!)
  - ALT: €50.00
  - NEU: €48.00
- Änderungszeit wird aktualisiert
- **COMMIT**: Alle Änderungen werden in DB gespeichert

---

## 📤 SCHRITT 7: Backend → Frontend (Response)

```python
# 🔟 Sende Ergebnis zum Frontend
return {
    "record_id": "abc123xyz",
    "estimated_value_eur": 48.0,
    "price_range_min": 45.0,
    "price_range_max": 52.0,
    "market_condition": "stable",
    "factors": ["original pressing", "good condition", "normal demand"],
    "explanation": "The 1991 original pressing is very common...",
    "sources_found": 5
}
```

**Response JSON:**
```json
{
  "record_id": "abc123xyz",
  "estimated_value_eur": 48.0,
  "price_range_min": 45.0,
  "price_range_max": 52.0,
  "market_condition": "stable",
  "factors": ["original pressing", "good condition", "stable market"],
  "explanation": "Market shows stable pricing in the €45-52 range",
  "sources_found": 5
}
```

---

## 🎨 SCHRITT 8: Frontend - Anzeige & Formatierung

**Back in `VinylCard.tsx`:**

```typescript
// Erhalte Response vom Backend
const data = await response.json()

console.log('VinylCard: Value estimation response:', data)

if (data.estimated_value_eur) {
  const value = data.estimated_value_eur  // 48.0
  const range = data.price_range_min && data.price_range_max 
    ? ` (€${data.price_range_min}-€${data.price_range_max})`
    : ''
  // → " (€45.0-€52.0)"
  
  const condition = data.market_condition ? ` [${data.market_condition} market]` : ''
  // → " [stable market]"
  
  // FINALE ANZEIGE:
  setWebValue(`€${value}${range}${condition}`)
  // → "€48.0 (€45.0-€52.0) [stable market]"
  
  console.log('VinylCard: Web value set to:', value)
}
```

**Frontend zeigt jetzt:**
```
Estimated Value: €48.0
Web: €48.0 (€45.0-€52.0) [stable market]
     ✓ Apply
```

---

## ✅ SCHRITT 9: User klickt "✓ Apply"

```typescript
const applyWebValue = async () => {
  if (!webValue) return
  
  // Extrahiere Zahl aus "€48.0 (€45.0-€52.0) [stable market]"
  const priceMatch = webValue.match(/\d+(?:\.\d{2})?/)
  if (!priceMatch) return
  
  const newValue = parseFloat(priceMatch[0])  // 48.0
  
  // Aktualisiere Component-State
  const updatedRecord = {
    ...record,
    metadata: {
      ...record.metadata,
      estimated_value_eur: newValue,  // ← Neuer Wert
    },
  }
  
  onMetadataUpdate?.(updatedRecord.metadata)  // Speichere zu übergeordnetem Component
  setWebValue(null)
}
```

**Was passiert:**
- "Apply" Button wird geklickt
- Wert wird aus der Anzeige extrahiert (€48.0)
- Component speichert neuen Wert
- UI aktualisiert sich

---

## 📋 Vollständiger Ablauf - Zusammenfassung

| Schritt | Was | Wo | Dauer |
|---------|-----|----|----|
| 1 | User klickt "🔍 Web Search" | Frontend | sofort |
| 2 | POST Request gesendet | Frontend → Backend | < 1ms |
| 3 | Record aus DB geladen | Backend | < 10ms |
| 4 | Web Search durchgeführt | Tavily API | 2-5 Sek |
| 5 | Claude Haiku Analyse | Claude API | 3-10 Sek |
| 6 | Wert geparst & gespeichert | Backend DB | < 50ms |
| 7 | Response zum Frontend | Backend → Frontend | < 1ms |
| 8 | Wert formatiert & angezeigt | Frontend | sofort |
| 9 | User klickt "✓ Apply" | Frontend | (User entscheidet) |
| **TOTAL** | **Von Klick bis Anzeige** | | **5-16 Sekunden** |

---

## 🔄 Wiederholung Test

**Was passiert bei der 2. Suche?**

```
1. Suche #1: €50.00 → €48.00 ✓
2. Suche #2: €48.00 → €48.00 ✓ (nicht €57.60!)
3. Suche #3: €48.00 → €48.00 ✓ (immer €48.00)
```

**Warum ist das richtig?**
- Web Search findet immer die gleichen Marktdaten
- Claude gibt immer die gleiche Analyse
- Wert wird **ERSETZT** nicht addiert
- ≠ Altes System: €48 × 1.2 = €57.60 ❌

---

## 🐛 Was kann schief gehen?

| Problem | Ursache | Lösung |
|---------|--------|--------|
| "Error checking market value" | Backend nicht erreichbar | `docker-compose restart backend` |
| Suche dauert > 30 Sek | TAVILY API zu langsam | Internet-Verbindung prüfen |
| Keine Ergebnisse | Ungültiger Artist/Title | Record mit korrektem Namen hochladen |
| Unrealistische Werte | Claude falsch trainiert | Claude Response prüfen (Logs) |
| Wert speichert nicht | "Apply" Button nicht geklickt | User muss "✓ Apply" klicken |

---

## 📝 Logs prüfen

**Backend-Logs anschauen:**
```bash
docker-compose logs backend -f
```

**Sollte zeigen:**
```
INFO: Estimating value for Nirvana - Nevermind
INFO: Web search results retrieved
INFO: Claude valuation response: ESTIMATED_VALUE: €48.00...
INFO: Value estimation completed: €48.00 for Nirvana - Nevermind
```

**Browser-Logs (F12):**
```javascript
VinylCard: Requesting web-based value estimation for Nirvana - Nevermind
VinylCard: Value estimation response: {estimated_value_eur: 48, ...}
VinylCard: Web value set to: 48
```

---

## 🎯 Zusammenfassung: Warum ist das besser?

| Aspekt | Alt (❌) | Neu (✅) |
|--------|----------|----------|
| **Logik** | Multiplikation | Real Data |
| **Konsistenz** | Wertet auf jedes Mal | Gleich bleibend |
| **Marktdaten** | Simuliert | Echt (Tavily) |
| **Analyse** | Formel | KI (Claude) |
| **Wiederholbar** | €50 → €60 → €72 | €50 → €48 → €48 |
| **Transparent** | Keine Erklärung | Preisspanne + Faktoren |

