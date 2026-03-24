import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Garden Bloom Timeline", layout="wide")
st.title("Garden Bloom Timeline")

@st.cache_data
def load_data():
    return pd.read_csv("garden_timelines.csv")

df = load_data()

YEAR = 2026

def parse_mmdd(date_str):
    return pd.to_datetime(f"{YEAR}-{date_str}", format="%Y-%m-%d")

df["bloom_date_dt"] = df["bloom_date"].apply(parse_mmdd)
df["full_bloom_dt"] = df["full_bloom"].apply(parse_mmdd)
df["bloom_end_dt"] = df["bloom_end"].apply(parse_mmdd)

def bloom_intensity(current_date, start, peak, end):
    if current_date < start or current_date > end:
        return 0.0

    if current_date <= peak:
        rise_total = (peak - start).days
        if rise_total == 0:
            return 1.0
        t = (current_date - start).days / rise_total
        return 0.5 - 0.5 * np.cos(np.pi * t)

    fall_total = (end - peak).days
    if fall_total == 0:
        return 1.0
    t = (current_date - peak).days / fall_total
    return 0.5 + 0.5 * np.cos(np.pi * t)

# -----------------------------
# FLOWER SELECTION
# -----------------------------
flower_options = df["flower name"].tolist()

selected_flowers = st.sidebar.multiselect(
    "Choose flowers for your garden",
    options=flower_options,
    default=[]
)

garden_df = df[df["flower name"].isin(selected_flowers)].copy()

if garden_df.empty:
    st.info("Choose flowers from the sidebar.")
    st.stop()

# -----------------------------
# TIMELINE
# -----------------------------
season_start = pd.Timestamp(f"{YEAR}-03-01")
season_end = pd.Timestamp(f"{YEAR}-10-31")
timeline = pd.date_range(season_start, season_end, freq="D")

all_colors = sorted(garden_df["primary_color"].dropna().unique())

color_series = {color: [] for color in all_colors}

for day in timeline:
    daily_totals = {color: 0.0 for color in all_colors}

    for _, row in garden_df.iterrows():
        intensity = bloom_intensity(
            day,
            row["bloom_date_dt"],
            row["full_bloom_dt"],
            row["bloom_end_dt"]
        )
        daily_totals[row["primary_color"]] += intensity

    for color in all_colors:
        color_series[color].append(daily_totals[color])

# -----------------------------
# COLOR MAP
# -----------------------------
plot_color_map = {
    "Red": "red",
    "Yellow": "gold",
    "Pink": "hotpink",
    "Purple": "purple",
    "White": "lightgray",
    "Orange": "orange",
    "Blue": "steelblue",
    "Green": "green"
}

# -----------------------------
# SIDE-BY-SIDE VIOLIN LANES
# -----------------------------
fig, ax = plt.subplots(figsize=(14, 7))

lane_spacing = 3.0
scale = 0.4

for i, color in enumerate(all_colors):
    center = i * lane_spacing
    intensities = np.array(color_series[color])

    upper = center + intensities * scale
    lower = center - intensities * scale

    ax.fill_between(
        timeline,
        lower,
        upper,
        color=plot_color_map.get(color, color.lower()),
        alpha=0.75,
        linewidth=1
    )

    ax.plot(timeline, upper, color="black", linewidth=0.5, alpha=0.5)
    ax.plot(timeline, lower, color="black", linewidth=0.5, alpha=0.5)

# labels
ax.set_yticks([i * lane_spacing for i in range(len(all_colors))])
ax.set_yticklabels(all_colors)

ax.set_xlabel("Date")
ax.set_ylabel("Flower Color")
ax.set_title("Garden Bloom Timeline by Color")
ax.grid(axis="x", alpha=0.2)

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

plt.tight_layout()
st.pyplot(fig)