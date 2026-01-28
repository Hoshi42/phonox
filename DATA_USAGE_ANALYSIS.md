# Datenverwendung für Preissuche - Analyse

## Zusammenfassung
- **Bildanalyse**: Extrahiert Katalognummer, nutzt sie aber NICHT für Preissuche
- **Websearch**: Nutzt NUR Artist + Titel + Jahr, die Katalognummer wird IGNORIERT

---

## 1. Bildanalyse (Backend: `vision.py`)

### Extrahierte Daten
```python
{
    "artist": "extracted artist name",
    "title": "extracted album title",
    "year": 1969 or null,
    "label": "extracted label name",
    "catalog_number": "extracted catalog number or null",  ← WIRD EXTRAHIERT
    "barcode": "extracted barcode/UPC or null",
    "genres": ["genre1", "genre2"],
    "confidence": 0.85
}
```

### Wie Katalognummer extrahiert wird
- Claude Sonnet 4.5 analysiert das Albumcover
- Sucht nach alphanumerischen Codes wie "ABC-123", "DEF 456"
- Unterscheidet diese vom Barcode (12-13 stellige Zahlen)
- **Speichert** die Katalognummer in der Datenbank

### Problem
Die Katalognummer wird extrahiert und gespeichert, aber **NICHT verwendet** für die Preissuche.

---

## 2. Websearch für Preissuche (Backend: `routes.py`, Zeile 896-900)

### Aktuell verwendete Daten
```python
search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
if vinyl_record.year:
    search_query += f" {vinyl_record.year}"

# Beispiel: "Pink Floyd The Wall vinyl record price 1979"
```

### Daten, die NICHT verwendet werden
- ❌ `catalog_number` - wird ignoriert
- ❌ `label` - wird ignoriert
- ❌ `barcode` - wird ignoriert
- ❌ `genres` - werden ignoriert

### Auswirkung
- Die Suche ist zu allgemein
- Kann mehrere Ausgaben des gleichen Albums finden (unterschiedliche Label/Länder)
- Preise können stark variieren zwischen verschiedenen Ausgaben des gleichen Albums
- **Beispiel**: Pink Floyd "The Wall" wurde von vielen Labels in verschiedenen Jahren gepresst
  - Deutsche Ausgabe (1979, Harvest) ≠ US-Ausgabe (1979, Columbia) ≠ UK-Ausgabe (1979, Harvest)
  - Jede Ausgabe hat unterschiedliche Preise und Raritäten

---

## 3. Vergleich: Katalognummer-Nutzen

### Ohne Katalognummer (aktuell)
```
Suche: "Pink Floyd The Wall vinyl record price 1979"
Ergebnisse:
  - Pink Floyd The Wall (Türkei, Philips) €15
  - Pink Floyd The Wall (UK, Harvest) €25
  - Pink Floyd The Wall (Japan, Odeon) €60
  - Pink Floyd The Wall (US, Columbia) €30
```
→ Durchschnittspreis sehr ungenau

### Mit Katalognummer (verbessert)
```
Suche: "Pink Floyd The Wall vinyl record price 1979 SHVL 411"
Ergebnisse:
  - Pink Floyd The Wall (UK, Harvest, SHVL 411) €25
  - Pink Floyd The Wall (UK, Harvest, SHVL 411) €27
  - Pink Floyd The Wall (UK, Harvest, SHVL 411) €24
```
→ Spezifische Ausgabe, viel genauere Preisermittlung

---

## 4. Empfehlung

### Katalognummer sollte in Websearch verwendet werden

**Änderung in `backend/api/routes.py` (Zeile 896-898):**

```python
# AKTUELL:
search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
if vinyl_record.year:
    search_query += f" {vinyl_record.year}"

# VERBESSERT:
search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
if vinyl_record.catalog_number:
    search_query += f" {vinyl_record.catalog_number}"  # ← SPEZIFISCHER
if vinyl_record.year:
    search_query += f" {vinyl_record.year}"
```

### Vorteile
1. **Genauere Preissuche**: Findet die exakte Ausgabe statt beliebiger Versionen
2. **Bessere Valuation**: Berücksichtigt Rarität und Label
3. **Nutzt verfügbare Daten**: Katalognummer wird bereits extrahiert!
4. **Mehr Relevanz**: Discogs und Vinted Suchanfragen werden präziser

### Beispiel-Suchanfragen
```
Schlecht: "Pink Floyd The Wall vinyl record price 1979"
Besser:   "Pink Floyd The Wall vinyl record price SHVL 411 1979"

Schlecht: "The Beatles Abbey Road vinyl record price"
Besser:   "The Beatles Abbey Road vinyl record price PCS 7088 1969"
```

---

## 5. Zusätzliche Daten die überlegt werden könnten

| Daten | Verwendung | Empfehlung |
|-------|-----------|------------|
| catalog_number | Exakte Ausgabe | ✅ **Nutzen!** |
| barcode | ISBN-ähnlich, eindeutig | ⚠️ Optional (wenn Katalognummer fehlschlägt) |
| label | Pressland identifizieren | ⚠️ Optional (kann in search_query nach Katalognummer kommen) |
| genres | Markt-Kontext | ❌ Nicht nötig |
| condition | Preis-Multiplikator | ✅ Wird von Claude analysiert |

---

## Implementierung

**Datei**: `/home/hoshhie/phonox/backend/api/routes.py`
**Zeilen**: 896-898

```python
# Search query should include catalog_number for specificity
search_query = f"{vinyl_record.artist} {vinyl_record.title} vinyl record price"
if vinyl_record.catalog_number:
    search_query += f" {vinyl_record.catalog_number}"
if vinyl_record.year:
    search_query += f" {vinyl_record.year}"

logger.info(f"Web search query: {search_query}")
```

**Status**: 🔴 **Nicht implementiert** - Katalognummer wird ignoriert
