# Cost Model

This page documents exactly how Anthropic API costs are incurred during a
Phonox analysis pipeline, including token counts derived from the actual prompts
in the codebase.

Pricing source: [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing)
(verified 2026-02-21).

## Model configuration

Models are set in `.env` and override the defaults shown here.

| `.env` variable | Default | Used for |
|---|---|---|
| `ANTHROPIC_VISION_MODEL` | `claude-sonnet-4-6` | Vision extraction — both per-image calls |
| `ANTHROPIC_AGGREGATION_MODEL` | `claude-sonnet-4-6` | Multi-image aggregation merge |
| `ANTHROPIC_ENHANCEMENT_MODEL` | `claude-opus-4-5` | Re-analysis enhancement merge |

## Current API pricing (standard, no caching)

| Model | Input / MTok | Output / MTok |
|---|---|---|
| `claude-sonnet-4-6` *(default vision/agg)* | $3.00 | $15.00 |
| `claude-sonnet-4-5` | $3.00 | $15.00 |
| `claude-opus-4-5` *(default enhancement)* | $5.00 | $25.00 |
| `claude-opus-4-1` | $15.00 | $75.00 |
| `claude-haiku-4-5` | $1.00 | $5.00 |

## Initial analysis — call-by-call breakdown (2 images)

### Graph execution path

```
START → validate_images → extract_features
      → vision_extraction  ← 2× Claude API calls
      → lookup_metadata     (Discogs + MusicBrainz — free,
                             + Spotify via Tavily/DDG — may cost)
      → [websearch_fallback if confidence < 0.75]
      → confidence_gate → END
```

### Call 1 — Vision extraction, Image 1

**Model:** `ANTHROPIC_VISION_MODEL` (default: Sonnet 4.6)  
**`max_tokens`:** 1,500  
**`temperature`:** 0.3

| Input component | Tokens |
|---|---|
| System prompt (expert cataloguer) | 120 |
| Position guidance (Image 1 of 2) | 470 |
| Chain-of-thought extraction prompt | 660 |
| Image 1 at ≈1,500 × 1,500 px (`(1500×1500)/750`) | ~3,000 |
| **Total input** | **~4,250** |
| **Output** (CoT reasoning + JSON, typical) | **~750** |

### Call 2 — Vision extraction, Image 2

**Model:** `ANTHROPIC_VISION_MODEL` (default: Sonnet 4.6)  
**`max_tokens`:** 1,500  
**`temperature`:** 0.3

| Input component | Tokens |
|---|---|
| System prompt | 120 |
| Position guidance (Image 2 of 2, incl. previous artist/title) | 510 |
| Chain-of-thought extraction prompt | 660 |
| Image 2 at ≈1,500 × 1,500 px | ~3,000 |
| **Total input** | **~4,290** |
| **Output** (CoT reasoning + JSON, typical) | **~750** |

### Call 3 — Multi-image aggregation

**Model:** `ANTHROPIC_AGGREGATION_MODEL` (default: Sonnet 4.6)  
**`max_tokens`:** 1,500  
**`temperature`:** 0.3  
**Vision:** No (text-only)

| Input component | Tokens |
|---|---|
| Aggregation prompt template | 600 |
| 2 × JSON result blobs (per-image metadata) | ~360 |
| **Total input** | **~960** |
| **Output** (merged JSON + reasoning field) | **~450** |

---

### Total — initial analysis, 2 images (Sonnet 4.6)

| | Tokens | Rate | Cost |
|---|---|---|---|
| Input | 9,500 | $3.00 / MTok | $0.0285 |
| Output | 1,950 | $15.00 / MTok | $0.0293 |
| **Total** | **11,450** | | **$0.0578** |

Output tokens drive ~51 % of the bill because every vision call includes a
full chain-of-thought reasoning trace before emitting the JSON payload.

## Image token formula

```
tokens = (width_px × height_px) / 750
```

Claude scales down any image whose long edge exceeds 1,568 px, so the maximum
cost per image is:

