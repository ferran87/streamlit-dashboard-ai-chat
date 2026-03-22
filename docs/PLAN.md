# HelloFresh Funnel Analytics Dashboard — Implementation Plan

## Context

Build a Streamlit multi-page funnel analytics dashboard for HelloFresh's funnel optimization team. The app uses a realistic mock data model based on prospect sessions, activations, funnel step CTRs, meal selections, discounts, and activation value. The AI chat uses a **multi-agent architecture** — an Orchestrator routes questions to a specialized Analytics Agent (data queries) and an Insights Agent (validation + synthesis) — to maximize accuracy and eliminate hallucinations.

**Stack:** Streamlit 1.55.0, Anthropic SDK 0.85.0 (`claude-sonnet-4-6`), Pandas 2.3.3, Plotly 6.6.0, Faker, NumPy, PyArrow — all in `.venv`.

---

## Multi-Agent Architecture (AI Chat)

Three Claude agent roles, each with a distinct system prompt and tool set:

### 1. Orchestrator Agent
- **Role**: Receives the user question, decomposes it, routes sub-tasks to Analytics Agent and/or Insights Agent, synthesizes their outputs into a final response.
- **Tools**: `delegate_to_analytics(question)`, `delegate_to_insights(analytics_result, original_question)`
- **System prompt**: Knows the full schema, knows which agent handles which query type. Instructs sub-agents to never invent numbers.

### 2. Analytics Agent
- **Role**: Data retrieval specialist. Answers only with exact numbers from the data model. Never interprets or recommends — only fetches.
- **Tools**: 8 query tools (see below). Can call multiple tools per turn.
- **System prompt**: "You are an analytics engineer. Return only facts from tools. If a number is not in the tool output, state you cannot answer, not an estimate."

### 3. Insights Agent
- **Role**: Receives analytics results and generates grounded insights. Compares metrics to known benchmarks (injected as static context), flags anomalies, surfaces recommendations — but always tied to specific numbers from the Analytics Agent output.
- **Tools**: `validate_metric(metric_name, value, benchmark)` — checks if a value is in expected range and returns interpretation.
- **System prompt**: "You are an insights strategist. You ONLY interpret numbers given to you. You NEVER invent data. Reference every claim with the exact figure provided."

### Agent Flow

```
User question
    → Orchestrator identifies query type(s)
    → Calls Analytics Agent → gets exact numbers
    → Calls Insights Agent with those numbers → gets interpretation
    → Synthesizes final response with cited figures
```

The Orchestrator can also answer directly from injected context for simple KPI lookups, skipping sub-agents.

---

## File Structure

```
streamlit-dashboard-ai-chat/
├── app.py
├── .streamlit/config.toml
├── requirements.txt
├── docs/
│   └── PLAN.md
├── data/
│   ├── __init__.py
│   ├── generate.py          # Deterministic Faker data gen → parquet
│   └── loader.py            # @st.cache_data load_all() → dict of DataFrames
├── src/
│   ├── __init__.py
│   ├── metrics.py           # Pure metric computation (no Streamlit)
│   ├── charts.py            # Plotly figure builders
│   └── agents/
│       ├── __init__.py
│       ├── orchestrator.py  # Orchestrator agent loop
│       ├── analytics.py     # Analytics Agent (data tools + loop)
│       ├── insights.py      # Insights Agent (validation + synthesis)
│       ├── tools.py         # Tool definitions (TOOLS lists per agent)
│       └── context.py       # build_context_block() — shared injected context
└── pages/
    ├── 1_Overview.py
    ├── 2_Funnel_Analysis.py
    ├── 3_Activation_Deep_Dive.py
    └── 4_AI_Chat.py
```

---

## HelloFresh Data Model (mock, seed=42, ~50k sessions over 12 months)

### `sessions.parquet` — one row per prospect session

