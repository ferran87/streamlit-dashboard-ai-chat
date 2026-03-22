# HelloFresh Funnel Analytics Dashboard

A Streamlit multi-page analytics dashboard for HelloFresh's funnel optimisation team, featuring an AI chat assistant powered by Claude that answers questions using **live data only** — no hallucinations.

![Stack](https://img.shields.io/badge/Streamlit-1.55-red) ![Stack](https://img.shields.io/badge/Claude-Sonnet_4.6-blue) ![Stack](https://img.shields.io/badge/Plotly-6.6-purple) ![Stack](https://img.shields.io/badge/Pandas-2.3-green)

## Features

### Dashboard Pages

| Page | Description |
|---|---|
| **Overview** | KPI cards, funnel drop-off bar chart, activation type pie, weekly session trend |
| **Funnel Analysis** | Filterable CTR chart, drop-off waterfall, CVR by channel & device, time-on-step heatmap |
| **Activation Deep Dive** | Value by plan, meal type adoption, discount effectiveness table, activation trend, cuisine pie |
| **AI Chat** | Conversational analytics assistant with inline charts and streaming responses |

### AI Agent Architecture

The AI Chat uses a **unified agent** that combines data retrieval, benchmark validation, and insight generation in a single multi-tool exchange:

```
User question
  → Unified Agent (Claude Sonnet 4.6)
      ├─ Calls data tools (8 analytics queries)
      ├─ Validates metrics against hardcoded benchmarks
      ├─ Generates inline Plotly charts on request
      └─ Streams final response (~2s to first token)
```

**Anti-hallucination guarantees:**
1. Live KPI context injected into every system prompt
2. 8 data tools fetch exact numbers from DataFrames — no estimation allowed
3. `validate_metric` tool checks values against hardcoded benchmarks before any qualitative claim
4. `generate_chart` tool renders from real data — no invented numbers in visuals

### Data Model

Deterministic mock data (seed=42) modelling HelloFresh's acquisition funnel:

- **sessions** — 50,000 prospect browsing sessions across 6 channels, 3 devices, 8 countries
- **funnel_steps** — 7-step funnel (landing → confirmation) with step-level CTRs and time-on-step
- **activations** — ~5,000 conversions with plan, meals, discount, and basket value
- **meal_selections** — ~17,500 meal picks from a 30-meal catalogue, influenced by plan type
- **discounts** — 10-code catalogue with channel-targeted promotions and usage stats

## Quick Start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) (for the AI Chat page)

### Setup

```bash
# Clone the repo
git clone https://github.com/ferran87/streamlit-dashboard-ai-chat.git
cd streamlit-dashboard-ai-chat

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Generate mock data
python -m data.generate

# Set your Anthropic API key
# Create a .env file in the project root:
echo ANTHROPIC_API_KEY=sk-ant-your-key-here > .env

# Run the app
streamlit run app.py
```

The dashboard opens at [http://localhost:8501](http://localhost:8501).

## Project Structure

```
streamlit-dashboard-ai-chat/
├── app.py                      # Entry point — multi-page navigation
├── .streamlit/config.toml      # Dark theme config
├── requirements.txt
├── docs/PLAN.md                # Full implementation plan
├── data/
│   ├── generate.py             # Deterministic mock data generator (seed=42)
│   └── loader.py               # @st.cache_data loader
├── src/
│   ├── metrics.py              # Pure metric functions (no Streamlit imports)
│   ├── charts.py               # Plotly dark-themed figure builders
│   └── agents/
│       ├── unified.py          # Unified agent — streaming + inline charts
│       ├── orchestrator.py     # Original 3-agent orchestrator (legacy)
│       ├── analytics.py        # Analytics Agent (legacy)
│       ├── insights.py         # Insights Agent (legacy)
│       ├── tools.py            # Tool schemas (analytics + insights + chart)
│       └── context.py          # Live context builder + benchmark validation
└── pages/
    ├── 1_Overview.py
    ├── 2_Funnel_Analysis.py
    ├── 3_Activation_Deep_Dive.py
    └── 4_AI_Chat.py
```

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit 1.55 |
| Charts | Plotly 6.6 |
| AI | Anthropic Claude Sonnet 4.6 |
| Data | Pandas 2.3, NumPy, PyArrow |
| Mock data | Faker 34 |

## AI Chat — Example Questions

- "What is our overall conversion rate?"
- "Which channel has the highest CVR?"
- "Show me the funnel drop-off"
- "Is our discount strategy working?"
- "How does mobile CVR compare to desktop?"
- "Show activation trend over time"

## License

MIT
