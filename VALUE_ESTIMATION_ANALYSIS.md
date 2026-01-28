# Wertermittlung bei Bildanalyse - Problemanalyse

## Problem: "23" wird oft als Wert angezeigt

### Fundstelle: `estimate_vinyl_value()` in `backend/agent/metadata.py` (Zeile 319-408)

Die Funktion nutzt **Heuristiken** basierend auf:
- Erscheinungsjahr (year_multiplier)
- Label-Prestige (label_multiplier)
- Genre (genre_multiplier)

**Basis-Formel:**
```
Estimated Value = BASE (€10) × Year_Multiplier × Label_Multiplier × Genre_Multiplier
```

### Beispiel: Warum oft "23" herauskommt

1. **Base Value**: €10.00
2. **Typische Multiplikator-Kombination**:
   - Jahr 1979: `year_multiplier = 1.8` → €18
   - Label (z.B. "Warner"): `label_multiplier = 2.0` → €36
   - Genre (z.B. "Rock"): `genre_multiplier = 1.0` → €36
   - **Oder**:
   - Jahr 1985: `year_multiplier = 1.2` → €12
   - Label (Standard): `label_multiplier = 1.1` → €13.20
   - Genre: `genre_multiplier = 1.0` → €13.20
   - Nach Zufallslogik → ca. €23

### Probleme mit der aktuellen Implementierung

| Problem | Details |
|---------|---------|
| **Sehr simpel** | Nur 3 Faktoren (Jahr, Label, Genre) |
| **Fest codiert** | Label-Namen sind hardcoded mit `str.lower()` Vergleichen |
| **Keine Marktdaten** | Basiert auf Heuristiken, nicht auf realen Preisen |
| **Keine Condition** | Berücksichtigt den Zustand des Records nicht |
| **Keine Katalognummer** | Katalognummer wird nicht für Preissuche verwendet |
| **Statisch** | Gleiche Multiplikatoren für alle Alben eines Jahres |

---

## Warum "23" immer wieder erscheint

Die Funktion erzeugt oft Werte zwischen €15-€30 (die "23" Zone) weil:

1. **Häufig vorkommen**:
   - Jahr 1970-1985 (`year_multiplier = 1.2-1.8`)
   - Standard-Labels (`label_multiplier = 1.0-1.1`)
   - Rock/Pop (`genre_multiplier = 1.0`)
   - = €12-20 EUR

2. **Statistischer Durchschnitt**:
   - Die meisten Vinyl-Records im Register sind aus den 70er-80ern
   - Viele haben Standard-Labels
   - €23 ist praktisch der "Standardpreis" der Heuristik

---

## Lösungsansätze

### Option 1: Websearch direkt nutzen (Empfohlen ✅)
- **Nicht** die Bildanalyse für Wertermittlung nutzen
- **Direkt** in Websearch für Preisermittlung gehen
- `estimate_vinyl_value()` nur als Fallback verwenden

### Option 2: Heuristik verbessern (Teilweise)
- Mehr Faktoren einbeziehen:
  - Katalognummer (Rarity Score)
  - Condition/Zustand
  - Anzahl der Tracks
  - Label-Logo-Qualität (aus Vision-Analyse)

### Option 3: Hybrid-Ansatz (Beste Lösung)
- Bildanalyse: Schnelle Vorschätzung mit `estimate_vinyl_value()`
- Zeige dem Nutzer: "Geschätzter Wert: €23 (basierend auf Metadaten)"
- Button "🔍 Web Search": Führt zu genauerer Preisermittlung via Tavily
- Websearch ersetzt die Schätzung mit echten Marktdaten

---

## Aktuelle Datenfluss-Probleme

