import os, re, shutil, glob, urllib.request
M="C:/Users/Edwin David/cochinwood-site"
CF="C:/Users/EDWIND~1/AppData/Local/Temp/claude/_cfmirror"
TMP="C:/Users/EDWIND~1/AppData/Local/Temp/claude"

# fresh staging = full mirror copy (minus git + build logs)
if os.path.exists(CF): shutil.rmtree(CF)
shutil.copytree(M, CF, ignore=shutil.ignore_patterns('.git','_mirror.log','README.md','.nojekyll'))

# --- self-host the original fonts ---
css=open(TMP+"/origfonts.css",encoding='utf-8').read()
os.makedirs(CF+"/assets/fonts",exist_ok=True)
UA={'User-Agent':'Mozilla/5.0'}
urls=sorted(set(re.findall(r'https://fonts\.gstatic\.com/[^)]+\.woff2', css)))
seen={}
for u in urls:
    base=u.split('/')[-1]
    fam='heebo' if 'heebo' in u else 'cormorant' if 'cormorant' in u else 'poppins' if 'poppins' in u else 'breeserif' if 'breeserif' in u else 'f'
    name=f"{fam}-{base}"
    data=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read()
    open(CF+"/assets/fonts/"+name,'wb').write(data)
    seen[u]="fonts/"+name
out=css
for u,l in seen.items(): out=out.replace(u,l)
open(CF+"/assets/fonts.css","w",encoding='utf-8').write(out)
print("fonts self-hosted:", len(seen), "woff2")

# --- per page: swap the zoho webfonts link -> local; strip tracking scripts ---
TRACK=re.compile(r'<script[^>]*(googletagmanager|google-analytics|gtag|salesiq|pagesense|clarity\.ms|connect\.facebook|hotjar|doubleclick)[^>]*>.*?</script>', re.S|re.I)
TRACK_INLINE=re.compile(r'<script[^>]*>[^<]*(gtag\(|GoogleAnalytics|_setAccount|ZohoSalesIQ|pagesense|clarity\()[^<]*</script>', re.S|re.I)
FONTLINK=re.compile(r'<link[^>]*webfonts\.zoho\.in[^>]*>', re.I)
n=0; stripped=0
for fp in glob.glob(CF+"/**/*.html", recursive=True):
    t=open(fp,encoding='utf-8',errors='replace').read()
    orig=t
    t=FONTLINK.sub('<link rel="stylesheet" href="/assets/fonts.css">', t)
    t2=TRACK.sub('', t); t2=TRACK_INLINE.sub('', t2)
    if t2!=t: stripped+=1
    if t2!=orig:
        open(fp,'w',encoding='utf-8').write(t2); n+=1
print("pages updated:", n, "| pages with tracking stripped:", stripped)

# CF headers + nojekyll
open(CF+"/.nojekyll","w").close()
open(CF+"/_headers","w",encoding='utf-8').write("/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
tot=sum(len(f) for _,_,f in os.walk(CF))
print("cleaned mirror staged:", tot, "files")
# verify a page no longer references zoho fonts
home=open(CF+"/index.html",encoding='utf-8').read()
print("home still refs webfonts.zoho:", 'webfonts.zoho' in home, "| refs local fonts.css:", '/assets/fonts.css' in home)
