from typing import List, Dict

# Curated AI/ML RSS sources with simple region tags.
# Regions: "Global", "North America", "Europe", "Asia".
DEFAULT_SOURCES: List[Dict[str, str]] = [
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "region": "North America"},
    {"name": "Google AI Blog", "url": "https://ai.googleblog.com/feeds/posts/default", "region": "North America"},
    {"name": "DeepMind", "url": "https://deepmind.google/discover/blog/feed.xml", "region": "Europe"},
    {"name": "Anthropic", "url": "https://www.anthropic.com/news.xml", "region": "North America"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "region": "Europe"},
    {"name": "Stability AI", "url": "https://stability.ai/blog/rss.xml", "region": "Europe"},
    {"name": "NVIDIA Technical Blog - AI", "url": "https://developer.nvidia.com/blog/tag/ai/feed/", "region": "North America"},
    {"name": "Berkeley BAIR Blog", "url": "https://bair.berkeley.edu/blog/feed.xml", "region": "North America"},
    {"name": "Stanford HAI", "url": "https://hai.stanford.edu/news/feed", "region": "North America"},
    {"name": "MIT News - AI", "url": "https://news.mit.edu/topic/artificial-intelligence2-rss.xml", "region": "North America"},
    {"name": "Allen AI (AI2)", "url": "https://allenai.org/news/rss.xml", "region": "North America"},
    {"name": "Papers With Code - Daily", "url": "https://paperswithcode.com/news/daily/rss", "region": "Global"},
    {"name": "The Gradient", "url": "https://thegradient.pub/rss/", "region": "Global"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/tag/artificial-intelligence/feed/", "region": "North America"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/artificial-intelligence/rss/index.xml", "region": "North America"},
    {"name": "NYT - AI", "url": "https://rss.nytimes.com/services/xml/rss/nyt/ArtificialIntelligence.xml", "region": "North America"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "region": "North America"},
    # Additional Asia-focused sources
    {"name": "Preferred Networks Tech Blog", "url": "https://tech.preferred.jp/en/blog/rss.xml", "region": "Asia"},
    {"name": "LINE Engineering (EN)", "url": "https://engineering.linecorp.com/en/blog/rss/", "region": "Asia"},
    {"name": "Sony AI Blog", "url": "https://ai.sony/blog/index.xml", "region": "Asia"},
]
