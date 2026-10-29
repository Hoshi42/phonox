# Cost Model

Phonox incurs Anthropic API costs for image extraction, multi-image aggregation,
metadata enhancement, chat and market valuation. External web search can add
separate charges. The number of calls depends on the selected workflow and
whether tools or fallback searches are needed.

## Recommended models and published pricing

Verified against the official Anthropic model pages on **2026-10-29**.
Rates are USD per million tokens, before any applicable caching or batch
discounts. Haiku's published prices are starting rates, not a guaranteed rate
for every request or platform.

| Environment variable | Recommended model | Input / MTok | Output / MTok |
|---|---|---|---|
| `ANTHROPIC_CHAT_MODEL` | `claude-haiku-5-5` | From $0.10 | From $0.50 |
| `ANTHROPIC_VISION_MODEL` | `claude-sonnet-5-5` | $2.00 | $10.00 |
| `ANTHROPIC_AGGREGATION_MODEL` | `claude-sonnet-5-5` | $2.00 | $10.00 |
| `ANTHROPIC_ENHANCEMENT_MODEL` | `claude-opus-5-5` | $4.00 | $20.00 |

Sources:

- [Claude Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
- [Claude Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)
- [Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview)
- [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)

These are recommendations from `.env.example`, not a statement of which model
is currently running. The backend still has older code-level fallbacks, and the
current Compose file does not forward the model variables. See
[model configuration](../getting-started/configuration.md#vision--chat-models)
before estimating costs for a deployment. This documentation update does not
certify all vision, aggregation and enhancement paths against the new models.

## Which operations incur costs?

| Operation | Models selected by | Cost considerations |
|---|---|---|
| Per-image extraction | `ANTHROPIC_VISION_MODEL` | Image input, extraction prompt and response |
| Multi-image merging | `ANTHROPIC_AGGREGATION_MODEL` | Extracted metadata, merge prompt and response |
| Metadata enrichment / re-analysis | `ANTHROPIC_ENHANCEMENT_MODEL` | Existing metadata, new evidence and response |
| Chat | `ANTHROPIC_CHAT_MODEL` | Conversation context; tool use may require multiple model turns |
| Market valuation | `ANTHROPIC_CHAT_MODEL` | Search results, valuation prompt and response |
| Collection analysis | `ANTHROPIC_CHAT_MODEL` | Collection size, prompt and potentially long response |

Graph execution may include metadata synthesis or web-search fallback.
Consequently, a fixed "three calls per two-image analysis" is not a reliable
description of every complete request.

## Estimating a request

For each model call without cached tokens:

```text
cost_usd =
    input_tokens  / 1,000,000 * input_rate
  + output_tokens / 1,000,000 * output_rate
```

Add the costs of **all** model calls and any paid search services. For cached
requests, account for cache reads and writes at their applicable rates.
Use reported usage rather than assuming that a `max_tokens` limit is the
actual number of output tokens billed.

### Illustrative arithmetic, not measured Phonox usage

Suppose the Sonnet calls in one workflow together report **9,500 input tokens**
and **1,950 output tokens**. At the Sonnet 5.5 rates above:

| Component | Calculation | Cost |
|---|---|---|
| Input | 9,500 / 1,000,000 x $2 | $0.0190 |
| Output | 1,950 / 1,000,000 x $10 | $0.0195 |
| **Sonnet subtotal** | | **$0.0385** |

This excludes Opus enhancement, Haiku valuation/chat, tool loops, paid search
and retries. It is **not** a fixed price or upper bound for analysing a record.
For 100 identical Sonnet subtotals the arithmetic is $3.85; real costs vary
with image content, model selection, conversation history and output.

Token estimates from older models cannot simply be reused as measured 5.5
usage. Anthropic documents a newer tokenizer for Haiku 5.5; the same text can
use approximately 30% more tokens than on Haiku 4.5. Image-token handling also
needs to be checked against the selected model's current specifications.

## Keeping costs controlled

- Use Haiku 5.5 for routine chat and valuation; evaluate its output on your tasks.
- Start with Sonnet 5.5 for vision and aggregation. Evaluate Haiku 5.5 as a
  lower-cost vision alternative before relying on its extraction results.
- If Opus enhancement is unnecessary for your records, evaluate Sonnet 5.5.
  At the published rates it costs half as much for the same token counts.
- Avoid repeated full re-analysis when a targeted image or manual correction
  is sufficient.
- Reduce unnecessarily large images while keeping labels and barcodes legible.
  Do not assume a universal image-size saving across all models.
- Prompt caching and batch processing can reduce eligible API charges, but
  the application's normal interactive paths do not automatically gain every
  available discount. Phonox does not currently implement a batch mode.

## Search and monitoring

Tavily is billed separately from Anthropic under the account's search plan;
DuckDuckGo requests do not incur Anthropic token charges. Passing search
results to a model still consumes input tokens.

Monitor effective model IDs, provider-reported token usage and total spend in
the [Anthropic Console](https://console.anthropic.com/settings/usage).
Configure the available workspace spending controls and alerts for your account.
Do not use the former per-image or per-record estimates as billing guarantees.
