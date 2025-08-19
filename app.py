import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="YouTube Audit Dashboard", layout="wide")
PD, RP = "data/processed", "reports"

def lp(p):
    try:
        return pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

videos = lp(f"{PD}/videos.parquet")
analytics = lp(f"{PD}/analytics_365d.parquet")
master = lp(f"{PD}/master_join.parquet")
thumbs = lp(f"{PD}/thumbnail_features.parquet")

st.title("📊 YouTube Deep-Dive Dashboard")
st.markdown("---")

if master.empty:
    st.warning("Run the fetch + analysis scripts first.")
    st.stop()

df = master.merge(thumbs, on="videoId", how="left") if not thumbs.empty else master.copy()

# Key Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_views = int(df.get("views", 0).sum())
    st.metric("Total Views (365d)", f"{total_views:,}")
with col2:
    ctr = df.get("clickThroughRate")
    if ctr is not None:
        median_ctr = (ctr * 100).median()
        st.metric("Median CTR", f"{median_ctr:.2f}%")
    else:
        st.metric("Median CTR", "—")
with col3:
    avd = df.get("averageViewDuration")
    if avd is not None:
        median_avd = avd.median()
        st.metric("Median AVD", f"{median_avd:.1f}s")
    else:
        st.metric("Median AVD", "—")
with col4:
    total_subs = int(df.get("subscribersGained", 0).sum())
    st.metric("Total Subs Gained", f"{total_subs:,}")

st.markdown("---")

# Top Performers
st.subheader("🎯 Top Performers by CTR")
cols = ["title", "videoId", "clickThroughRate", "impressions", "views", "averageViewDuration", "title_caption_sim"]
display_cols = [c for c in cols if c in df.columns]
if "clickThroughRate" in df.columns:
    top_ctr = df[display_cols].sort_values("clickThroughRate", ascending=False).head(10)
    st.dataframe(top_ctr, use_container_width=True)
else:
    st.info("CTR data not available")

st.markdown("---")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Title–Caption Similarity vs CTR")
    q = df.dropna(subset=["title_caption_sim", "clickThroughRate"])
    if not q.empty:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(q["title_caption_sim"], q["clickThroughRate"] * 100, alpha=0.6, s=50)
        ax.set_xlabel("Title-Caption Similarity")
        ax.set_ylabel("CTR (%)")
        ax.grid(True, alpha=0.2)
        ax.set_title("Content Alignment vs Performance")
        st.pyplot(fig)
    else:
        st.info("Insufficient data for similarity analysis")

with col2:
    st.subheader("📊 Views Distribution")
    if "views" in df.columns:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.hist(df["views"], bins=10, alpha=0.7, edgecolor='black')
        ax.set_xlabel("Views")
        ax.set_ylabel("Frequency")
        ax.set_title("Video Views Distribution")
        ax.grid(True, alpha=0.2)
        st.pyplot(fig)
    else:
        st.info("Views data not available")

st.markdown("---")

# Thumbnail Analysis
if not thumbs.empty:
    st.subheader("🖼️ Thumbnail Analysis")
    thumb_cols = ["videoId", "sharpness", "brightness", "contrast", "text_density"]
    available_thumb_cols = [c for c in thumb_cols if c in thumbs.columns]
    
    if len(available_thumb_cols) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            if "sharpness" in thumbs.columns:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.hist(thumbs["sharpness"].dropna(), bins=10, alpha=0.7, edgecolor='black')
                ax.set_xlabel("Sharpness")
                ax.set_ylabel("Frequency")
                ax.set_title("Thumbnail Sharpness Distribution")
                ax.grid(True, alpha=0.2)
                st.pyplot(fig)
        
        with col2:
            if "text_density" in thumbs.columns:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.hist(thumbs["text_density"].dropna(), bins=10, alpha=0.7, edgecolor='black')
                ax.set_xlabel("Text Density")
                ax.set_ylabel("Frequency")
                ax.set_title("Thumbnail Text Density Distribution")
                ax.grid(True, alpha=0.2)
                st.pyplot(fig)

st.markdown("---")

# All Videos Table
st.subheader("📋 All Videos")
all_cols = ["title", "videoId", "views", "clickThroughRate", "averageViewDuration", "impressions", "subscribersGained", "likes", "comments"]
available_all_cols = [c for c in all_cols if c in df.columns]
if "views" in df.columns:
    all_videos = df[available_all_cols].sort_values("views", ascending=False)
    st.dataframe(all_videos, use_container_width=True)
else:
    st.info("Video data not available")

st.markdown("---")

# Correlation Analysis
st.subheader("🔍 Correlation Analysis")
if os.path.exists(f"{RP}/correlations.csv"):
    corr_df = pd.read_csv(f"{RP}/correlations.csv", index_col=0)
    st.dataframe(corr_df, use_container_width=True)
else:
    st.info("Correlation analysis not available")

# Footer
st.markdown("---")
st.markdown("*Dashboard generated by yt-Stripper - YouTube Deep-Dive Audit Tool*")
