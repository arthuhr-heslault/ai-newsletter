import os
import csv
import pathlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import feedparser
from dateutil import tz
from dateutil.parser import parse as parse_date

import sys
import pathlib

# Add the parent directory of `src` to the Python path
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from src.sources import DEFAULT_SOURCES

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

LOCAL_TZ = tz.tzlocal()


class Article:
    def __init__(self, title: str, link: str, source: str, published: datetime,
                 authors: Optional[str] = None, summary: Optional[str] = None) -> None:
        self.title = title
        self.link = link
        self.source = source
        self.published = published
        self.authors = authors
        self.summary = summary


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz.UTC).astimezone(LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ)


def fetch_feed(url: str) -> Any:
    return feedparser.parse(url)


def parse_entry(entry: Any, source_name: str) -> Optional[Article]:
    published_dt: Optional[datetime] = None
    if entry.get("published_parsed"):
        try:
            published_dt = datetime(*entry.published_parsed[:6])
        except Exception:
            published_dt = None
    if not published_dt and entry.get("published"):
        try:
            published_dt = parse_date(entry.get("published"))
        except Exception:
            published_dt = None
    if not published_dt:
        for key in ("pubDate", "dc:date"):
            value = entry.get(key)
            if value:
                try:
                    published_dt = parse_date(value)
                    break
                except Exception:
                    continue
    if not published_dt:
        if entry.get("updated_parsed"):
            try:
                published_dt = datetime(*entry.updated_parsed[:6])
            except Exception:
                published_dt = None
        if not published_dt and entry.get("updated"):
            try:
                published_dt = parse_date(entry.get("updated"))
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
        published=to_local(published_dt),
        authors=authors,
        summary=summary_text,
    )


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


def filter_last_days_top_n(articles: List[Article], days: int, top_n: int) -> List[Article]:
    end = datetime.now(tz=LOCAL_TZ)
    start = end - timedelta(days=days)
    filtered = [a for a in articles if start <= a.published <= end]
    return sorted(filtered, key=lambda a: a.published, reverse=True)[:top_n]


def generate_summary(articles: List[Article]) -> str:
    if not articles:
        return "No articles available for this period."

    highlights = ", ".join(a.title for a in articles[:3])
    summary = (
        f"This week's AI digest highlights the top advancements and discussions in the field. "
        f"Key topics include {highlights}. "
        f"Stay updated with the latest breakthroughs and insights from the AI community."
    )
    return summary


THEME_CSS = """
<style>
body { background: #FFFFFF; color: #000000; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
.container { max-width: 1080px; margin: 0 auto; padding: 24px 16px; }
.header { border-bottom: 2px solid #009ddf; padding-bottom: 8px; margin-bottom: 20px; }
.header h1 { margin: 0; color: #009ddf; }
.meta { color: #333; opacity: 0.8; }
.card { border: 1px solid #009ddf; border-radius: 10px; padding: 14px 16px; margin: 14px 0; background: #f9f9f9; }
.card h3 { margin: 0 0 6px 0; color: #000; }
.card .meta { font-size: 0.9rem; margin-bottom: 8px; }
.card .summary { margin: 6px 0 10px 0; }
.btn { display: inline-block; background: #009ddf; color: #fff; padding: 6px 10px; border-radius: 6px; text-decoration: none; }
.btn:hover { background: #008cc8; }
.small { font-size: 0.9rem; color: #333; }
.footer { margin-top: 24px; border-top: 1px solid #e5e5e5; padding-top: 12px; }
</style>
"""


def render_html(articles: List[Article], period_days: int, summary: str) -> str:
    if not articles:
        body = "<p>No articles found for this period.</p>"
    else:
        items = []
        for a in articles:
            meta = f"{a.source} · {a.published.strftime('%Y-%m-%d %H:%M')}"
            if a.authors:
                meta += f" · {a.authors}"
            items.append(
                f"""
                <div class=\"card\">
                  <h3>{a.title}</h3>
                  <div class=\"meta\">{meta}</div>
                  <div class=\"summary\">{(a.summary or '').strip()}</div>
                  <a class=\"btn\" href=\"{a.link}\" target=\"_blank\">Read</a>
                </div>
                """
            )
        body = f"<p class=\"small\">{summary}</p>" + "\n".join(items)

    now = datetime.now(tz=LOCAL_TZ)
    html = f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>AI Articles Digest</title>
  {THEME_CSS}
</head>
<body>
  <div class=\"container\">
    <div class=\"header\">
      <h1>AI Articles Digest</h1>
      <div class=\"meta\">Generated on {now.strftime('%Y-%m-%d %H:%M')} · Last {period_days} days</div>
    </div>
    {body}
    <div class=\"footer small\">Theme: #009ddf blue on white with black text.</div>
  </div>
</body>
</html>
"""
    return html


def write_csv(path: pathlib.Path, articles: List[Article]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "source", "published", "link", "authors"]) 
        for a in articles:
            w.writerow([a.title, a.source, a.published.isoformat(), a.link, a.authors or ""]) 


def send_email(subject: str, body: str, to_email: str, attachments: List[pathlib.Path]) -> None:
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        raise ValueError("Please set EMAIL_SENDER and EMAIL_PASSWORD environment variables.")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    for attachment in attachments:
        with attachment.open("rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{attachment.name}"')
        msg.attach(part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)


def main() -> None:
    period_days = int(os.environ.get("PERIOD_DAYS", "7"))
    out_dir = pathlib.Path("dist")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_articles = load_articles(DEFAULT_SOURCES)
    recent = filter_last_days_top_n(all_articles, period_days, 10)

    summary = generate_summary(recent)
    html = render_html(recent, period_days, summary)
    (out_dir / "newsletter.html").write_text(html, encoding="utf-8")
    write_csv(out_dir / "newsletter.csv", recent)

    docs_dir = pathlib.Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "index.html").write_text(html, encoding="utf-8")

    print(f"Wrote: {out_dir / 'newsletter.html'}")
    print(f"Wrote: {out_dir / 'newsletter.csv'}")
    print(f"Wrote: {docs_dir / 'index.html'} (for GitHub Pages)")

    # Send the newsletter via email
    recipient_email = os.environ.get("RECIPIENT_EMAIL")
    if recipient_email:
        send_email(
            subject="Weekly AI Newsletter",
            body=html,
            to_email=recipient_email,
            attachments=[out_dir / "newsletter.html", out_dir / "newsletter.csv"]
        )
        print(f"Newsletter sent to {recipient_email}")
    else:
        print("No RECIPIENT_EMAIL environment variable set. Skipping email sending.")


if __name__ == "__main__":
    main()
