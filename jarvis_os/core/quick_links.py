from typing import Dict, List, Any

SITE_MAP: Dict[str, str] = {
    "github": "https://github.com",
    "linkedin": "https://linkedin.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "gmail": "https://mail.google.com",
    "youtube": "https://youtube.com",
    "notion": "https://notion.so",
    "leetcode": "https://leetcode.com"
}

QUICK_LINKS: List[Dict[str, str]] = [
    {"name": "GitHub", "site": "github"},
    {"name": "LinkedIn", "site": "linkedin"},
    {"name": "ChatGPT", "site": "chatgpt"},
    {"name": "Claude", "site": "claude"},
    {"name": "Gmail", "site": "gmail"},
    {"name": "YouTube", "site": "youtube"},
    {"name": "Notion", "site": "notion"},
    {"name": "LeetCode", "site": "leetcode"}
]


def get_top_sites(limit: int = 3) -> List[Dict[str, Any]]:
    """Returns top sites by persistent usage count (from usage.py)."""
    from jarvis_os.core.usage import get_usage_summary
    data = get_usage_summary()
    all_sites: Dict[str, int] = data.get("quick_links", {})
    sorted_sites = sorted(all_sites.items(), key=lambda item: item[1], reverse=True)
    top = []
    for site, count in sorted_sites[:limit]:
        name = site.title()
        for link in QUICK_LINKS:
            if link["site"] == site:
                name = link["name"]
                break
        top.append({"name": name, "site": site, "count": count})
    return top