| Column | Type | Values |
|---|---|---|
| session_id | str (UUID) | PK |
| visitor_id | str (UUID) | same visitor may have multiple sessions |
| session_date | date | last 12 months |
| session_datetime | datetime | with hour (weighted: 7–22h) |
| channel | str | organic_search, paid_search, paid_social, email, referral, direct |
| device | str | mobile(55%), desktop(35%), tablet(10%) |
| country | str | DE, US, GB, AU, NL, AT, BE, CH — weighted by market size |
| utm_source | str | google, facebook, instagram, newsletter, partner, None |
| utm_campaign | str | brand, non_brand, retargeting, welcome_back, None |
| landing_page | str | homepage, menu, offer, blog, referral_landing |
| activated | bool | True if session → activation |

### `funnel_steps.parquet` — one row per (session, step)

Each session has rows for steps it reached. Steps in order:

| Step | step_order |
|---|---|
| landing | 1 |
| menu_browse | 2 |
| plan_selection | 3 |
| delivery_settings | 4 |
| account_creation | 5 |
| payment | 6 |
| confirmation | 7 |

| Column | Type | Values |
|---|---|---|
| session_id | str | FK |
| step_name | str | see above |
| step_order | int | 1–7 |
| reached | bool | always True (only rows for reached steps) |
| exited | bool | True if the user left at this step |
| time_on_step_seconds | int | Poisson-distributed per step |
| ctr | float | computed: sessions reaching step N+1 / sessions reaching step N |

Baseline CTRs (with noise): landing→menu 65%, menu→plan 45%, plan→delivery 70%, delivery→account 80%, account→payment 75%, payment→confirmation 82%.

### `activations.parquet` — one row per conversion

| Column | Type | Values |
|---|---|---|
| activation_id | str (UUID) | PK |
| session_id | str | FK |
| visitor_id | str | FK |
| activation_date | date | |
| activation_type | str | first_order(70%), reactivation(20%), referral(8%), gift(2%) |
| plan_name | str | classic, veggie, family, protein, low_calorie, quick_easy |
| meals_per_week | int | 2, 3, 4, 5 |
| portions | int | 2, 4 |
| activation_value | float | basket value in $ (meals_per_week × portions × meal_price × discount_factor) |
| has_discount | bool | |
| discount_code | str\|None | |
| discount_type | str\|None | percentage, fixed_amount, free_box, None |
| discount_amount | float | $ off applied |
| discount_pct | float | effective % discount |

### `meal_selections.parquet` — meals chosen at activation

| Column | Type | Values |
|---|---|---|
| activation_id | str | FK |
| meal_id | str | from fixed catalogue of 30 meals |
| meal_name | str | e.g. "Honey Garlic Chicken", "Mushroom Risotto" |
| meal_type | str | classic, veggie, protein, low_cal, quick, family |
| price_per_serving | float | $4.50–$9.50 |
| cuisine | str | italian, asian, mexican, american, mediterranean |

### `discounts.parquet` — discount catalogue + usage

| Column | Type | Values |
|---|---|---|
| discount_code | str | e.g. "WELCOME50", "FREEBOX", "20OFF" |
| discount_type | str | percentage, fixed_amount, free_box |
| discount_value | float | 10–60% or $5–$30 fixed |
| channel_target | str | channel this promo is associated with |
| activations_used | int | count (derived at generation) |
| avg_activation_value | float | avg basket when this code used |

---

## Key Metrics (`src/metrics.py`)

### Funnel metrics
- `get_funnel_ctr(df_funnel, channel=None, device=None, date_range=None)` → DF `[step, sessions_reached, ctr_to_next, exit_rate]`
- `get_overall_conversion_rate(df_sessions, filters)` → float
- `get_conversion_by_channel(df_sessions, df_activations)` → DF `[channel, sessions, activations, cvr]`
- `get_conversion_by_device(...)` → same shape
- `get_funnel_drop_off(df_funnel)` → DF `[step, dropped_sessions, drop_pct]`

