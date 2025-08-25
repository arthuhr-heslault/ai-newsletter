import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set

import streamlit as st
import feedparser
from dateutil import tz
from dateutil.parser import parse as parse_date
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from sources import DEFAULT_SOURCES

LOCAL_TZ = tz.tzlocal()

class Article(BaseModel):
    title: str
    link: str
    source: str
    published: datetime
    authors: Optional[str] = None
    summary: Optional[str] = None


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz.UTC).astimezone(LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz.UTC)
    return dt.astimezone(tz.UTC)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8))
def fetch_feed(url: str) -> Any:
    return feedparser.parse(url)


def parse_entry(entry: Any, source_name: str) -> Optional[Article]:
    published_dt: Optional[datetime] = None
    for key in ("published", "updated", "pubDate", "dc:date"):
        value = entry.get(key)
        if value:
            try:
                published_dt = parse_date(value)
                break
            except Exception:
                continue
    if not published_dt and entry.get("published_parsed"):
        try:
            published_dt = datetime(*entry.published_parsed[:6])
        except Exception:
            published_dt = None

    if not published_dt:
        return None

    authors = None
    if entry.get("author"):
        authors = entry.get("author")
    elif entry.get("authors"):
        try:
            authors = ", ".join(a.get("name") for a in entry.get("authors") if a.get("name"))
        except Exception:
            authors = None

    summary_text = None
    for key in ("summary", "description"):
        if entry.get(key):
            summary_text = entry.get(key)
            break

    link = entry.get("link") or ""

    return Article(
        title=entry.get("title", "(no title)"),
        link=link,
        source=source_name,
        published=to_utc(published_dt),  # Ensure the date is stored in UTC
        authors=authors,
        summary=summary_text,
    )


@st.cache_data(ttl=60 * 15, show_spinner=False)
def load_articles(sources: List[Dict[str, str]]) -> List[Article]:
    articles: List[Article] = []
    for src in sources:
        url = src.get("url")
        name = src.get("name") or url
        if not url:
            continue
        try:
            feed = fetch_feed(url)
            for entry in feed.entries:
                art = parse_entry(entry, name)
                if art:
                    articles.append(art)
        except Exception:
            continue
    seen: set[str] = set()
    deduped: List[Article] = []
    for a in articles:
        key = a.link or a.title
        if key in seen:
            continue
        seen.add(key)
        deduped.append(a)
    deduped.sort(key=lambda a: a.published, reverse=True)
    return deduped


def crewai_available() -> bool:
    try:
        import crewai  # noqa: F401
        return True
    except Exception:
        return False


def summarize_with_crewai(text: str, api_key: Optional[str]) -> Optional[str]:
    try:
        from crewai import LLM
        if not api_key:
            return None
        llm = LLM(model="gpt-4o-mini", api_key=api_key)
        prompt = (
            "Summarize the following AI article in 3 bullet points with key takeaways. "
            "Keep it factual and concise.\n\n" + text[:6000]
        )
        response = llm.call(prompt)
        return response
    except Exception:
        return None


def apply_filters(
    articles: List[Article],
    start_date: datetime,
    end_date: datetime,
    allowed_sources: Set[str],
    allowed_regions: Set[str],
    source_name_to_region: Dict[str, str],
    query: str,
) -> List[Article]:
    filtered = []
    for a in articles:
        if not (start_date <= a.published <= end_date):
            continue
        if allowed_sources and a.source not in allowed_sources:
            continue
        reg = source_name_to_region.get(a.source, "Global")
        if allowed_regions and reg not in allowed_regions:
            continue
        filtered.append(a)
    if query:
        q = query.lower()
        filtered = [a for a in filtered if q in a.title.lower() or (a.summary and q in a.summary.lower())]
    return filtered