```
(1568 × 1568) / 750 ≈ 3,280 tokens
```

Phonox additionally compresses base64 strings above 4.5 MB before sending
(`compress_image_to_claude_limits()` in `vision.py`).

### Image size sensitivity

| Photo resolution | Tokens / image | Δ cost vs. 1,500 px |
|---|---|---|
| 800 × 800 px (compressed) | 853 | −$0.012 |
| 1,200 × 1,200 px | 1,920 | −$0.005 |
| **1,500 × 1,500 px (typical)** | **3,000** | **baseline** |
| 1,568 × 1,568 px (API max) | 3,278 | +$0.001 |

## Re-analysis — additional call

Re-analysis via `/api/v1/reanalyze/{id}` fires:

1. One vision extraction call per **new** image (Sonnet 4.6, same as above)
2. One enhancement merge call (`ANTHROPIC_ENHANCEMENT_MODEL`, default **Opus 4.5**)

### Enhancement merge call (Opus 4.5)

| Input component | Tokens |
|---|---|
| Enhancement prompt + existing metadata JSON | ~700 |
| New metadata JSON from new image(s) | ~300 |
| **Total input** | **~1,000** |
| **Output** (change log + merged metadata JSON) | **~400** |

| | Tokens | Rate | Cost |
|---|---|---|---|
| Opus 4.5 input | 1,000 | $5.00 / MTok | $0.005 |
| Opus 4.5 output | 400 | $25.00 / MTok | $0.010 |
| 1 × Sonnet 4.6 vision call | 5,000 | mixed | ~$0.030 |
| **Re-analysis total** | | | **~$0.045** |

!!! tip "Opus 4.5 is 3× cheaper than the previous Opus 4.1 default"
    Opus 4.5 ($5/$25 MTok) replaced Opus 4.1 ($15/$75 MTok) as the default
    enhancement model in v1.9.3, reducing re-analysis cost by ~40 %.
    To reduce cost further, switch to Sonnet 4.6:
    ```env
    ANTHROPIC_ENHANCEMENT_MODEL=claude-sonnet-4-6
    ```

## Websearch fallback

The `websearch_fallback` node runs when preliminary confidence < 0.75.
It uses Tavily (paid) and/or DuckDuckGo (free) — no Anthropic calls.

| Service | Cost |
|---|---|
| Tavily (text search) | ~$0.008–$0.015 / query (billed to your Tavily key) |
| DuckDuckGo | Free |

Phonox supplements Tavily with DuckDuckGo whenever Tavily returns fewer than
`WEBSEARCH_MIN_RESULTS_THRESHOLD` results (default: 4).

## Scale projections

Figures use default models, 2 images per record, no Batch API discount.

| Records | Input tokens | Output tokens | Cost |
|---|---|---|---|
| 10 | 95,000 | 19,500 | $0.58 |
| 100 | 950,000 | 195,000 | $5.78 |
| 1,000 | 9,500,000 | 1,950,000 | $57.80 |
| 10,000 | 95,000,000 | 19,500,000 | $578 |

## Cost optimisation options

| Technique | Saving | Notes |
|---|---|---|
| Batch API (50 % discount) | ~50 % | Async; 24 h turnaround |
| Prompt caching on static prompts | ~15 % | ~1,250 tokens are identical every call |
| Switch vision model → Haiku 4.5 | ~67 % | Lower accuracy on difficult covers |
| Resize images to 1,000 px | ~30 % | Minimal accuracy loss |
| Switch enhancement → Sonnet 4.5 | ~80 % on re-analysis | Slight quality reduction on conflict resolution |

### Prompt caching opportunity

The system prompt (120 tokens) and the extraction prompt body (660 tokens) are
identical on every vision call. Enabling prompt caching (5-minute TTL) would
cache ~780 tokens per call at 0.1× read cost, saving:

```
780 tokens × $3.00/MTok × 0.9 discount × N calls
= $0.0007 saved per record (both vision calls)
```

Small per-record but meaningful at thousands of analyses.
