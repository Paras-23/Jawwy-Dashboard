import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse
from collections import Counter
import os

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Jawwy Tracking Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0f1117; }
  [data-testid="stSidebar"] { background: #161b27; }
  .metric-card {
    background: linear-gradient(135deg, #1e2538 0%, #252d42 100%);
    border: 1px solid #2d3a52;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin-bottom: 8px;
  }
  .metric-card h2 { color: #4f8ef7; font-size: 2rem; margin: 0; }
  .metric-card p  { color: #8892a4; font-size: 0.85rem; margin: 4px 0 0 0; }
  .section-header {
    font-size: 1.1rem; font-weight: 700; color: #c9d1e0;
    border-left: 4px solid #4f8ef7; padding-left: 10px;
    margin: 20px 0 12px 0;
  }
  .stDataFrame { background: #1e2538 !important; }
  div[data-testid="metric-container"] {
    background: #1e2538;
    border: 1px solid #2d3a52;
    border-radius: 10px;
    padding: 16px;
  }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/160x50/4f8ef7/ffffff?text=Jawwy+📡", width=160)
    st.markdown("## ⚙️ Configuration")

    mongo_uri = st.text_input(
        "MongoDB URI",
        value=os.getenv("MONGO_URI", "mongodb+srv://..."),
        type="password",
        help="Paste your full Atlas connection string",
    )
    db_name   = st.text_input("Database",   value="Jawwy")
    coll_name = st.text_input("Collection", value="Logs")

    st.markdown("---")
    st.markdown("## 🔍 Filters")

    limit = st.slider("Max documents to load", 1000, 50000, 10000, 1000,
                      help="Fetches the most-recent N docs (sorted by created_at desc)")

    status_filter = st.multiselect(
        "Status filter", ["pending", "processing", "done"],
        default=["pending", "processing", "done"],
    )

    date_range = st.date_input(
        "Date range (created_at)",
        value=[datetime.now().date() - timedelta(days=7), datetime.now().date()],
    )

    refresh = st.button("🔄 Refresh Data", use_container_width=True)

    st.markdown("---")
    st.caption("Built for Jawwy distributed tracker · v1.0")


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner="Fetching from MongoDB…")
def load_data(uri, db, coll, lim, statuses, start_date, end_date):
    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    collection = client[db][coll]

    query = {}
    if statuses:
        query["status"] = {"$in": statuses}
    if start_date and end_date:
        query["created_at"] = {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lte": datetime.combine(end_date,   datetime.max.time()),
        }

    cursor = collection.find(query).sort("created_at", -1).limit(lim)
    docs   = list(cursor)
    client.close()

    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)
    df.drop(columns=["_id"], errors="ignore", inplace=True)

    # --- Parse timestamps ---
    for col in ["created_at", "updated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    if "t" in df.columns:
        df["t_parsed"] = pd.to_datetime(df["t"], utc=True, errors="coerce")
    else:
        df["t_parsed"] = df.get("created_at")

    # --- Derived columns ---
    if "t_parsed" in df.columns:
        df["minute_bucket"] = df["t_parsed"].dt.floor("min")
        df["hour_bucket"]   = df["t_parsed"].dt.floor("h")
        df["date_only"]     = df["t_parsed"].dt.date

    if "u" in df.columns:
        df["url_path"] = df["u"].apply(lambda x: urlparse(str(x)).path if pd.notna(x) else "")

    if "ua" in df.columns:
        def detect_device(ua):
            ua = str(ua).lower()
            if "iphone" in ua or "ipad" in ua: return "iOS"
            if "android" in ua:                return "Android"
            if "windows" in ua:                return "Windows"
            if "mac os x" in ua and "iphone" not in ua and "ipad" not in ua: return "macOS"
            if "linux" in ua:                  return "Linux"
            return "Other"
        df["device_type"] = df["ua"].apply(detect_device)

    if "ref" in df.columns:
        def extract_ref_domain(r):
            try:
                p = urlparse(str(r))
                return p.netloc or "direct"
            except Exception:
                return "direct"
        df["ref_domain"] = df["ref"].apply(extract_ref_domain)

    return df


# ── Load data ─────────────────────────────────────────────────────────────────
if "data" not in st.session_state or refresh:
    try:
        with st.spinner("Connecting to MongoDB Atlas…"):
            start = date_range[0] if len(date_range) > 0 else (datetime.now().date() - timedelta(days=7))
            end   = date_range[1] if len(date_range) > 1 else datetime.now().date()
            df = load_data(mongo_uri, db_name, coll_name, limit, status_filter, start, end)
            st.session_state["data"] = df
            if not df.empty:
                st.sidebar.success(f"✅ Loaded {len(df):,} records")
    except Exception as e:
        st.error(f"❌ MongoDB connection failed: {e}")
        st.info("👆 Enter a valid MongoDB URI in the sidebar and click **Refresh Data**.")
        st.stop()
else:
    df = st.session_state.get("data", pd.DataFrame())

if df is None or df.empty:
    st.warning("No data loaded yet. Configure your MongoDB URI in the sidebar and click **Refresh Data**.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("# 📡 Jawwy Tracking Dashboard")
st.markdown(f"Showing **{len(df):,}** documents · Last refreshed: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
st.markdown("---")

# ── KPI Row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

total   = len(df)
done    = int((df["status"] == "done").sum()) if "status" in df.columns else 0
pending = int((df["status"] == "pending").sum()) if "status" in df.columns else 0
done_pct = round(done / total * 100, 1) if total else 0

avg_dur = None
if "session_duration" in df.columns:
    avg_dur = df["session_duration"].dropna().mean()

unique_uids = df["uid"].nunique() if "uid" in df.columns else 0
unique_urls  = df["u"].nunique()   if "u"   in df.columns else 0

k1.metric("📄 Total Events",      f"{total:,}")
k2.metric("✅ Done",              f"{done:,}",    delta=f"{done_pct}%")
k3.metric("⏳ Pending",           f"{pending:,}")
k4.metric("👥 Unique UIDs",       f"{unique_uids:,}")
k5.metric("🔗 Unique URLs",       f"{unique_urls:,}")

if avg_dur is not None:
    st.metric("⏱ Avg Session Duration (s)", f"{avg_dur:.1f}s")

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Traffic & Volume",
    "🔗 URL Analysis",
    "👷 Worker Analysis",
    "📱 Device & Geo",
    "🔄 Status Funnel",
    "🔬 Raw Explorer",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 · TRAFFIC & VOLUME
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Events Per Minute (by t field)</div>', unsafe_allow_html=True)

    if "minute_bucket" in df.columns:
        per_min = (
            df.groupby("minute_bucket").size().reset_index(name="count")
            .sort_values("minute_bucket")
        )
        fig = px.area(
            per_min, x="minute_bucket", y="count",
            title="Events ingested per minute",
            color_discrete_sequence=["#4f8ef7"],
            template="plotly_dark",
        )
        fig.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            xaxis_title="Time", yaxis_title="Event Count",
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Peak minute
        peak = per_min.loc[per_min["count"].idxmax()]
        st.info(f"🔥 **Peak minute:** `{peak['minute_bucket']}` with **{int(peak['count']):,}** events")

    st.markdown('<div class="section-header">Events Per Hour</div>', unsafe_allow_html=True)
    if "hour_bucket" in df.columns:
        per_hr = df.groupby("hour_bucket").size().reset_index(name="count").sort_values("hour_bucket")
        fig2 = px.bar(
            per_hr, x="hour_bucket", y="count",
            color="count", color_continuous_scale="Blues",
            template="plotly_dark",
        )
        fig2.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=300,
                           xaxis_title="Hour", yaxis_title="Events")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-header">Event Type Distribution (ev field)</div>', unsafe_allow_html=True)
    if "ev" in df.columns:
        ev_counts = df["ev"].value_counts().reset_index()
        ev_counts.columns = ["event_type", "count"]
        c1, c2 = st.columns(2)
        with c1:
            fig3 = px.pie(ev_counts, names="event_type", values="count",
                          hole=0.45, template="plotly_dark",
                          color_discrete_sequence=px.colors.sequential.Blues_r)
            fig3.update_layout(paper_bgcolor="#0f1117", height=300)
            st.plotly_chart(fig3, use_container_width=True)
        with c2:
            fig4 = px.bar(ev_counts, x="event_type", y="count",
                          color="count", color_continuous_scale="Blues",
                          template="plotly_dark")
            fig4.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=300)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown('<div class="section-header">Daily Trend</div>', unsafe_allow_html=True)
    if "date_only" in df.columns:
        daily = df.groupby("date_only").size().reset_index(name="count")
        fig5 = px.line(daily, x="date_only", y="count", markers=True,
                       color_discrete_sequence=["#4f8ef7"], template="plotly_dark")
        fig5.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                           xaxis_title="Date", yaxis_title="Events", height=300)
        st.plotly_chart(fig5, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 · URL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">All Unique URLs (u field)</div>', unsafe_allow_html=True)

    if "u" in df.columns:
        url_counts = df["u"].value_counts().reset_index()
        url_counts.columns = ["url", "hits"]

        st.markdown(f"**{len(url_counts):,} unique URLs found**")
        search_url = st.text_input("🔎 Filter URLs", placeholder="e.g. shop, activation, ar")
        filtered_urls = url_counts[url_counts["url"].str.contains(search_url, case=False, na=False)] if search_url else url_counts
        st.dataframe(filtered_urls, use_container_width=True, height=300)

        st.markdown('<div class="section-header">Top 20 URLs by Traffic</div>', unsafe_allow_html=True)
        top20 = url_counts.head(20)
        fig6 = px.bar(
            top20, x="hits", y="url", orientation="h",
            color="hits", color_continuous_scale="Blues",
            template="plotly_dark",
        )
        fig6.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                           height=520, yaxis=dict(autorange="reversed"),
                           xaxis_title="Hits", yaxis_title="URL")
        st.plotly_chart(fig6, use_container_width=True)

    st.markdown('<div class="section-header">URL Path Breakdown</div>', unsafe_allow_html=True)
    if "url_path" in df.columns:
        path_counts = df["url_path"].value_counts().head(25).reset_index()
        path_counts.columns = ["path", "count"]
        fig7 = px.treemap(path_counts, path=["path"], values="count", template="plotly_dark",
                          color="count", color_continuous_scale="Blues")
        fig7.update_layout(paper_bgcolor="#0f1117", height=380)
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown('<div class="section-header">Referrer Analysis (ref field)</div>', unsafe_allow_html=True)
    if "ref" in df.columns:
        ref_counts = df["ref"].value_counts().head(15).reset_index()
        ref_counts.columns = ["referrer", "count"]
        fig8 = px.bar(ref_counts, x="count", y="referrer", orientation="h",
                      color="count", color_continuous_scale="Teal",
                      template="plotly_dark")
        fig8.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                           height=400, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig8, use_container_width=True)

    if "ref_domain" in df.columns:
        st.markdown('<div class="section-header">Traffic Source Domains</div>', unsafe_allow_html=True)
        ref_dom = df["ref_domain"].value_counts().reset_index()
        ref_dom.columns = ["domain", "count"]
        fig9 = px.pie(ref_dom, names="domain", values="count", hole=0.4,
                      template="plotly_dark", color_discrete_sequence=px.colors.sequential.Teal_r)
        fig9.update_layout(paper_bgcolor="#0f1117", height=320)
        st.plotly_chart(fig9, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 · WORKER ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Worker Performance Overview</div>', unsafe_allow_html=True)

    worker_col = None
    for c in ["worker", "worker_name"]:
        if c in df.columns:
            worker_col = c
            break

    if worker_col and "session_duration" in df.columns:
        worker_stats = (
            df.groupby(worker_col)
            .agg(
                total_events   =("session_duration", "count"),
                avg_duration_s =("session_duration", "mean"),
                median_duration=("session_duration", "median"),
                min_duration   =("session_duration", "min"),
                max_duration   =("session_duration", "max"),
                done_count     =("status",           lambda x: (x == "done").sum()),
            )
            .reset_index()
        )
        worker_stats["completion_rate_%"] = (
            worker_stats["done_count"] / worker_stats["total_events"] * 100
        ).round(1)
        worker_stats["avg_duration_s"] = worker_stats["avg_duration_s"].round(2)

        st.dataframe(worker_stats, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            fig10 = px.bar(worker_stats, x=worker_col, y="avg_duration_s",
                           color="avg_duration_s", color_continuous_scale="Blues",
                           title="Avg Session Duration by Worker",
                           template="plotly_dark")
            fig10.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=320)
            st.plotly_chart(fig10, use_container_width=True)
        with c2:
            fig11 = px.bar(worker_stats, x=worker_col, y="completion_rate_%",
                           color="completion_rate_%", color_continuous_scale="Greens",
                           title="Completion Rate % by Worker",
                           template="plotly_dark")
            fig11.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=320)
            st.plotly_chart(fig11, use_container_width=True)

        # Session duration distribution by worker
        st.markdown('<div class="section-header">Session Duration Distribution per Worker</div>', unsafe_allow_html=True)
        fig12 = px.box(
            df.dropna(subset=["session_duration"]),
            x=worker_col, y="session_duration",
            color=worker_col, template="plotly_dark",
            title="Session Duration Box Plot by Worker",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig12.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=360)
        st.plotly_chart(fig12, use_container_width=True)

        # Violin
        fig13 = px.violin(
            df.dropna(subset=["session_duration"]),
            x=worker_col, y="session_duration",
            color=worker_col, box=True, template="plotly_dark",
            title="Session Duration Violin by Worker",
        )
        fig13.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=360)
        st.plotly_chart(fig13, use_container_width=True)

    elif worker_col:
        wc = df[worker_col].value_counts().reset_index()
        wc.columns = [worker_col, "events"]
        fig_w = px.bar(wc, x=worker_col, y="events", color="events",
                       color_continuous_scale="Blues", template="plotly_dark",
                       title="Events per Worker")
        fig_w.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=340)
        st.plotly_chart(fig_w, use_container_width=True)
    else:
        st.info("No `worker` or `worker_name` column found in this dataset slice.")

    # Events processed over time per worker
    if worker_col and "minute_bucket" in df.columns:
        st.markdown('<div class="section-header">Worker Activity Timeline</div>', unsafe_allow_html=True)
        worker_time = (
            df.groupby([worker_col, "hour_bucket"]).size()
            .reset_index(name="events")
        )
        fig14 = px.line(worker_time, x="hour_bucket", y="events", color=worker_col,
                        template="plotly_dark", markers=True,
                        title="Hourly Events per Worker")
        fig14.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=340)
        st.plotly_chart(fig14, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 · DEVICE & GEO
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    c1, c2 = st.columns(2)

    if "device_type" in df.columns:
        with c1:
            st.markdown('<div class="section-header">Device Type Breakdown</div>', unsafe_allow_html=True)
            dev = df["device_type"].value_counts().reset_index()
            dev.columns = ["device", "count"]
            fig15 = px.pie(dev, names="device", values="count", hole=0.4,
                           template="plotly_dark",
                           color_discrete_sequence=px.colors.sequential.Blues_r)
            fig15.update_layout(paper_bgcolor="#0f1117", height=320)
            st.plotly_chart(fig15, use_container_width=True)

    if "ip" in df.columns:
        with c2:
            st.markdown('<div class="section-header">Top IPs</div>', unsafe_allow_html=True)
            ip_counts = df["ip"].value_counts().head(15).reset_index()
            ip_counts.columns = ["ip", "count"]
            fig16 = px.bar(ip_counts, x="count", y="ip", orientation="h",
                           color="count", color_continuous_scale="Blues",
                           template="plotly_dark")
            fig16.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                                height=320, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig16, use_container_width=True)

    if "ua" in df.columns:
        st.markdown('<div class="section-header">Top User Agents</div>', unsafe_allow_html=True)
        ua_counts = df["ua"].value_counts().head(10).reset_index()
        ua_counts.columns = ["user_agent", "count"]
        # Truncate long UA strings
        ua_counts["short_ua"] = ua_counts["user_agent"].str[:80]
        fig17 = px.bar(ua_counts, x="count", y="short_ua", orientation="h",
                       color="count", color_continuous_scale="Teal",
                       template="plotly_dark")
        fig17.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                            height=380, yaxis=dict(autorange="reversed"),
                            yaxis_title="User Agent (truncated)")
        st.plotly_chart(fig17, use_container_width=True)

    if "device_type" in df.columns and "session_duration" in df.columns:
        st.markdown('<div class="section-header">Session Duration by Device</div>', unsafe_allow_html=True)
        fig18 = px.box(df.dropna(subset=["session_duration"]),
                       x="device_type", y="session_duration",
                       color="device_type", template="plotly_dark",
                       color_discrete_sequence=px.colors.qualitative.Pastel)
        fig18.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=340)
        st.plotly_chart(fig18, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 · STATUS FUNNEL
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    if "status" in df.columns:
        st.markdown('<div class="section-header">Status Distribution</div>', unsafe_allow_html=True)
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]

        color_map = {"done": "#22c55e", "pending": "#f59e0b", "failed": "#ef4444", "error": "#a855f7"}
        c1, c2 = st.columns(2)
        with c1:
            fig19 = px.pie(status_counts, names="status", values="count",
                           hole=0.45, template="plotly_dark",
                           color="status", color_discrete_map=color_map)
            fig19.update_layout(paper_bgcolor="#0f1117", height=320)
            st.plotly_chart(fig19, use_container_width=True)
        with c2:
            fig20 = px.funnel(status_counts.sort_values("count", ascending=False),
                              x="count", y="status",
                              color="status", color_discrete_map=color_map,
                              template="plotly_dark")
            fig20.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=320)
            st.plotly_chart(fig20, use_container_width=True)

        st.markdown('<div class="section-header">Status Over Time</div>', unsafe_allow_html=True)
        if "hour_bucket" in df.columns:
            status_time = (
                df.groupby(["hour_bucket", "status"]).size()
                .reset_index(name="count")
            )
            fig21 = px.bar(status_time, x="hour_bucket", y="count", color="status",
                           barmode="stack", template="plotly_dark",
                           color_discrete_map=color_map)
            fig21.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=360)
            st.plotly_chart(fig21, use_container_width=True)

        st.markdown('<div class="section-header">Status by Event Type</div>', unsafe_allow_html=True)
        if "ev" in df.columns:
            ev_status = df.groupby(["ev", "status"]).size().reset_index(name="count")
            fig22 = px.bar(ev_status, x="ev", y="count", color="status",
                           barmode="group", template="plotly_dark",
                           color_discrete_map=color_map)
            fig22.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=340)
            st.plotly_chart(fig22, use_container_width=True)

        # Time-to-completion analysis
        if "created_at" in df.columns and "updated_at" in df.columns:
            st.markdown('<div class="section-header">⏱ Time to Completion (created_at → updated_at)</div>', unsafe_allow_html=True)
            done_df = df[(df["status"] == "done") & df["created_at"].notna() & df["updated_at"].notna()].copy()
            if not done_df.empty:
                done_df["processing_time_s"] = (
                    done_df["updated_at"] - done_df["created_at"]
                ).dt.total_seconds()
                done_df = done_df[done_df["processing_time_s"] > 0]
                if not done_df.empty:
                    avg_proc = done_df["processing_time_s"].mean()
                    med_proc = done_df["processing_time_s"].median()
                    st.info(f"⚡ Avg processing time: **{avg_proc:.1f}s** | Median: **{med_proc:.1f}s**")
                    fig23 = px.histogram(done_df, x="processing_time_s", nbins=40,
                                         template="plotly_dark",
                                         color_discrete_sequence=["#4f8ef7"],
                                         title="Distribution of Processing Time (seconds)")
                    fig23.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", height=320)
                    st.plotly_chart(fig23, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 · RAW EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-header">🔬 Interactive Data Explorer</div>', unsafe_allow_html=True)

    cols_to_show = st.multiselect(
        "Select columns to display",
        options=list(df.columns),
        default=[c for c in ["created_at", "ev", "status", "u", "ip", "worker", "session_duration", "uid"]
                 if c in df.columns],
    )

    status_vals = df["status"].dropna().unique().tolist() if "status" in df.columns else []
    sel_status  = st.multiselect("Filter status", options=status_vals, default=status_vals)

    filtered = df.copy()
    if sel_status and "status" in filtered.columns:
        filtered = filtered[filtered["status"].isin(sel_status)]

    text_search = st.text_input("🔎 Search any column (substring)", placeholder="e.g. shop, iphone, worker_2")
    if text_search:
        mask = filtered.apply(lambda col: col.astype(str).str.contains(text_search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]

    st.info(f"Showing **{len(filtered):,}** rows")
    st.dataframe(filtered[cols_to_show] if cols_to_show else filtered, use_container_width=True, height=480)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download as CSV", data=csv, file_name="jawwy_export.csv", mime="text/csv")

    # Summary stats
    st.markdown('<div class="section-header">📊 Numeric Summary</div>', unsafe_allow_html=True)
    numeric_cols = filtered.select_dtypes("number")
    if not numeric_cols.empty:
        st.dataframe(numeric_cols.describe().round(3), use_container_width=True)