def render_article(a: Article, do_summarize: bool, api_key: Optional[str]):
    card_html = f"""
    <div class="article-card">
      <h3>{a.title}</h3>
      <div class="meta">{a.source} · {a.published.strftime('%Y-%m-%d %H:%M')}{' · ' + a.authors if a.authors else ''}</div>
      <div class="summary">{(a.summary or '').strip()}</div>
      <div class="actions"><a class="btn" href="{a.link}" target="_blank" rel="noopener noreferrer">Read</a></div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="AI Articles Digest", page_icon="AI", layout="wide")
    st.title("Weekly Onepoint AI Newsletter")
    st.caption("Aggregated from top sources. Filter the last 30 days and beyond.")

    # --- CSS (robust overrides, including the TOGGLE) ---
    st.markdown(
        """
        <style>
        /* Force Streamlit theme primary to blue (prevents red fallback) */
        :root {
          --primary-color: #009ddf !important;
          --color-primary: #009ddf !important;
          --accent-color: #009ddf !important;
        }
        body, .stApp { background-color: #FFFFFF; color: #000000; }

        /* Inputs (Date + Search) - dark bg + white text */
        .stTextInput > div > div > input,
        .stDateInput > div > div > input,
        input[type="text"], input[type="search"] {
            background: #262626 !important;
            color: #ffffff !important;
            caret-color: #ffffff !important;
        }
        .stTextInput div[data-baseweb="input"],
        .stDateInput div[data-baseweb="input"] {
            background: #262626 !important;
            color: #ffffff !important;
            border-color: #009ddf !important;
        }
        .stTextInput div[data-baseweb="input"] input,
        .stDateInput div[data-baseweb="input"] input {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        input:-webkit-autofill,
        input:-webkit-autofill:hover,
        input:-webkit-autofill:focus {
            -webkit-text-fill-color: #ffffff !important;
            -webkit-box-shadow: 0 0 0px 1000px #262626 inset !important;
            box-shadow: 0 0 0px 1000px #262626 inset !important;
            caret-color: #ffffff !important;
        }
        .stTextInput > div > div > input::placeholder,
        .stDateInput > div > div > input::placeholder,
        input::placeholder { color: #bbbbbb !important; }
        .stTextInput svg, .stDateInput svg { color: #ffffff !important; fill: #ffffff !important; }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #FFFFFF !important;
            color: #000000 !important;
            border-right: 2px solid #009ddf !important;
        }
        section[data-testid="stSidebar"] * { color: #000000 !important; }

        /* Multiselect container (big box -> dark grey) */
        .stMultiSelect div[data-baseweb="select"] {
            background: #262626 !important;
            border: 1px solid #009ddf !important;
            border-radius: 6px !important;
            color: #ffffff !important;
        }
        .stMultiSelect div[data-baseweb="select"] > div { background: #262626 !important; color: #ffffff !important; }
        .stMultiSelect div[data-baseweb="select"] input { color: #ffffff !important; }
        .stMultiSelect div[role="listbox"] { background: #262626 !important; color: #ffffff !important; }
        .stMultiSelect [role="option"] { color: #ffffff !important; }
        .stMultiSelect svg { color: #ffffff !important; fill: #ffffff !important; }

        /* Multiselect tags (chips -> blue) */
        .stMultiSelect [data-baseweb="tag"] {
            background: linear-gradient(135deg, #009ddf 0%, #00b4ff 100%) !important;
            color: #ffffff !important;
            border-radius: 4px !important;
            padding: 2px 6px !important;
            font-weight: 600 !important;
            border: none !important;
        }
        .stMultiSelect [data-baseweb="tag"] span { color: #ffffff !important; }

        /* ===== Toggle: "Summarize with CrewAI" ===== */
        /* Outer shell – thin grey padding ring */
        [data-testid="stToggle"] [data-baseweb="switch"],
        [data-testid="stToggle"] [role="switch"] {
            background-color: #262626 !important;      /* thin outer padding */
            border-radius: 9999px !important;
            padding: 2px !important;
        }

        /* Remove any vendor gradients that keep the red */
        [data-testid="stToggle"] [data-baseweb="switch"],
        [data-testid="stToggle"] [role="switch"],
        [data-testid="stToggle"] [data-baseweb="switch"] * ,
        [data-testid="stToggle"] [role="switch"] * {
            background-image: none !important;
            filter: none !important;
        }

        /* Track (pill) – BLUE in both states */
        [data-testid="stToggle"] [data-baseweb="switch"] > div:last-child,
        [data-testid="stToggle"] [role="switch"] > div:last-child {
            background-color: #009ddf !important;
            border: 1px solid #009ddf !important;
            width: 44px !important;
            height: 24px !important;
            box-shadow: none !important;
        }
        [data-testid="stToggle"] [data-baseweb="switch"][aria-checked="true"] > div:last-child,
        [data-testid="stToggle"] [role="switch"][aria-checked="true"] > div:last-child {
            background-color: #009ddf !important;
            border-color: #009ddf !important;
        }

        /* Thumb (the circle) – always GREY so it's visible ON or OFF */
        [data-testid="stToggle"] [data-baseweb="switch"] > div:last-child > div,
        [data-testid="stToggle"] [role="switch"] > div:last-child > div {
            background-color: #9aa0a6 !important;  /* grey knob */
            box-shadow: none !important;
        }

        /* Focus ring */
        [data-testid="stToggle"] [data-baseweb="switch"]:focus-visible > div:last-child,
        [data-testid="stToggle"] [role="switch"]:focus-visible > div:last-child {
            outline: 2px solid #00b4ff !important;
            outline-offset: 2px !important;
        }

        /* Article cards */
        .article-card {
            border: 1px solid #009ddf;
            border-radius: 10px;
            padding: 14px 16px;
            margin: 18px 0;
            background: #f9f9f9;
        }
        .article-card h3 { color: #000000; }
        .article-card .meta { color: #333; font-size: 0.9rem; margin-bottom: 8px; }
        .article-card .summary { color: #000000; }

        /* Pagination (Google-like) */
        .pagination { text-align: center; margin: 20px 0; }
        .pagination a {
            margin: 0 6px; text-decoration: none;
            color: #009ddf; font-weight: 500; font-size: 16px;
        }
        .pagination a.active {
            color: #fff !important; background: #009ddf;
            border-radius: 50%; padding: 4px 10px; font-weight: 700;
        }
        .pagination a.disabled { color: #bbb !important; pointer-events: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Settings")
        # Set the default date filter to last week
        default_days = 7  # Change from 30 to 7 for last week
        today = datetime.now(tz=LOCAL_TZ)
        start = today - timedelta(days=default_days)
        date_range: Tuple[datetime, datetime] = st.date_input("Date range", (start.date(), today.date()))
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date = datetime.combine(date_range[0], datetime.min.time(), tzinfo=LOCAL_TZ)
            end_date = datetime.combine(date_range[1], datetime.max.time(), tzinfo=LOCAL_TZ)
        else:
            start_date, end_date = start, today

        sources = DEFAULT_SOURCES
        source_names = [s["name"] for s in sources]
        source_name_to_region = {s["name"]: s.get("region", "Global") for s in sources}
        regions = sorted({s.get("region", "Global") for s in sources})
        selected_sources = st.multiselect("Sources", options=source_names, default=source_names)
        selected_regions = st.multiselect("Regions", options=regions, default=regions)

        query = st.text_input("Search (title/summary)", placeholder="Type here...")

        can_summarize = crewai_available()
        summarize_toggle = st.toggle("Summarize with CrewAI", value=False, disabled=not can_summarize)
        crewai_api_key = (
            st.text_input("OpenAI-compatible API key", type="password", placeholder="sk-...")
            if summarize_toggle else None
        )

        # Preserve filters and page state across page changes
        if "filters" not in st.session_state:
            st.session_state["filters"] = {
                "date_range": (start_date, end_date),
                "selected_sources": source_names,
                "selected_regions": regions,
                "query": "",
                "page": 1,
            }

        # Update filters only if they are changed
        if st.session_state["filters"]["date_range"] != (start_date, end_date):
            st.session_state["filters"]["date_range"] = (start_date, end_date)
        if st.session_state["filters"]["selected_sources"] != selected_sources:
            st.session_state["filters"]["selected_sources"] = selected_sources
        if st.session_state["filters"]["selected_regions"] != selected_regions:
            st.session_state["filters"]["selected_regions"] = selected_regions
        if st.session_state["filters"]["query"] != query:
            st.session_state["filters"]["query"] = query

        # Use filters from session state
        start_date, end_date = st.session_state["filters"]["date_range"]
        selected_sources = st.session_state["filters"]["selected_sources"]
        selected_regions = st.session_state["filters"]["selected_regions"]
        query = st.session_state["filters"]["query"]

        # Preserve page state
        if "page" not in st.session_state:
            st.session_state["page"] = 1
        page = st.session_state["page"]

        # Sync page with URL query params
        try:
            qp = st.query_params
            if "page" in qp and str(qp.get("page")):
                p = int(qp.get("page"))
                if p != page:
                    st.session_state["page"] = p
        except Exception:
            pass

    all_articles = load_articles(sources)

    filter_key = (
        str(start_date.date()), str(end_date.date()),
        tuple(sorted(selected_sources)), tuple(sorted(selected_regions)),
        (query or "").strip().lower(),
    )
    if st.session_state.get("_filter_key") != filter_key:
        st.session_state["_filter_key"] = filter_key
        st.session_state["page"] = 1

    filtered = apply_filters(
        all_articles, start_date, end_date,
        set(selected_sources), set(selected_regions),
        source_name_to_region, query
    )

    st.subheader(f"Results ({len(filtered)})")

    per_page = 10
    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = st.session_state.get("page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["page"] = page
    try:
        st.query_params.update({"page": str(page)})
    except Exception:
        pass

    start_idx, end_idx = (page - 1) * per_page, min(page * per_page, total)

    for a in filtered[start_idx:end_idx]:
        render_article(a, summarize_toggle if 'summarize_toggle' in locals() else False,
                       crewai_api_key if 'crewai_api_key' in locals() else None)

    # Pagination
    if total_pages > 1:
        st.markdown(f"Page {page} of {total_pages} — showing {start_idx+1} to {end_idx}")
        html = '<div class="pagination">'
        if page > 1:
            html += f'<a href="?page={page-1}">◀</a>'
        else:
            html += '<a class="disabled">◀</a>'
        start_win = max(1, page-2)
        end_win = min(total_pages, page+2)
        for p in range(start_win, end_win+1):
            if p == page:
                html += f'<a class="active">{p}</a>'
            else:
                html += f'<a href="?page={p}">{p}</a>'
        if page < total_pages:
            html += f'<a href="?page={page+1}">▶</a>'
        else:
            html += '<a class="disabled">▶</a>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
