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

TODO (Cursor): Implement all chart sections below.
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

# ---------------------------------------------------------------------------
# Activation value by plan
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Activation Value by Plan")
    # TODO: st.plotly_chart(charts.activation_value_by_plan_bar(metrics.get_activation_value_by_plan(df_filtered)), use_container_width=True)
    st.info("Implement `metrics.get_activation_value_by_plan()` and `charts.activation_value_by_plan_bar()` to enable this chart.")

with col_right:
    st.subheader("Meal Type Adoption")
    # TODO: st.plotly_chart(charts.meal_type_adoption_bar(metrics.get_meal_type_adoption(...)), use_container_width=True)
    st.info("Implement `metrics.get_meal_type_adoption()` and `charts.meal_type_adoption_bar()` to enable this chart.")

st.divider()

# Discount effectiveness
st.subheader("Discount Effectiveness")
# TODO: st.plotly_chart(charts.discount_effectiveness_table(metrics.get_discount_effectiveness(...)), use_container_width=True)
st.info("Implement `metrics.get_discount_effectiveness()` and `charts.discount_effectiveness_table()` to enable this chart.")

st.divider()

# Activation value trend + cuisine pie
col_left2, col_right2 = st.columns([3, 2])

with col_left2:
    st.subheader(f"Activation Value Trend (by {granularity})")
    # TODO: st.plotly_chart(charts.activation_trend_line(metrics.get_activation_trend(df_filtered, granularity=granularity)), use_container_width=True)
    st.info("Implement `metrics.get_activation_trend()` and `charts.activation_trend_line()` to enable this chart.")

with col_right2:
    st.subheader("Cuisine Breakdown")
    # TODO: st.plotly_chart(charts.cuisine_pie(dfs["meal_selections"]), use_container_width=True)
    st.info("Implement `charts.cuisine_pie()` to enable this chart.")
