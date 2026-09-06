"""Normalize imported hero templates without rewriting their substantive content.

``normalize_page_hero(body, path, breadcrumb_html='')`` returns ``(body, consumed)``.
``hero_end(body)`` returns the offset immediately after the normalized hero, or None.
Source after the original hero is untouched. This module has no third-party dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
import re


VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
IGNORED = frozenset(('script', 'style', 'template', 'noscript'))


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str | None]
    start: int
    open_end: int
    close_start: int
    end: int
    parent: HtmlNode | None = field(default=None, repr=False)
    children: list[HtmlNode] = field(default_factory=list, repr=False)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get('class') or '').split())

    def contains(self, node: HtmlNode) -> bool:
        return self.start <= node.start and node.end <= self.end


class HtmlFragment(HTMLParser):
    """Source-offset parser; nodes expose start/open_end/close_start/end/children."""
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.nodes: list[HtmlNode] = []
        self._stack: list[HtmlNode] = []
        self._lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.feed(source)
        self.close()
        for node in self._stack:
            node.close_start = node.end = len(source)

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self._offset()
        end = start + len(self.get_starttag_text())
        parent = self._stack[-1] if self._stack else None
        node = HtmlNode(tag, dict(attrs), start, end, end, end, parent)
        if parent:
            parent.children.append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self._stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self._stack.pop()

    def handle_endtag(self, tag):
        start = self._offset()
        end = self.source.find('>', start) + 1
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i].tag == tag:
                for node in self._stack[i:]:
                    node.close_start = start
                    node.end = end
                del self._stack[i:]
                break

    def raw(self, node: HtmlNode) -> str:
        return self.source[node.start:node.end]

    def inner(self, node: HtmlNode) -> str:
        return self.source[node.open_end:node.close_start]


def parse_fragment(source: str) -> HtmlFragment:
    return HtmlFragment(source)


def _has(node: HtmlNode, names: set[str]) -> bool:
    return bool(node.classes & names)


def _ignored(node: HtmlNode) -> bool:
    while node:
        if node.tag in IGNORED:
            return True
        node = node.parent
    return False


def _remove_ranges(source: str, start: int, end: int, nodes: list[HtmlNode]) -> str:
    cursor = start
    parts = []
    for node in sorted(nodes, key=lambda n: (n.start, -n.end)):
        if node.start < cursor or node.start < start or node.end > end:
            continue
        parts.append(source[cursor:node.start])
        cursor = node.end
    parts.append(source[cursor:end])
    return ''.join(parts)


_ATTR = r'\s+{name}\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)'


def _opening(raw: str, classes: list[str], tag: str | None = None) -> str:
    # Original ids, URLs, accessibility attributes and media attributes stay intact.
    raw = re.sub(_ATTR.format(name='class'), '', raw, flags=re.I)
    raw = re.sub(_ATTR.format(name='style'), '', raw, flags=re.I)
    if tag:
        raw = re.sub(r'^<[^\s/>]+', '<' + tag, raw, count=1)
    suffix = '/>' if raw.endswith('/>') else '>'
    return raw[:-len(suffix)] + (f' class="{escape(" ".join(classes), quote=True)}"' if classes else '') + suffix


def _clean(source: str, force_class: str | None = None) -> str:
    tree = HtmlFragment(source)
    edits = []
    for i, node in enumerate(tree.nodes):
        if _ignored(node):
            continue
        original = node.classes
        # Drop old hero/template styling hooks, retaining functional catalogue
        # family-navigation classes, data attributes and all destinations.
        kept = [c for c in (node.attrs.get('class') or '').split()
                if not c.startswith(('cwp__', 'cwg__', 'cw__', 'cw-hero', 'cw-btn')) and c not in {'cw-wrap', 'cw-sec__h', 'cw-eyebrow'}]
        if force_class and i == 0:
            kept.append(force_class)
        elif node.tag == 'h1':
            kept.append('cw-page-hero__title')
        elif node.tag == 'figcaption':
            kept.append('cw-page-hero__caption')
        if node.tag == 'span' and node.parent and node.parent.tag == 'h1' and re.search(r'font-style\s*:\s*italic', node.attrs.get('style') or '', re.I):
            kept.append('cw-page-hero__scientific')
        if node.tag == 'a' and any('btn' in c or 'button' in c for c in original):
            kept.append('cw-page-hero__button')
            if any('secondary' in c or c.endswith('--g') for c in original):
                kept.append('cw-page-hero__button--secondary')
        if original & {'cw-hero__cta', 'cwp__hero-actions', 'cw__hero-actions'}:
            kept.append('cw-page-hero__actions')
        if original & {'cwp__hero-meta', 'cw__hero-meta', 'cw-hero__strip'}:
            kept.append('cw-page-hero__facts')
        raw = source[node.start:node.open_end]
        updated = _opening(raw, kept)
        if raw != updated:
            edits.append((node.start, node.open_end, updated))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    return source


def normalize_page_hero(body: str, path: str, breadcrumb_html: str = '') -> tuple[str, bool]:
    if path.rstrip('/') == '' or 'class="cw-page-hero' in body:
        return body, False
    tree = HtmlFragment(body)
    h1 = next((n for n in tree.nodes if n.tag == 'h1' and not _ignored(n)), None)
    if not h1:
        return body, False
    hero = h1.parent
    hero_classes = {'cw-hero', 'cwp__hero', 'cw__page-hero', 'cwg__hero'}
    while hero and not (_has(hero, hero_classes) or (path.rstrip('/') == '/contact' and 'cw-section__head' in hero.classes)):
        hero = hero.parent
    if not hero:
        return body, False
    descendants = [n for n in tree.nodes if hero.contains(n) and not _ignored(n)]
    content = h1.parent
    text_classes = {'cw-hero__content', 'cwp__hero-text', 'cw__hero-text', 'cwg__container', 'cw-section__head'}
    while content != hero and content and not _has(content, text_classes):
        content = content.parent
    content = content or hero
    media = next((n for n in descendants if _has(n, {'cw-hero__media', 'cwp__hero-img', 'cw__hero-img'})
                  and any(n.contains(i) and i.tag == 'img' for i in descendants)), None)
    crumb = next((n for n in descendants if _has(n, {'cwp__crumb', 'cw__crumb', 'cwg__crumb', 'cw-article-context'})), None)
    eyebrow = next((n for n in descendants if n.start < h1.start and _has(n, {'cw-hero__ey', 'cw-eyebrow', 'cwp__eyebrow', 'cw__eyebrow', 'cwg__eyebrow'})), None)
    removed = [n for n in (h1, crumb, eyebrow, media) if n]
    supporting = _remove_ranges(body, content.open_end, content.close_start, removed)
    extras = '' if content == hero else _remove_ranges(body, hero.open_end, hero.close_start, [content] + [n for n in (media, crumb) if n])
    # Wrappers left around removed content contain no substantive content. Keep
    # any real ancillary strip or byline outside the main text container.
    if not re.sub(r'<[^>]*>|\s+', '', extras):
        extras = ''
    crumb_source = tree.raw(crumb) if crumb else breadcrumb_html
    crumb_markup = (_clean(crumb_source, 'cw-page-hero__breadcrumbs') if crumb_source
                    else '<div class="cw-page-hero__breadcrumbs" aria-hidden="true"></div>')
    title = _clean(tree.raw(h1))
    kicker = _clean(tree.raw(eyebrow), 'cw-page-hero__eyebrow') if eyebrow else ''
    compact = not media
    if not kicker and not compact:
        kicker = '<div class="cw-page-hero__eyebrow" aria-hidden="true"></div>'
    classes = ['cw-page-hero'] + (['cw-page-hero--compact'] if compact else [])
    if path.rstrip('/') == '/contact':
        classes.append('cw-page-hero--contact')
    if path.startswith('/blogs/post/'):
        classes.append('cw-page-hero--article')
    contact = path.rstrip('/') == '/contact'
    outer_tag = 'header' if contact else hero.tag
    opening = _opening(body[hero.start:hero.open_end], classes, outer_tag)
    image = _clean(tree.raw(media), 'cw-page-hero__media') if media else ''
    normalized = (opening + '<div class="cw-page-hero__inner">' + crumb_markup
                  + '<div class="cw-page-hero__heading">' + kicker + title + '</div>'
                  + image + '<div class="cw-page-hero__support">' + _clean(supporting)
                  + _clean(extras) + '</div></div></' + outer_tag + '>')
    # Removed hero nodes leave indentation-only lines in this new markup.
    # Clean only the assembled hero; the original article body stays untouched.
    normalized = re.sub(r'(?m)^[ \t]+$', '', normalized)
    if contact:
        quote = hero.parent
        while quote and quote.attrs.get('id') != 'quote':
            quote = quote.parent
        if quote:
            return (body[:quote.start] + normalized + body[quote.start:hero.start]
                    + body[hero.end:]), bool(breadcrumb_html)
    return body[:hero.start] + normalized + body[hero.end:], bool(breadcrumb_html)


def hero_end(body: str) -> int | None:
    """Insertion offset for a sibling page navigator; None when no hero exists."""
    return next((n.end for n in HtmlFragment(body).nodes if 'cw-page-hero' in n.classes), None)
