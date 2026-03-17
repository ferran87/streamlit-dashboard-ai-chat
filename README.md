# Streamlit Dashboard + AI Chat

A Streamlit app with interactive data visualizations and an AI-powered chat that answers questions and generates insights from the underlying data. A mini metrics layer computes numbers in code so the LLM only narrates verified facts.

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/ferran87/streamlit-dashboard-ai-chat.git
cd streamlit-dashboard-ai-chat

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Generate mock data
python data/generate_data.py

# 6. Run the app
streamlit run run_app.py
```

## Project structure

```
├── run_app.py              # Streamlit entry point
├── pages/
│   ├── 1_Dashboard.py      # Data visualization dashboard
│   └── 2_AI_Chat.py        # AI chat for insights
├── src/
│   ├── data/               # Data loading and schema
│   ├── viz/                # Chart helpers (Plotly / Altair)
│   ├── chat/               # Context building and chat UI
│   ├── llm/                # LLM provider abstraction
│   └── metrics/            # Mini metrics layer (compute-then-narrate)
├── data/
│   ├── generate_data.py    # Mock data generator
│   └── raw/                # Generated parquet files
├── tests/                  # Unit tests
└── docs/                   # Documentation
```

## Pages

- **Dashboard** — Sidebar filters (date range, region, product) and 3-4 interactive Plotly charts: revenue over time, top products, revenue by region, and price distribution.
- **AI Chat** — Ask questions about the data. The app pre-computes metrics in code and injects only verified numbers into the LLM prompt, reducing hallucination.

## Hallucination reduction

The AI Chat uses a **compute-then-narrate** strategy:

1. User question arrives
2. Relevant metrics are computed in Python (pandas) via `src/metrics/`
3. Only the pre-computed results (not raw data) are injected into the LLM prompt
4. The LLM narrates and explains the numbers — it does not invent them

## Configuration

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | LLM backend (`openai`, `anthropic`, `azure`) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `DATA_PATH` | Override data directory | `./data/raw` |

## License

MIT