### Bei Upload/Bildanalyse:
```
Bild hochladen
↓
Vision-Analyse (extrahiert: Artist, Titel, Label, Katalognummer, Genres)
↓
estimate_vinyl_value() wird aufgerufen
↓
Heuristik-Berechnung (€10 × Multiplikatoren)
↓
Oft: €20-25 ("Magic 23 Zone")
↓
In Datenbank gespeichert als initial estimated_value_eur
```

### Problem:
- Nutzer sieht sofort einen Wert (z.B. €23)
- Denkt, das ist der echte Marktwert
- Der Wert ist aber nur eine **Schätzung ohne Marktdaten**

---

## Empfohlene Verbesserung

### Option 3 (Hybrid-Ansatz) implementieren:

1. **Bei Bildanalyse**: `estimate_vinyl_value()` aufrufen
   - Zeige Wert als "Vorschätzung" an (z.B. "€23 (Schätzung)")
   - Klar kennzeichnen: "Based on metadata, not market data"

2. **Websearch-Button**: Nutzer kann echte Marktdaten abrufen
   - Backend sucht mit Katalognummer + Artist + Titel
   - Claude analysiert echte Marktpreise
   - Zeigt realistische Werte mit Preisrange

3. **Anzeige im UI**:
   ```
   Geschätzter Wert: €23 (Vorschätzung basierend auf Metadaten)
   
   [🔍 Web Search] → Sucht echte Marktdaten
   
   Nach Web Search:
   Marktbasierter Wert: €28-35 (aktuellen Marktpreisen)
   ```

---

## Implementierungsschritte

### Schritt 1: UI klarstellen (Vordergrund)
In `VinylCard.tsx`:
- Zeige "€23 (estimated from metadata)" beim initialen Laden
- Unterscheide deutlich von "Market-based value" nach Web Search

### Schritt 2: `estimate_vinyl_value()` verbessern (Backend)
Optionale Multiplikatoren erweitern:
```python
def estimate_vinyl_value(
    artist: str,
    title: str,
    year: Optional[int] = None,
    label: Optional[str] = None,
    genres: Optional[List[str]] = None,
    catalog_number: Optional[str] = None,  # NEU
    condition_score: Optional[float] = None,  # NEU (0.0-1.0)
) -> Dict[str, float]:
    # Existing code...
    
    # NEW: Catalog number rarity multiplier
    if catalog_number and len(catalog_number) > 3:
        # Longer catalog numbers suggest more specific editions
        catalog_multiplier = 1.15
    
    # NEW: Condition multiplier
    condition_multiplier = 1.0
    if condition_score:
        # Better condition = higher value
        condition_multiplier = 0.5 + (condition_score * 1.5)
    
    estimated_eur *= catalog_multiplier * condition_multiplier
```

### Schritt 3: Websearch priorisieren (Wichtig!)
- Websearch muss die Bildanalyse-Schätzung ersetzen
- Nicht additiv sein (wie derzeit)
- Nutzer wählt bewusst: "Möchte ich Web Search?"

---

## Zusammenfassung

| Aspekt | Status | Empfehlung |
|--------|--------|------------|
| **Ursache "23"** | ✅ Analysiert | Heuristik-Berechnung mit Standard-Multiplikatoren |
| **Problemlösung** | ❌ Noch nicht | Hybrid-Ansatz: Vorschätzung + Web Search |
| **UI-Klarheit** | ❌ Fehlt | Kennzeichne klar: "Schätzung vs. Marktwert" |
| **Katalognummer Nutzung** | ❌ Nicht genutzt | Im Websearch verwenden (bereits implementiert!) |
| **Condition-Faktor** | ❌ Fehlt | In `estimate_vinyl_value()` einbauen |

---

## Nächste Schritte

1. ✅ **Katalognummer in Websearch nutzen** (bereits gemacht!)
2. 🔲 **UI klarstellen**: "Schätzung" vs. "Marktwert"
3. 🔲 **`estimate_vinyl_value()` mit Condition erweitern** (optional)
4. ✅ **Websearch implementiert und funktioniert** (bereits gemacht!)
