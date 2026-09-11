# content/export/countries/ — lane data the build does not read yet

**Nothing in this directory reaches the site.** `export_section.py` loads exactly one data file:

```python
# export_section.py:56
def _load():
    with open(os.path.join(CDIR, "export.json"), encoding="utf-8") as f:
```

There is no scan of `countries/`. Until someone wires it, `python build.py` still reports
`9 export pages` — the hub and the original eight — and the `<slug>.body.html` files that go
with these entries sit unused next to it.

The directory exists so that several agents could each add lanes in parallel without four of
them editing the same 30 KB `export.json` and colliding. Each file here is **one element of
the `countries` array**, in the exact shape `export_section.page()` expects, plus a few keys
whose names begin with `_` that are notes for whoever wires this and must not be shipped.

## Wiring it, option A — fold the files into export.json (no code change)

For each slug, append the object minus its `_`-prefixed keys to `countries` in
`content/export/export.json`, and add the slug to `shared.related.order`. That is the whole
job; the hero, TL;DR, breadcrumb, canonical, WebPage and FAQPage schema, the sitemap entry and
the back-links from every other lane all follow from the data, exactly as
`export_section.py`'s module docstring says.

## Wiring it, option B — teach the builder to read this directory

Merge in `_load()`, after `export.json` is parsed:

```python
cdir = os.path.join(CDIR, "countries")
for fn in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(cdir, fn), encoding="utf-8") as f:
        c = json.load(f)
    data["countries"].append({k: v for k, v in c.items() if not k.startswith("_")})
```

…and still add the slugs to `shared.related.order` (or derive that order from the merged list).
Sorted filename order keeps two builds byte-identical; `os.listdir` order alone does not.

**Do not skip the `_`-prefix filter.** Those keys carry unresolved questions for Edwin and a
`[TO CONFIRM]` inventory; they are not page content.

## Why these lanes carry no `import` block

`export_section.import_essentials()` builds the "Import essentials" table from
`shared["import"]`, and two of its rows are hard-coded Gulf facts:

```python
# export_section.py:105-107
rows = [("HS code", s["hs_code"]),
        ("Customs duty", s["customs_duty"]),      # "5% GCC Common External Tariff on CIF value"
        ("VAT at import", imp["vat"])]
```

That customs-duty string is true for the six GCC lanes and false everywhere else. Giving a
United States or Chile entry an `import` block would print a 5% GCC tariff to a real buyer on
a page that has nothing to do with the GCC — a confidently wrong number, which is the one
failure mode this content is not allowed to have.

So these five lanes follow the Sri Lanka and Israel precedent (`d.get("import")` returns
`None`, the section renders empty) and carry their own `Import essentials` table, with the
same `id="import"`, inside their `<slug>.body.html`. Cells that no page on this site can
source are marked `[TO CONFIRM]` rather than filled in.

If someone later adds per-lane overrides to `import_essentials()` — `imp.get("customs_duty",
s["customs_duty"])` and an optional VAT row — the tables can move back out of the prose and
into data. Nothing here blocks that.

## Cross-lane dependency

`puerto-rico.body.html` links to `/export/united-states`. `tools/check_site.py`'s link check
fails on a target the build does not emit, so wire those two together, or drop that one anchor.
