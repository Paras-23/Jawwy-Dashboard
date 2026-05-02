# 📡 Jawwy Tracking Dashboard

A real-time analytics dashboard for your distributed tracking + automation system.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the dashboard
streamlit run dashboard.py
```

The dashboard opens at **http://localhost:8501**

## ⚙️ Configuration

Your MongoDB URI is pre-filled. You can also set it via `.env`:

```
MONGO_URI=mongodb+srv://pandeydevendra20devops_db_user:...@deliverly.4lvw8v3.mongodb.net/
```

Or paste it directly in the **sidebar** of the dashboard at runtime.

## 📊 Dashboard Tabs

| Tab | What you get |
|-----|-------------|
| **Traffic & Volume** | Events/minute chart, hourly heatmap, event-type breakdown, daily trend |
| **URL Analysis** | All unique URLs with search, top-20 bar, treemap, referrer breakdown |
| **Worker Analysis** | Avg duration per worker, completion rate, box/violin plots, timeline |
| **Device & Geo** | Device split, top IPs, user-agent breakdown, duration by device |
| **Status Funnel** | done/pending/failed funnel, status over time, processing time histogram |
| **Raw Explorer** | Filterable/searchable table, column picker, CSV export |

## 🗂 Expected MongoDB Schema

```
_id, ga, created_at, ev, gs, ip, ref, status, t, u, ua, uid,
updated_at (optional), worker (optional), session_duration (optional)
```

## 📦 Packages Used

- **Streamlit** — dashboard framework  
- **PyMongo** — MongoDB connection  
- **Plotly** — interactive charts  
- **Pandas** — data wrangling  
