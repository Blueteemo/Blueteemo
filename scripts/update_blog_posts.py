#!/usr/bin/env python3
"""Refresh the README's latest-post section from the blog RSS feed.

Uses the Python standard library so that this workflow does not depend on
legacy Node.js RSS parsing packages. Does not commit; the workflow commits once.
"""
from datetime import timezone
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

FEED_URL = "https://blog.207723.xyz/rss.xml"
README = Path("README.md")
START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"
MAX_POSTS = 5


def latest_posts():
    request = Request(
        FEED_URL,
        headers={"User-Agent": "rss-parser", "Accept": "application/rss+xml"},
    )
    with urlopen(request, timeout=40) as response:
        feed = ET.fromstring(response.read())

    channel = feed.find("channel")
    if channel is None:
        raise ValueError("Expected an RSS feed with a channel element")

    posts = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        if not title or not link or not published:
            raise ValueError("RSS item is missing a title, link or pubDate")
        link = link.replace("http://localhost:8090", "https://blog.207723.xyz")
        parsed = urlsplit(link)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid blog post URL: {link}")
        date = parsedate_to_datetime(published)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        posts.append((date, escape(title, quote=True), link))

    if not posts:
        raise ValueError("RSS feed contains no posts; keeping README unchanged")
    posts.sort(key=lambda post: post[0], reverse=True)
    return posts[:MAX_POSTS], len(posts)


def main():
    posts, count = latest_posts()
    readme = README.read_text(encoding="utf-8")
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("Expected one complete BLOG-POST-LIST marker pair")
    before, remainder = readme.split(START, 1)
    _, after = remainder.split(END, 1)
    lines = [f"- [{title}]({url}) " for _, title, url in posts]
    content = "\n" + "\n\n".join(lines) + "\n"
    updated = before + START + content + END + after
    if updated != readme:
        README.write_text(updated, encoding="utf-8")
        print(f"Updated {README} with {len(posts)} posts ({count} in feed)")
    else:
        print(f"No blog changes ({len(posts)} posts, {count} in feed)")


if __name__ == "__main__":
    main()
