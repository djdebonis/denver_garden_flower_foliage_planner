import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# -----------------------------
# PAGE SETUP
# -----------------------------
st.set_page_config(page_title="Garden Bloom Timeline", layout="wide")
st.title("Garden Bloom Timeline")
st.write("Choose flowers and visualize bloom timing across the growing season.")

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("garden_timelines.csv")

df = load_data()

# -----------------------------
# DATE HELPERS
# -----------------------------
YEAR = 2026

def parse_mmdd(date_str):
    return pd.to_datetime(f"{YEAR}-{date_str}", format="%Y-%m-%d")

df["bloom_date_dt"] = df["bloom_date"].apply(parse_mmdd)
df["full_bloom_dt"] = df["full_bloom"].apply(parse_mmdd)
df["bloom_end_dt"] = df["bloom_end"].apply(parse_mmdd)

# -----------------------------
# COLOR HELPERS
# -----------------------------
fallback_color_map = {
    "Red": "#d62728",
    "Yellow": "#f1c40f",
    "Pink": "#ff69b4",
    "Purple": "#9467bd",
    "White": "#dddddd",
    "Orange": "#ff7f0e",
    "Blue": "#4f81bd",
    "Green": "#2ca02c",
}

def safe_color(row):
    """
    Try xkcd_color1 first.
    If it is invalid, fall back to primary_color mapping.
    """
    raw = str(row.get("xkcd_color1", "")).strip()

    # ensure proper hex data entry
    if raw.startswith("#") and len(raw) == 7:
        hex_part = raw[1:]
        valid_hex = all(c in "0123456789abcdefABCDEF" for c in hex_part)
        if valid_hex:
            return raw

    return fallback_color_map.get(row["primary_color"], "#999999")
def safe_foliage_color(row):
    """
    Use xkcd_color_foliage if valid.
    Otherwise fall back to a natural green.
    """
    raw = str(row.get("xkcd_color_foliage", "")).strip()

    if raw.startswith("#") and len(raw) == 7:
        hex_part = raw[1:]
        valid_hex = all(c in "0123456789abcdefABCDEF" for c in hex_part)
        if valid_hex:
            return raw

    # fallback foliage green
    return "#3a7d44"
# -----------------------------
# BLOOM CURVE
# -----------------------------
def bloom_intensity(current_date, start, peak, end):
    """
    Smooth bloom curve:
    - 0 before bloom
    - rises smoothly to peak
    - falls smoothly to end
    """
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
# SIDEBAR SELECTION
# -----------------------------
st.sidebar.header("Build Your Garden")

flower_options = sorted(df["flower name"].unique().tolist())

selected_flowers = st.sidebar.multiselect(
    "Choose flowers",
    options=flower_options,
    default=flower_options[:4]
)

garden_df = df[df["flower name"].isin(selected_flowers)].copy()

if garden_df.empty:
    st.info("Choose at least one flower from the sidebar.")
    st.stop()

# -----------------------------
# TIMELINE
# -----------------------------
season_start = pd.Timestamp(f"{YEAR}-03-01")
season_end = pd.Timestamp(f"{YEAR}-10-31")
timeline = pd.date_range(season_start, season_end, freq="D")

# -----------------------------
# FLOWER-LEVEL META + ORDERING
# -----------------------------
flower_meta = (
    garden_df[
        [
            "flower name",
            "primary_color",
            "xkcd_color1",
            "bloom_date_dt",
            "full_bloom_dt",
            "bloom_end_dt",
        ]
    ]
    .drop_duplicates(subset=["flower name"])
    .sort_values(["full_bloom_dt", "bloom_date_dt", "flower name"])
    .reset_index(drop=True)
)

flower_names = flower_meta["flower name"].tolist()

# -----------------------------
# BUILD BLOOM CURVES BY FLOWER
# -----------------------------
flower_series = {}

for _, row in flower_meta.iterrows():
    flower = row["flower name"]

    intensities = []
    for day in timeline:
        intensity = bloom_intensity(
            current_date=day,
            start=row["bloom_date_dt"],
            peak=row["full_bloom_dt"],
            end=row["bloom_end_dt"]
        )
        intensities.append(intensity)

    flower_series[flower] = np.array(intensities)

# -----------------------------
# OPTIONAL DATA PREVIEW
# -----------------------------
with st.expander("See selected flower data"):
    st.dataframe(
        flower_meta[
            ["flower name", "primary_color", "bloom_date_dt", "full_bloom_dt", "bloom_end_dt"]
        ],
        use_container_width=True
    )

# -----------------------------
# PLOT SETTINGS
# -----------------------------
n_flowers = len(flower_names)

lane_spacing = 1.0
scale = 0.28
fig_height = max(5, n_flowers * 0.38)

fig, ax = plt.subplots(figsize=(14, fig_height))

# -----------------------------
# DRAW FLOWER VIOLIN LANES
# -----------------------------
for i, (_, row) in enumerate(flower_meta.iterrows()):
    flower = row["flower name"]
    center = i * lane_spacing
    intensities = flower_series[flower]
    fill_color = safe_color(row)

    upper = center + intensities * scale
    lower = center - intensities * scale

    # faint centerline
    ax.hlines(
        y=center,
        xmin=timeline.min(),
        xmax=timeline.max(),
        colors="gray",
        linewidth=0.3,
        alpha=0.2
    )

    # fill
    ax.fill_between(
        timeline,
        lower,
        upper,
        color=fill_color,
        alpha=0.8,
        linewidth=0
    )
    
    outline_color = safe_foliage_color(row)

    # outline
    ax.plot(
        timeline,
        upper,
        color=outline_color,
        linewidth=0.5,
        alpha=0.6
    )
    ax.plot(
        timeline,
        lower,
        color=outline_color,
        linewidth=0.5,
        alpha=0.6
    )

# -----------------------------
# AXIS FORMATTING
# -----------------------------
ax.set_yticks([i * lane_spacing for i in range(n_flowers)])
ax.set_yticklabels(flower_names, fontsize=9)

ax.set_xlabel("Date")
ax.set_ylabel("Flower")
ax.set_title("Garden Bloom Timeline by Flower")

ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

ax.grid(axis="x", alpha=0.2)

for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

plt.tight_layout()
st.pyplot(fig, use_container_width=True)