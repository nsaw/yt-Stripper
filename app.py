import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from analysis.insight_engine import generate_insights_and_actions

st.set_page_config(page_title="YouTube Audit Dashboard", layout="wide")
PD, RP = "data/processed", "reports"

def lp(p):
    try:
        return pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

videos = lp(f"{PD}/videos.parquet")
analytics = lp(f"{PD}/analytics_365d.parquet")
thumbs = lp(f"{PD}/thumbnail_features.parquet")

st.title("📊 YouTube Deep-Dive Dashboard")

# === Insights & Actions ===
try:
    payload = generate_insights_and_actions(master, prov if 'prov' in globals() else {})
    st.header('🔎 Insights')
    if payload.get('narrative_gpt'):
        st.write(payload['narrative_gpt'])
    if payload.get('insights_heuristic'):
        st.subheader('Heuristic Highlights')
        for i in payload['insights_heuristic']:
            st.markdown(f'- {i}')
    st.header('✅ Action Items')
    actions = payload.get('actions_heuristic', [])
    if actions:
        import pandas as pd
        st.dataframe(pd.DataFrame(actions))
    else:
        st.info('No actions generated yet. Add more data or enable Analytics per-video for deeper signals.')
except Exception as _e:
    st.warning('Insights engine unavailable — check data or LLM settings.')

# HONEST MODE banner
import json, time
prov = {"synthetic": None, "source":"unknown","ts":None}
try:
    honest_banner
except Exception as _e:
    pass
try:
    prov = json.load(open("data_provenance.json"))
except Exception:
    pass
def honest_banner(df_master):
    missing = []
    for path in ["data/processed/analytics_365d.parquet","reports/correlations.csv"]:
        if not os.path.exists(path): missing.append(path)
    if prov.get("synthetic") is True or missing or df_master.empty:
        st.warning("HONEST MODE: Real analytics are missing or incomplete. No synthetic data is displayed.")
        if missing: st.info("Missing artifacts: " + ", ".join(missing))
        st.caption(f"Provenance source: {prov.get('source')} | synthetic: {prov.get('synthetic')} | ts: {prov.get('ts')}")

st.markdown("---")

# Try to load master_join first, fallback to manual merge
master = lp(f"{PD}/master_join.parquet")
if not master.empty:
    df = master.copy()
    if not thumbs.empty:
        df = df.merge(thumbs, on="videoId", how="left")
else:
    # Create master dataframe by merging videos and analytics
    if not videos.empty:
        df = videos.copy()
        # Only merge analytics if it has videoId column (per-video data)
        if not analytics.empty and "videoId" in analytics.columns:
            df = df.merge(analytics, on="videoId", how="left")
        elif not analytics.empty:
            # Analytics is channel-level totals, add as summary info
            st.info("📊 Channel Analytics: " + str(analytics.iloc[0].to_dict()) if not analytics.empty else "")
        if not thumbs.empty:
            df = df.merge(thumbs, on="videoId", how="left")
    else:
        st.warning("Missing video data. Please run the fetch scripts first.")
        st.stop()

# HONEST MODE banner
(honest_banner(master) if 'master' in globals() or 'master' in locals() else None)

# Data Status
st.info("📊 **Data Status**: This dashboard shows real video metadata but analytics data is limited due to API quota restrictions.")

# Key Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_videos = len(df)
    st.metric("Total Videos", f"{total_videos}")
with col2:
    if "viewCount" in df.columns:
        total_views = int(df["viewCount"].sum())
        st.metric("Total Views", f"{total_views:,}")
    else:
        st.metric("Total Views", "API quota exceeded")
with col3:
    if "likeCount" in df.columns:
        total_likes = int(df["likeCount"].sum())
        st.metric("Total Likes", f"{total_likes:,}")
    else:
        st.metric("Total Likes", "API quota exceeded")
with col4:
    if "commentCount" in df.columns:
        total_comments = int(df["commentCount"].sum())
        st.metric("Total Comments", f"{total_comments:,}")
    else:
        st.metric("Total Comments", "API quota exceeded")

st.markdown("---")

# Video List
st.subheader("📺 Your YouTube Videos")
display_cols = ["title", "publishedAt"]
if "viewCount" in df.columns:
    display_cols.append("viewCount")
if "likeCount" in df.columns:
    display_cols.append("likeCount")
if "commentCount" in df.columns:
    display_cols.append("commentCount")

video_display = df[display_cols].copy()
if "publishedAt" in video_display.columns:
    video_display["publishedAt"] = pd.to_datetime(video_display["publishedAt"]).dt.strftime("%Y-%m-%d")
    video_display = video_display.sort_values("publishedAt", ascending=False)

st.dataframe(video_display, use_container_width=True)

st.markdown("---")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Video Performance (if available)")
    if "viewCount" in df.columns:
        views_data = df["viewCount"].dropna()
        if len(views_data) > 0:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.hist(views_data, bins=min(10, len(views_data)), alpha=0.7, edgecolor='black')
            ax.set_xlabel("Views")
            ax.set_ylabel("Frequency")
            ax.set_title("Video Views Distribution")
            ax.grid(True, alpha=0.2)
            st.pyplot(fig)
        else:
            st.info("No view data available")
    else:
        st.info("View data not available due to API quota limits")

with col2:
    st.subheader("📈 Engagement Metrics (if available)")
    if "likeCount" in df.columns and "commentCount" in df.columns:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(df["likeCount"], df["commentCount"], alpha=0.6, s=50)
        ax.set_xlabel("Likes")
        ax.set_ylabel("Comments")
        ax.set_title("Likes vs Comments")
        ax.grid(True, alpha=0.2)
        st.pyplot(fig)
    else:
        st.info("Engagement data not available due to API quota limits")

st.markdown("---")

# Thumbnail Analysis
if not thumbs.empty:
    st.subheader("🖼️ Thumbnail Analysis")
    thumb_cols = ["videoId", "sharpness", "brightness", "contrast", "text_density"]
    available_thumb_cols = [c for c in thumb_cols if c in thumbs.columns]
    
    if len(available_thumb_cols) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            if "sharpness" in thumbs.columns and not thumbs["sharpness"].isna().all():
                sharpness_data = thumbs["sharpness"].dropna()
                if len(sharpness_data) > 0:
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.hist(sharpness_data, bins=min(10, len(sharpness_data)), alpha=0.7, edgecolor='black')
                    ax.set_xlabel("Sharpness")
                    ax.set_ylabel("Frequency")
                    ax.set_title("Thumbnail Sharpness Distribution")
                    ax.grid(True, alpha=0.2)
                    st.pyplot(fig)
                else:
                    st.info("No valid sharpness data available")
            else:
                st.info("Sharpness data not available")
        
        with col2:
            if "text_density" in thumbs.columns and not thumbs["text_density"].isna().all():
                text_density_data = thumbs["text_density"].dropna()
                if len(text_density_data) > 0:
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.hist(text_density_data, bins=min(10, len(text_density_data)), alpha=0.7, edgecolor='black')
                    ax.set_xlabel("Text Density")
                    ax.set_ylabel("Frequency")
                    ax.set_title("Thumbnail Text Density Distribution")
                    ax.grid(True, alpha=0.2)
                    st.pyplot(fig)
                else:
                    st.info("No valid text density data available")
            else:
                st.info("Text density data not available")

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
