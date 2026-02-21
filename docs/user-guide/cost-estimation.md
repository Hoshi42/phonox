# Cost Estimation

Phonox uses the Anthropic Claude API to analyse your vinyl records. Understanding
how costs are calculated lets you plan your usage and keep bills predictable.

## How much does one analysis cost?

| Scenario | Typical cost |
|---|---|
| 1 image | ~$0.033 |
| **2 images (recommended)** | **~$0.057** |
| 3 images | ~$0.081 |

These figures are based on **Claude Sonnet 4.5** pricing ($3 / MTok input,
$15 / MTok output) with typical phone-camera JPEG photos (~1500 × 1500 px).

!!! tip "Two images is the sweet spot"
    One front-cover photo provides the artist and title. A second photo of the
    back or label adds the barcode, catalog number, label, and condition details.
    Beyond two images the marginal information gain is small while cost grows
    linearly.

## Where do the tokens go?

Each analysis with 2 images makes **3 Claude API calls**:

| Call | What it does | Est. input tokens | Est. output tokens |
|---|---|---|---|
| Vision – image 1 | Reads front cover, extracts artist / title | ~3,710 | ~750 |
| Vision – image 2 | Reads back cover / label, focused on barcode & catalog | ~3,755 | ~750 |
| Aggregation | Merges both results, resolves conflicts | ~960 | ~450 |
| **Total** | | **~8,425** | **~1,950** |

Image tokens dominate: each 1500 × 1500 px photo uses approximately
`(1500 × 1500) / 750 ≈ 3,000 tokens`.

## What triggers extra costs?

### Web search fallback (Tavily)
When visual analysis confidence is below 75 %, Phonox queries Tavily for
additional metadata. Tavily is a paid service billed separately to your Tavily
account — typically **$0.008–$0.015 per search query**.

DuckDuckGo (the supplementary search source) is **always free**.

If you see `websearch_fallback` in logs frequently, your images may be unclear;
try better-lit photos or add a back-cover image.

### Re-analysis
Re-analysing a record with additional images uses `claude-opus-4-5` for the
enhancement merge step. Opus 4.5 costs $5/$25 per MTok (input/output) — the
same quality tier as before but **3× cheaper** than the old Opus 4.1 default
($15/$75 MTok). A single re-analysis with 1 new image costs roughly
**$0.04–$0.05** depending on how much context is passed.

## Cost at scale

| Records catalogued | Estimated cost (2 images each) |
|---|---|
| 10 | $0.57 |
| 50 | $2.85 |
| 100 | $5.70 |
| 500 | $28.50 |
| 1,000 | $57 |

These are upper bounds assuming no prompt caching and no Batch API.

## How to reduce costs

### 1 — Use smaller images
Phonox automatically compresses images above 4.5 MB. You can help by
resizing JPEGs to around 1,200 × 1,200 px before uploading — this brings each
image to ~1,900 tokens and saves roughly 30 % per call.

### 2 — Use the Batch API (offline use)
The Anthropic Batch API offers a **50 % discount** on all tokens. It processes
requests asynchronously (results within 24 hours) rather than in real time.
This is not currently integrated into Phonox but can be enabled by setting
`ANTHROPIC_BATCH_MODE=true` in `.env` in a future release.

### 3 — Set `ANTHROPIC_VISION_MODEL` to a cheaper model
You can override the model used for vision extraction in your `.env`:

```env
ANTHROPIC_VISION_MODEL=claude-haiku-4-5-20251001
```

[Haiku 4.5](https://docs.anthropic.com/en/docs/about-claude/models/overview) costs $1/$5 per MTok (input/output), reducing each analysis
to around **$0.019 for 2 images**. It is less accurate on stylised or damaged
covers but works well for clear, high-resolution photos.

| Model | Cost / 2-image analysis | Accuracy |
|---|---|---|
| `claude-haiku-4-5` | ~$0.019 | Good (clear images) |
| `claude-sonnet-4-6` *(default)* | ~$0.057 | Excellent |
| `claude-sonnet-4-5` | ~$0.057 | Excellent |
| `claude-opus-4-5` | ~$0.190 | Best |

### 4 — Minimise re-analysis
Re-analysis is more expensive because it uses Opus for the enhancement step.
If you need to add a barcode or catalog number later, adding just one targeted
image costs less than a full two-image re-analysis.

## Monitoring your spend

Your API key spend is visible in the
[Anthropic Console](https://console.anthropic.com/settings/usage). Set a
**monthly spend limit** there to prevent unexpected bills — the console supports
hard caps per API key.

We recommend setting an alert at 80 % of your intended budget.

## Frequently asked questions

**Is there a free tier?**  
New Anthropic accounts receive a small credit (~$5) for testing. After that,
usage is pay-as-you-go with no minimum.

**Does Phonox send my images to any other third party?**  
Images are sent to Anthropic's API for analysis and (if web search is triggered)
the text-based search query (no image) is sent to Tavily. No images are stored
externally beyond Anthropic's standard API processing.

**Why does the cost vary from the $0.002/image figure I saw somewhere?**  
That figure predates the large chain-of-thought extraction prompts added in
v1.7+. The real per-image cost including prompts and output is closer to
**$0.027–$0.030** (Sonnet 4.5).
