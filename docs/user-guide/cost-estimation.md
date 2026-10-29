# Cost Estimation

Phonox uses the Anthropic Claude API for image analysis, metadata enhancement,
market valuation and chat. Usage is billed by the effective model and the
tokens processed, not at a fixed price per record.

## Recommended models

The recommendations in `.env.example` are:

| Task | Model | Published input / output price per million tokens |
|---|---|---|
| Chat and market valuation | `claude-haiku-5-5` | From $0.10 / $0.50 |
| Image analysis and multi-image aggregation | `claude-sonnet-5-5` | $2 / $10 |
| Metadata enhancement | `claude-opus-5-5` | $4 / $20 |

Prices are in USD, checked on **2026-10-29** against the official
[Haiku](https://platform.claude.com/docs/en/models/haiku-5-5/overview),
[Sonnet](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) and
[Opus](https://platform.claude.com/docs/en/models/opus-5-5/overview) pages.
Haiku prices are published starting rates; check the rates applicable to your
request and platform.

!!! warning "Recommendations are not necessarily the active configuration"
    The backend must receive the model variables explicitly. Older code-level
    fallbacks remain, and the current Compose file does not yet forward these
    variables. Follow the
    [configuration guide](../getting-started/configuration.md#vision--chat-models)
    before assuming the new rates apply to your deployment.

## How much does an analysis cost?

There is no verified fixed 5.5 price per image or complete record analysis.
The cost depends on:

- The models actually used for each step.
- Image size and the selected model's image-token rules.
- Prompt length, extracted metadata and generated output.
- Additional enhancement, valuation, chat tool turns and retries.
- Paid web search, billed separately by the search provider.

For illustration only, **9,500 input tokens and 1,950 output tokens** on
Sonnet 5.5 cost **$0.0385** at the published rates. This is a Sonnet subtotal,
not a measured complete Phonox analysis and not an upper bound.

Older estimates should not be carried over unchanged: model tokenizers and
processing rules can differ. The [technical cost model](../architecture/cost-model.md)
explains the calculation and its assumptions.

## How to reduce costs

### 1. Use the recommended lower-cost chat model

Set this in the backend environment:

```env
ANTHROPIC_CHAT_MODEL=claude-haiku-5-5
```

Chat cost also depends on conversation length and whether tools trigger
additional model turns.

### 2. Evaluate lower-cost alternatives for analysis

For lower-cost image extraction, evaluate:

```env
ANTHROPIC_VISION_MODEL=claude-haiku-5-5
```

Check artist, pressing, barcode and condition accuracy on representative
records before switching. There is no project benchmark establishing identical
quality across models.

For less expensive metadata enhancement, evaluate:

```env
ANTHROPIC_ENHANCEMENT_MODEL=claude-sonnet-5-5
```

At the published rates, Sonnet costs half as much as Opus 5.5 for the same
number of input and output tokens.

### 3. Avoid unnecessary work

Use clear, well-lit cover and label photos. Keep barcodes readable and avoid
unnecessarily large files. Add a targeted photo or edit a known field instead
of repeatedly running a full analysis.

### 4. Do not assume batch or caching discounts

Anthropic offers discounts for eligible batch processing and caching, but
Phonox does not currently implement a batch mode. Setting an undocumented
batch environment variable does not enable it.

## Monitor actual spending

Check model usage and spending in the
[Anthropic Console](https://console.anthropic.com/settings/usage).
Configure the spending controls and alerts available for your workspace.
Tavily charges are separate and depend on your Tavily plan.

The recommendations and published rates above are not an end-to-end
compatibility certification of all analysis paths with Claude 5.5.
