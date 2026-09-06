"""Native section navigation for the shared inner-page shell.

Heading targets use the same source-preserving helper as blog articles. The
normalised hero is the sole insertion point; existing article copy stays intact.
"""
from html import escape
import re

from blog_navigation import enrich_article
from hero_layout import hero_end


def add_page_navigation(body, path, *, context=""):
    """Return a page with a compact section menu after its recognised hero.

Indexes and blog articles already have their own discovery/contents navigation.
Contact stays focused on its form. Native details and anchors work without JS.
"""
    if path in {"/", "/products", "/blogs", "/woods-we-use", "/contact", "/404"} or path.startswith("/blogs/post/"):
        return body
    if hero_end(body) is None:
        return body
    enriched, toc, _ = enrich_article(body)
    listing = re.search(r'<ol class="cw-article-toc__list">(.*?)</ol>', toc, re.S)
    count = listing.group(1).count("<li>") if listing else 0
    menu = ""
    if count >= 2:
        menu = ('<details class="cw-section-menu"><summary>On this page '
                f'<span>{count} sections</span></summary>'
                '<nav aria-label="On this page"><ol class="cw-section-links">'
                + listing.group(1) + '</ol></nav></details>')
    if not context and not menu:
        return enriched
    end = hero_end(enriched)
    navigation = '<div class="cw-page-navigation"><div class="cw-page-navigation__inner">' + context + menu + '</div></div>'
    return enriched[:end] + navigation + enriched[end:]


def parent_navigation(label, href):
    return ('<nav class="cw-section-parent" aria-label="Section navigation"><a href="'
            + escape(href, quote=True) + '"><span aria-hidden="true">←</span> '
            + escape(label) + '</a></nav>')
