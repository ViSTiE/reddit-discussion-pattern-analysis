import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from core.utils import get_db, init_db

init_db()

st.set_page_config(
    page_title="Business Idea Hunter",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Business Idea Hunter")
st.caption("Automated startup problem discovery from Reddit & Hacker News")


def load_market_types() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT market_type FROM problems WHERE market_type IS NOT NULL ORDER BY market_type"
        ).fetchall()
    return [r["market_type"] for r in rows]


def load_sources() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT source FROM raw_posts ORDER BY source"
        ).fetchall()
    return [r["source"] for r in rows]


def load_subreddits() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT subreddit FROM raw_posts WHERE subreddit IS NOT NULL ORDER BY subreddit"
        ).fetchall()
    return [r["subreddit"] for r in rows]


# --- Sidebar Filters ---
st.sidebar.header("Filters")

market_types = load_market_types()
selected_markets = st.sidebar.multiselect("Market Type", market_types, default=market_types)

min_score = st.sidebar.slider("Minimum Score", 0, 100, 0)

sources = load_sources()
selected_sources = st.sidebar.multiselect("Source", sources, default=sources)

subreddits = load_subreddits()
selected_subreddits = st.sidebar.multiselect("Subreddit", subreddits, default=subreddits)


def build_query(time_filter: str | None = None, order: str = "p.final_score DESC", limit: int = 50) -> tuple[str, list]:
    params: list = []
    conditions = ["1=1"]

    if selected_markets:
        placeholders = ",".join("?" for _ in selected_markets)
        conditions.append(f"p.market_type IN ({placeholders})")
        params.extend(selected_markets)

    conditions.append("p.final_score >= ?")
    params.append(min_score)

    if selected_sources:
        placeholders = ",".join("?" for _ in selected_sources)
        conditions.append(f"rp.source IN ({placeholders})")
        params.extend(selected_sources)

    if selected_subreddits:
        placeholders = ",".join("?" for _ in selected_subreddits)
        conditions.append(f"(rp.subreddit IN ({placeholders}) OR rp.subreddit IS NULL)")
        params.extend(selected_subreddits)

    if time_filter:
        conditions.append("p.created_at >= ?")
        params.append(time_filter)

    where = " AND ".join(conditions)

    query = f"""
        SELECT
            p.id,
            p.problem_summary,
            p.target_group,
            p.market_type,
            p.buyer_type,
            p.pain_score,
            p.monetization_score,
            p.complexity_score,
            p.engagement_score,
            p.frequency_score,
            p.momentum_score,
            p.final_score,
            p.created_at,
            rp.source,
            rp.subreddit,
            rp.title as post_title,
            rp.upvotes,
            rp.comments,
            rp.id as post_id,
            COALESCE(cl.size, 1) as cluster_size
        FROM problems p
        JOIN raw_posts rp ON rp.id = p.post_id
        LEFT JOIN problem_clusters pc ON pc.problem_id = p.id
        LEFT JOIN clusters cl ON cl.id = pc.cluster_id
        WHERE {where}
        ORDER BY {order}
        LIMIT ?
    """
    params.append(limit)
    return query, params


def get_source_url(post_id: str) -> str:
    if post_id.startswith("reddit_"):
        reddit_id = post_id.replace("reddit_", "")
        return f"https://reddit.com/comments/{reddit_id}"
    elif post_id.startswith("askhn_"):
        hn_id = post_id.replace("askhn_", "")
        return f"https://news.ycombinator.com/item?id={hn_id}"
    return "#"


def render_card(row: dict) -> None:
    score = row["final_score"] or 0
    if score >= 70:
        color = "#22c55e"
    elif score >= 40:
        color = "#eab308"
    else:
        color = "#ef4444"

    source_url = get_source_url(row["post_id"])
    source_label = row["source"].upper()
    if row["subreddit"]:
        source_label += f" / r/{row['subreddit']}"

    st.markdown(
        f"""
        <div style="border: 1px solid #333; border-radius: 10px; padding: 16px; margin-bottom: 12px; background: #1a1a2e;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 1.1em; font-weight: 600; color: #e0e0e0;">{row['problem_summary']}</span>
                <span style="background: {color}; color: #000; padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 1.1em;">{score:.0f}</span>
            </div>
            <div style="color: #999; font-size: 0.85em; margin-bottom: 8px;">
                🎯 {row['target_group'] or 'N/A'} &nbsp;|&nbsp;
                🏪 {row['market_type'] or 'N/A'} &nbsp;|&nbsp;
                💰 {row['buyer_type'] or 'N/A'}
            </div>
            <div style="display: flex; gap: 16px; color: #bbb; font-size: 0.82em; margin-bottom: 8px;">
                <span>🔥 Pain: {row['pain_score']:.0f}</span>
                <span>💵 Monet: {row['monetization_score']:.0f}</span>
                <span>📊 Engage: {row['engagement_score']:.1f}</span>
                <span>🔄 Freq: {row['frequency_score']:.1f}</span>
                <span>🚀 Momentum: {row['momentum_score']:.1f}</span>
                <span>👥 Cluster: {row['cluster_size']}</span>
            </div>
            <div style="display: flex; justify-content: space-between; color: #777; font-size: 0.8em;">
                <span>📝 {row['post_title'][:80]}</span>
                <span>{source_label} · <a href="{source_url}" target="_blank" style="color: #6699cc;">View Source ↗</a></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_and_render(time_filter: str | None = None, order: str = "p.final_score DESC", limit: int = 50) -> None:
    query, params = build_query(time_filter=time_filter, order=order, limit=limit)
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    if not rows:
        st.info("No problems found matching your filters.")
        return

    st.caption(f"Showing {len(rows)} results")
    for row in rows:
        render_card(dict(row))


# --- Tabs ---
tab_today, tab_trending, tab_alltime = st.tabs(["📅 Today", "🔥 Trending", "🏆 All Time Best"])

with tab_today:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    fetch_and_render(time_filter=today_start, order="p.final_score DESC")

with tab_trending:
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    fetch_and_render(time_filter=seven_days_ago, order="p.momentum_score DESC, p.final_score DESC")

with tab_alltime:
    fetch_and_render(order="p.final_score DESC", limit=100)

# --- Footer stats ---
with get_db() as conn:
    total_posts = conn.execute("SELECT COUNT(*) as c FROM raw_posts").fetchone()["c"]
    total_problems = conn.execute("SELECT COUNT(*) as c FROM problems").fetchone()["c"]
    total_clusters = conn.execute("SELECT COUNT(*) as c FROM clusters").fetchone()["c"]

st.sidebar.markdown("---")
st.sidebar.metric("Total Posts", total_posts)
st.sidebar.metric("Problems Extracted", total_problems)
st.sidebar.metric("Clusters", total_clusters)