### Activation metrics
- `get_activation_value_by_plan(df_activations)` → DF `[plan_name, count, avg_value, total_value]`
- `get_activation_value_by_type(df_activations)` → DF `[activation_type, count, avg_value, discount_rate]`
- `get_discount_effectiveness(df_activations, df_discounts)` → DF `[discount_code, used_count, avg_value_with, avg_value_without, uplift_pct]`
- `get_meal_type_adoption(df_meals, df_activations)` → DF `[meal_type, activation_count, pct_of_activations]`
- `get_activation_trend(df_activations, granularity="week")` → DF `[period, activations, avg_value, total_revenue]`

### Session metrics
- `get_session_volume_trend(df_sessions)` → DF `[week, sessions, activated_sessions, cvr]`
- `get_kpi_summary(all_dfs)` → flat dict: total sessions, total activations, overall CVR, avg activation value, top channel, best/worst step CTR

---

## Analytics Agent Tools (`src/agents/tools.py`)

| Tool | Underlying metric | Use case |
|---|---|---|
| `get_funnel_ctr` | `metrics.get_funnel_ctr` | CTR by step, drop-off analysis |
| `get_conversion_by_channel` | `metrics.get_conversion_by_channel` | Which channel converts best |
| `get_conversion_by_device` | `metrics.get_conversion_by_device` | Mobile vs desktop CVR |
| `get_activation_value_breakdown` | `metrics.get_activation_value_by_plan` + by_type | Revenue by plan / activation type |
| `get_discount_analysis` | `metrics.get_discount_effectiveness` | Discount ROI and impact |
| `get_meal_type_performance` | `metrics.get_meal_type_adoption` | Meal type popularity at activation |
| `get_activation_trend` | `metrics.get_activation_trend` | Volume and value over time |
| `get_kpi_summary` | `metrics.get_kpi_summary` | Top-level snapshot |

---

## Insights Agent — Benchmarks

Static benchmarks injected into the Insights Agent system prompt (hardcoded — cannot be manipulated via data):

```
HelloFresh Funnel Benchmarks (industry / internal estimates):
- Overall CVR (session → activation): 2–5% healthy, <1.5% poor, >6% excellent
- Landing→Menu CTR: 60–70% healthy
- Plan Selection→Payment CTR: >65% healthy
- Mobile CVR typically 30–40% lower than desktop — expected
- First order activations: 65–75% of total is healthy
- Avg discount depth: 25–40% of basket is sustainable
- Free box offers typically yield 15–25% higher activation rate but lower LTV
- Classic plan dominates at ~40–50% of activations, Veggie 15–25%
```

---

## Context Injection (`src/agents/context.py`)

Injected as `system=` in every agent API call, computed fresh per user message from live DataFrames:

```
=== HELLOFRESH FUNNEL DATA — LIVE CONTEXT ===
Period: {date_range} | {total_sessions:,} sessions | {total_activations:,} activations

TOP-LINE KPIs
Overall CVR:          {cvr:.2f}%
Avg Activation Value: ${avg_value:.2f}
Total Revenue:        ${total_revenue:,.0f}
Top Channel:          {top_channel} ({top_channel_cvr:.1f}% CVR)
Worst Funnel Step:    {worst_step} (CTR: {worst_ctr:.1f}%)

FUNNEL STEPS (last 30 days)
landing → menu:         {ctr_1:.1f}%
menu → plan selection:  {ctr_2:.1f}%
plan → delivery:        {ctr_3:.1f}%
delivery → account:     {ctr_4:.1f}%
account → payment:      {ctr_5:.1f}%
payment → confirmation: {ctr_6:.1f}%

TOP ACTIVATION PLANS
{plan breakdown: name, count, avg_value}

DISCOUNT USAGE
{pct with discount:.0f}% of activations used a discount | Avg discount: {avg_disc_pct:.0f}%
```

---

## Pages

### `pages/1_Overview.py`
- 4 KPI metric cards: Overall CVR, Total Activations, Avg Activation Value, Top Channel CVR
- Funnel bar chart (sessions reached per step, with drop-off waterfall)
- Weekly activation trend (line chart)
- Activation split by type (pie)

