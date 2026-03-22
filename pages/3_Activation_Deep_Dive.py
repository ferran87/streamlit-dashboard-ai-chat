"""
pages/3_Activation_Deep_Dive.py
--------------------------------
Activation & discount analysis with interactive filters.

Sidebar filters: activation type, plan, discount presence
Charts:
  - Activation value by plan (bar)
  - Meal type adoption (horizontal bar)
  - Discount effectiveness table
  - Activation value trend (line)
  - Cuisine breakdown (pie)
"""

import streamlit as st
from data.loader import load_all
from src import metrics, charts

st.title("🎯 Activation Deep Dive")
st.caption("Revenue breakdown by plan, meal type, and discount strategy")

dfs = load_all()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    act_type_filter = st.selectbox(
        "Activation Type",
        ["All", "first_order", "reactivation", "referral", "gift"]
    )
    plan_filter = st.selectbox(
        "Plan",
        ["All", "classic", "veggie", "family", "protein", "low_calorie", "quick_easy"]
    )
    discount_filter = st.selectbox(
        "Discount",
        ["All", "With discount", "Without discount"]
    )
    granularity = st.radio("Trend granularity", ["week", "month"], horizontal=True)

# Apply filters
df_act = dfs["activations"].copy()
if act_type_filter != "All":
    df_act = df_act[df_act["activation_type"] == act_type_filter]
if plan_filter != "All":
    df_act = df_act[df_act["plan_name"] == plan_filter]
if discount_filter == "With discount":
    df_act = df_act[df_act["has_discount"]]
elif discount_filter == "Without discount":
    df_act = df_act[~df_act["has_discount"]]

if df_act.empty:
    st.warning("No activations match the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Activation value by plan + Meal type
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Activation Value by Plan")
    plan_df = metrics.get_activation_value_by_plan(df_act)
    st.plotly_chart(charts.activation_value_by_plan_bar(plan_df), use_container_width=True)

with col_right:
    st.subheader("Meal Type Adoption")
    meal_df = metrics.get_meal_type_adoption(dfs["meal_selections"], df_act)
    st.plotly_chart(charts.meal_type_adoption_bar(meal_df), use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Discount effectiveness
# ---------------------------------------------------------------------------
st.subheader("Discount Effectiveness")
disc_df = metrics.get_discount_effectiveness(df_act, dfs["discounts"])
st.plotly_chart(charts.discount_effectiveness_table(disc_df), use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Activation value trend + cuisine pie
# ---------------------------------------------------------------------------
col_left2, col_right2 = st.columns([3, 2])

with col_left2:
    st.subheader(f"Activation Value Trend (by {granularity})")
    trend_df = metrics.get_activation_trend(df_act, granularity=granularity)
    st.plotly_chart(charts.activation_trend_line(trend_df), use_container_width=True)

with col_right2:
    st.subheader("Cuisine Breakdown")
    filtered_meals = dfs["meal_selections"][
        dfs["meal_selections"]["activation_id"].isin(df_act["activation_id"])
    ]
    st.plotly_chart(charts.cuisine_pie(filtered_meals), use_container_width=True)
