"""Small, dependency-free navigation helpers for published blog articles.

enrich_article(html) returns (html_with_missing_h2_ids, toc_html, reading_minutes).
Only an id attribute may be inserted into the original HTML. Existing bytes,
including existing IDs, are otherwise preserved. Existing duplicate/empty IDs
are left alone and omitted from the TOC because their targets are ambiguous.

render_article_navigation(post, related_posts, link) returns a footer containing
Back to blog, an optional topic link, and at most three caller-selected articles.
``link`` is the generator's site-base-aware URL helper, e.g. build.u.

Post fields: slug, title; optional desc, topic_slug, topic_label, topic_href.
``topic`` may also be a string key or a dict with slug/key, label/name, href/url.
The caller supplies related posts in relevance order. Where both records expose
a topic key, a different topic is rejected; missing topic metadata is treated as
the caller's explicit selection. No chronological next/previous loop is made.
"""

from __future__ import annotations

from collections import Counter
from html import escape, unescape
from html.parser import HTMLParser
import math
import re
import unicodedata
from urllib.parse import quote


_IGNORED = {"script", "style", "template", "noscript"}
_BLOCKS = {"p", "div", "section", "article", "li", "tr", "td", "th",
           "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}


class _ArticleScan(HTMLParser):
    """Record positions without serialising or reformatting the source tree."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = [0]
        self.line_starts.extend(m.end() for m in re.finditer("\n", source))
        self.ids: Counter[str] = Counter()
        self.headings: list[dict] = []
        self.heading: dict | None = None
        self.visible: list[str] = []
        self.ignored: list[str] = []

    def _position(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def _finish_heading(self):
        if self.heading is not None:
            self.heading["text"] = re.sub(r"\s+", " ", "".join(self.heading.pop("parts"))).strip()
            self.headings.append(self.heading)
            self.heading = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        # Reserve IDs even in non-reading content, so insertion cannot collide.
        if attributes.get("id") is not None:
            self.ids[attributes["id"]] += 1
        if tag in _IGNORED:
            self.ignored.append(tag)
            return
        if self.ignored:
            return
        if tag in _BLOCKS:
            self.visible.append(" ")
            if self.heading is not None and tag != "h2":
                self.heading["parts"].append(" ")
        if tag == "h2":
            self._finish_heading()
            self.heading = {
                "start": self._position(),
                "tag": self.get_starttag_text(),
                "has_id": "id" in attributes,
                "id": attributes.get("id"),
                "parts": [],
            }
        elif tag == "img" and self.heading is not None and attributes.get("alt"):
            self.heading["parts"].append(attributes["alt"])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.ignored:
            if tag in self.ignored:
                # Tolerate malformed nested non-content elements in imports.
                self.ignored = self.ignored[:len(self.ignored) - 1 - self.ignored[::-1].index(tag)]
            return
        if tag == "h2":
            self._finish_heading()
        if tag in _BLOCKS:
            self.visible.append(" ")

    def _text(self, data):
        if not self.ignored:
            self.visible.append(data)
            if self.heading is not None:
                self.heading["parts"].append(data)

    def handle_data(self, data):
        self._text(data)

    def handle_entityref(self, name):
        self._text(unescape("&" + name + ";"))

    def handle_charref(self, name):
        self._text(unescape("&#" + name + ";"))

    def finish(self):
        self.close()
        self._finish_heading()


def _plain_text(value) -> str:
    scan = _ArticleScan(str(value or ""))
    scan.feed(scan.source)
    scan.finish()
    return re.sub(r"\s+", " ", "".join(scan.visible)).strip()


def _heading_slug(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).casefold()
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    slug = re.sub(r"[^\w]+", "-", folded, flags=re.UNICODE).strip("-_")
    return (slug[:72].rstrip("-_") or "section")


def _toc(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    links = "".join(
        '<li><a href="#' + escape(quote(anchor, safe="-_.:"), quote=True) + '">'
        + escape(text) + '</a></li>' for anchor, text in items
    )
    listing = '<ol class="cw-article-toc__list">' + links + '</ol>'
    return (
        '<nav class="cw-article-toc cw-article-toc--desktop" aria-label="On this page">'
        '<p class="cw-article-toc__title">On this page</p>' + listing + '</nav>'
        '<details class="cw-article-toc cw-article-toc--mobile">'
        '<summary>On this page <span>(' + str(len(items)) + ' sections)</span></summary>'
        '<nav aria-label="On this page">' + listing + '</nav></details>'
    )


def enrich_article(content: str) -> tuple[str, str, int]:
    """Add stable H2 targets, desktop/mobile contents and a 220-word/min estimate.

    Generated IDs avoid IDs on any element, even a later element in the source.
    Repeated headings get ``-2``, ``-3`` etc. Running this twice is idempotent.
    Existing empty or duplicate IDs are never rewritten; those headings are not
    linked from the contents. Script/style/template/noscript words are ignored.
    """
    scan = _ArticleScan(content)
    scan.feed(content)
    scan.finish()
    reserved = set(scan.ids)
    edits = []
    items = []
    for heading in scan.headings:
        text = heading["text"]
        if not text:
            continue
        if heading["has_id"]:
            anchor = heading["id"]
            if not anchor or scan.ids[anchor] != 1:
                continue
        else:
            base = _heading_slug(text)
            anchor = base
            serial = 2
            while anchor in reserved:
                anchor = f"{base}-{serial}"
                serial += 1
            reserved.add(anchor)
            tag = heading["tag"]
            # Insert immediately before > (or />), leaving all original bytes.
            end_offset = 2 if tag.endswith("/>") else 1
            position = heading["start"] + len(tag) - end_offset
            edits.append((position, ' id="' + escape(anchor, quote=True) + '"'))
        items.append((anchor, text))
    enriched = content
    for position, addition in reversed(edits):
        enriched = enriched[:position] + addition + enriched[position:]
    words = re.findall(r"[^\W_]+(?:[’'-][^\W_]+)*", "".join(scan.visible), flags=re.UNICODE)
    return enriched, _toc(items), max(1, math.ceil(len(words) / 220))


def _topic(post: dict) -> tuple[str, str, str]:
    topic = post.get("topic")
    if isinstance(topic, dict):
        key = topic.get("slug") or topic.get("key") or ""
        label = topic.get("label") or topic.get("name") or key
        href = topic.get("href") or topic.get("url") or ""
    else:
        key = post.get("topic_slug") or topic or ""
        label = post.get("topic_label") or key
        href = post.get("topic_href") or ""
    return str(key), _plain_text(label), str(href)


def render_article_navigation(post: dict, related_posts: list[dict], link) -> str:
    """Render local blog/topic navigation and up to three relevant reading links.

    Topic URLs must be site-relative. Related destinations always derive from
    their slug, not arbitrary URLs. No self links, repeated slugs or explicit
    cross-topic matches are included. Descriptions are optional, plain and short.
    """
    topic_key, topic_label, topic_href = _topic(post)
    back = '<a class="cw-article-back" href="' + escape(link('/blogs'), quote=True) + '"><span aria-hidden="true">←</span> Back to blog</a>'
    topic_link = ""
    if topic_label and topic_href.startswith("/") and not topic_href.startswith("//"):
        topic_link = '<a class="cw-article-topic" href="' + escape(link(topic_href), quote=True) + '">More in ' + escape(topic_label) + ' <span aria-hidden="true">↗</span></a>'
    links = '<nav class="cw-article-route" aria-label="Blog navigation">' + back + topic_link + '</nav>'
    cards = []
    seen = {str(post.get("slug") or "").strip("/")}
    for candidate in related_posts or []:
        slug = str(candidate.get("slug") or "").strip("/")
        candidate_topic, _, _ = _topic(candidate)
        if not slug or slug in seen or (topic_key and candidate_topic and topic_key != candidate_topic):
            continue
        seen.add(slug)
        title = _plain_text(candidate.get("title") or slug.replace("-", " ")).split("|")[0].strip()
        if not title:
            continue
        description = _plain_text(candidate.get("desc") or "")
        if len(description) > 165:
            description = description[:162].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        href = escape(link('/blogs/post/' + quote(slug, safe="-_")), quote=True)
        cards.append('<li><a href="' + href + '"><span class="cw-article-related__title">'
                     + escape(title) + '<span aria-hidden="true">↗</span></span>'
                     + ('<span class="cw-article-related__description">' + escape(description) + '</span>' if description else '')
                     + '</a></li>')
        if len(cards) == 3:
            break
    reading = ""
    if cards:
        reading = ('<section class="cw-article-related" aria-label="Continue reading">'
                   '<h2>Continue reading</h2>'
                   + ('<p class="cw-article-related__intro">More from ' + escape(topic_label) + '.</p>' if topic_label else '')
                   + '<ul>' + "".join(cards) + '</ul></section>')
    return '<div class="cw-article-navigation">' + links + reading + '</div>'
