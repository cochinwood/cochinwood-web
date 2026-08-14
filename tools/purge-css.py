import re, sys, zlib

corpus = set(open('/tmp/corpus.txt', encoding='utf-8').read().split('\n'))

def split_top(css):
    """Split stylesheet into (prelude, body_or_None, raw) blocks at top level."""
    out, i, n, depth, start = [], 0, len(css), 0, 0
    while i < n:
        c = css[i]
        if c == '{':
            if depth == 0:
                prelude = css[start:i]
                j, d = i, 0
                while j < n:
                    if css[j] == '{': d += 1
                    elif css[j] == '}':
                        d -= 1
                        if d == 0: break
                    j += 1
                out.append((prelude, css[i+1:j], css[start:j+1]))
                i = j + 1; start = i; continue
        i += 1
    return out

def selector_can_match(sel):
    toks = re.findall(r'\.(-?[A-Za-z_][\w-]*)', sel) + re.findall(r'#(-?[A-Za-z_][\w-]*)', sel)
    if not toks:
        return True                      # tag-only, *, :root — keep conservatively
    return all(t in corpus for t in toks)

def purge(css):
    kept, dropped = [], 0
    for prelude, body, raw in split_top(css):
        p = prelude.strip()
        if p.startswith('@'):
            name = p.split()[0].lower()
            if name in ('@media', '@supports', '@layer'):
                inner, d = purge(body)
                dropped += d
                if inner.strip():
                    kept.append(p + '{' + inner + '}')
                continue
            kept.append(raw)             # @font-face, @keyframes, @import, @charset
            continue
        sels = [s.strip() for s in p.split(',') if s.strip()]
        live = [s for s in sels if selector_can_match(s)]
        if live:
            kept.append(','.join(live) + '{' + body + '}')
            dropped += len(sels) - len(live)
        else:
            dropped += len(sels)
    return '\n'.join(kept), dropped

for f in sys.argv[1:]:
    css = open(f, encoding='utf-8', errors='ignore').read()
    out, dropped = purge(css)
    r0, r1 = len(css.encode()), len(out.encode())
    g0 = len(zlib.compress(css.encode(), 9)); g1 = len(zlib.compress(out.encode(), 9))
    print(f"{f.split('/')[-1]:22} raw {r0:>7}->{r1:>7} ({100-r1*100//r0:>2}% off)   gzip {g0:>6}->{g1:>6}   selectors dropped: {dropped}")
    open(f + '.purged', 'w', encoding='utf-8').write(out)