### `pages/2_Funnel_Analysis.py`
- Sidebar filters: date range, channel, device
- Funnel step CTR chart (horizontal bar — green if healthy, red if below benchmark)
- Drop-off by step (waterfall)
- CVR by channel (grouped bar: sessions vs activations)
- CVR by device (bar)
- Time on step heatmap (step × device)

### `pages/3_Activation_Deep_Dive.py`
- Sidebar filters: activation type, plan, discount presence
- Activation value by plan (bar)
- Meal type adoption (horizontal bar)
- Discount effectiveness table (code, usage count, avg value with/without discount, uplift %)
- Activation value trend (line)
- Cuisine breakdown (pie)

### `pages/4_AI_Chat.py`
- `st.chat_input` + `st.session_state.messages` for history
- Shows tool calls inside `st.status()` (e.g. "Analytics Agent → calling get_funnel_ctr")
- Calls `orchestrator.run_turn(messages, dfs, status)` → returns `(text, updated_messages)`
- Renders final response with `st.markdown()`

---

## Implementation Order

```
Step 1:  data/generate.py           — HelloFresh mock data, 5 parquets
Step 2:  src/metrics.py             — Pure metric functions (no Streamlit imports)
Step 3:  data/loader.py             — @st.cache_data load_all()
Step 4:  src/charts.py              — Plotly builders per schema above
Step 5:  src/agents/tools.py        — TOOLS lists for Analytics Agent
Step 6:  src/agents/context.py      — build_context_block()
Step 7:  src/agents/analytics.py    — Analytics Agent loop (query tools)
Step 8:  src/agents/insights.py     — Insights Agent loop (validate + synthesize)
Step 9:  src/agents/orchestrator.py — Orchestrator: decomposes → delegates → synthesizes
Step 10: app.py + .streamlit/config.toml — Navigation + dark theme
Step 11: pages/1_Overview.py
Step 12: pages/2_Funnel_Analysis.py
Step 13: pages/3_Activation_Deep_Dive.py
Step 14: pages/4_AI_Chat.py
Step 15: requirements.txt
```

---

## Anti-Hallucination — Three-Layer Defense

1. **Context injection**: Current KPIs + funnel CTRs + top plans always in system prompt. LLM answers common questions directly from injected facts.
2. **Analytics Agent with tools**: Fetches exact numbers from DataFrames on demand. System prompt explicitly forbids estimation.
3. **Insights Agent with benchmarks**: Interprets only numbers passed to it, compared against hardcoded benchmarks. Cannot invent a conversion rate.

---

## Verification

1. `python -m data.generate` → 5 parquet files created in `data/raw/`
2. `streamlit run app.py` → all 4 pages load without import errors
3. Overview: KPI cards show non-zero values, funnel chart shows all 7 steps
4. Funnel Analysis: channel filter updates CVR chart, step bar colors reflect benchmarks
5. Activation Deep Dive: discount table shows uplift values, meal type bars render
6. AI Chat test questions:
   - "What is our overall conversion rate?" → answered from injected context (no tool call)
   - "Which channel has the highest CVR on mobile?" → Analytics Agent calls `get_conversion_by_device`, Insights Agent interprets
   - "Is our discount strategy working?" → Analytics Agent calls `get_discount_analysis`, Insights Agent compares to benchmarks

---

## Key Pitfalls

- **Funnel step rows — reached only**: Sessions that exit at step 3 have rows for steps 1–3 only. CTR must be computed from row counts, not a stored field.
- **Tool result batching**: All tool results in one agent turn → single `"user"` message with list of `tool_result` blocks. Never one message per result.
- **Orchestrator message isolation**: Each sub-agent call uses a fresh `messages` list. Only the Orchestrator's list persists in `st.session_state` across user turns.
- **Discount data sparsity**: ~40% of activations have no discount — null-handling required in effectiveness calculations.
- **Benchmark immutability**: Benchmarks are hardcoded strings in the Insights Agent system prompt, not fetched from data. Intentional — prevents data-driven manipulation.
