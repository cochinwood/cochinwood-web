"""Topic-based blog discovery without changing indexed article URLs or content."""
from collections import Counter
from html import escape, unescape


def render_directory(posts, taxonomy, link, hero_image):
    assignments = taxonomy["posts"]
    counts = Counter(assignments[p["slug"]] for p in posts)
    def card(post):
        title = unescape((post.get("title") or post["slug"]).split("|")[0].strip())
        desc = unescape(post.get("desc") or "")
        return (f'<a data-blog-topic="{escape(assignments[post["slug"]])}" href="{link("/blogs/post/" + post["slug"])}">'
                f'<b>{escape(title)}</b><span>{escape(desc[:160])}</span></a>')
    topics = '<a href="#articles" data-blog-topic-filter="all" aria-current="true">All posts <span>' + str(len(posts)) + '</span></a>'
    groups = ""
    for topic in taxonomy["topics"]:
        key, label = topic["id"], topic["label"]
        group = [p for p in posts if assignments[p["slug"]] == key]
        topics += (f'<a href="#blog-topic-{key}" data-blog-topic-filter="{key}">{escape(label)} '
                   f'<span>{counts[key]}</span></a>')
        groups += (f'<section class="cw-blog-group" data-blog-group="{key}" id="blog-topic-{key}">'
                   f'<div class="cw-blog-group-heading"><h2>{escape(label)}</h2>'
                   f'<span class="cw-blog-group-count">{len(group)} guides</span></div>'
                   f'<p>{escape(topic["description"])}</p><div class="cw-bloglist">'
                   + "".join(card(p) for p in group) + '</div></section>')
    return f'''<section class="cw-hero cw-hero--light"><div class="cw-wrap"><div class="cw-hero__layout">
  <div class="cw-hero__content"><p class="cw-hero__ey">From the Cochin Wood desk</p><h1>Material knowledge.<br><em>Made practical.</em></h1><p>Explore plywood grades, export packing and supply guides. Browse by topic or search for the question you need to answer.</p><a class="cw-btn cw-btn--p" href="#articles">Find a guide &darr;</a></div>
  <figure class="cw-hero__media">{hero_image}</figure>
</div></div></section>
<section class="cw-blog-directory" id="articles"><div class="cw-wrap">
  <div class="cw-blogtools"><div class="cw-blog-searchfield"><label for="cw-blogsearch">Search {len(posts)} guides</label><div class="cw-blog-searchrow"><input id="cw-blogsearch" type="search" autocomplete="off" placeholder="Try marine, crate, Kochi or IS 710"><button id="cw-blogclear" type="button" hidden>Clear filters</button></div></div><p class="cw-blogcount" id="cw-blogcount" role="status" aria-live="polite">{len(posts)} guides across {len(taxonomy["topics"])} topics</p></div>
  <div class="cw-blog-browse"><nav class="cw-blog-topics" aria-label="Blog topics"><p>Browse by topic</p>{topics}</nav>
  <div class="cw-blogindex">{groups}<p id="cw-blogempty" hidden>No guides match these filters. Clear the filters to browse again, or <a href="{link('/contact')}">ask our desk</a>.</p></div></div>
</div></section>'''
