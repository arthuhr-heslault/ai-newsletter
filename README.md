# AI Articles Digest (Streamlit)

A Streamlit app that aggregates AI/ML articles from ~20 top sources via RSS, filters by date, and optionally summarizes via CrewAI.

## Features
- Curated list of ~20 AI/ML RSS sources
- Fetch, deduplicate, and sort articles
- Filter by date range (defaults to last 30 days)
- Search across titles and summaries
- Optional CrewAI summarization (if installed and API key provided)
- Export filtered results to CSV

## Setup
```powershell
# Clone or create the folder, then:
cd ai-newsletter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional summarization support
# pip install crewai openai
```

## Run
```powershell
streamlit run src/app.py
```

## Configure sources
Edit `src/sources.py` to add/remove feeds. You can also fork this list into UI later.

## Notes
- Some sources may rate-limit or have non-standard feeds; errors are skipped.
- CrewAI use is minimal: a single-call summarizer via an LLM. You can expand to multi-agent flows.
