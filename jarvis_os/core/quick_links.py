from typing import Dict, List, Any
import json

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

SITE_USAGE: Dict[str, int] = {}

def record_site_usage(site_alias: str):
    if site_alias in SITE_MAP:
        SITE_USAGE[site_alias] = SITE_USAGE.get(site_alias, 0) + 1

def get_top_sites(limit: int = 3) -> List[Dict[str, Any]]:
    sorted_usage = sorted(SITE_USAGE.items(), key=lambda item: item[1], reverse=True)
    top = []
    for site, count in sorted_usage[:limit]:
        name = site.title()
        for link in QUICK_LINKS:
            if link["site"] == site:
                name = link["name"]
                break
        top.append({"name": name, "site": site, "count": count})
    return top
