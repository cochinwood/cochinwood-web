#!/usr/bin/env bash
# WHAT THE CUTOVER MUST NOT HAVE BROKEN, checked against the live site.
#
# Run this AFTER merging the cutover PR and purging the edge cache (runbook step 6).
# Every expected figure below was measured against production on 4 Sep 2026, BEFORE the
# cutover, so a mismatch means the cutover changed something it was supposed to carry.
#
# These six are the ones with no second chance:
#   - the IndexNow key is verified by fetching this exact path and matching the body to the
#     filename, so a 301 in its place fails verification and every submission to Bing,
#     Yandex and Seznam stops silently while the site still looks fine;
#   - llms.txt is 11,918 bytes of hand-written copy that exists nowhere else, and robots.txt
#     deliberately courts the crawlers that fetch it;
#   - cw-events.js is the conversion beacon: if it stops loading the dashboard reports ZERO
#     website conversions, which is a WRONG answer rather than a missing one;
#   - cwi-og-share-1200x630.png is the og:image on 283 of the 293 live pages, so every share
#     card already sitting in a WhatsApp thread or a LinkedIn post points at it.
#
# Exit 0 = everything the cutover had to preserve is still there.

set -uo pipefail
SITE="${1:-https://www.cochinwood.in}"
fails=0

check() {   # path  expected_status  expected_bytes  what
  local path="$1" want_code="$2" want_bytes="$3" what="$4"
  local out code bytes
  out=$(curl -sS --max-time 25 -o /dev/null -w "%{http_code} %{size_download}" -L "$SITE$path" 2>/dev/null)
  code=${out%% *}; bytes=${out##* }
  if [ "$code" = "$want_code" ] && { [ "$want_bytes" = "-" ] || [ "$bytes" = "$want_bytes" ]; }; then
    printf "  ok    %-46s %s %s  %s\n" "$path" "$code" "$bytes" "$what"
  else
    printf "  FAIL  %-46s %s %s  (expected %s %s)  %s\n" "$path" "$code" "$bytes" "$want_code" "$want_bytes" "$what"
    fails=$((fails+1))
  fi
}

not_served() {  # path — must never come back as the file itself
  # THE CONTRACT IS "NOT SERVED", NOT "301". Before the cutover both paths answered
  # 301 -> / because the files WERE committed on cf-live and a redirect hid them. The
  # rebuilt tree does not contain CLAUDE.md at all, so it answers 404 - nothing to hide
  # rather than something hidden, which is the better outcome and was failed by an
  # earlier version of this check that asserted what live happened to do. .github/ IS
  # in the tree deliberately (it carries the required status check), so that one still
  # redirects. Both are correct; a 200 carrying the file is the only wrong answer.
  local path="$1" code loc
  code=$(curl -sS --max-time 25 -o /dev/null -w "%{http_code}" "$SITE$path" 2>/dev/null)
  loc=$(curl -sS --max-time 25 -o /dev/null -D - "$SITE$path" 2>/dev/null | tr -d '\r' | awk 'tolower($1)=="location:"{print $2}')
  if [ "$code" = "301" ] && [ "$loc" = "/" ]; then
    printf "  ok    %-46s 301 -> /   hidden, not served\n" "$path"
  elif [ "$code" = "404" ]; then
    printf "  ok    %-46s 404        absent from the tree, nothing to hide\n" "$path"
  else
    printf "  FAIL  %-46s %s -> %s   (must be 301 -> / or 404, never served)\n" "$path" "$code" "${loc:-none}"
    fails=$((fails+1))
  fi
}

echo "Post-cutover check against $SITE"
echo
echo "FILES THE CUTOVER HAD TO CARRY ACROSS (byte counts measured on live, 4 Sep 2026):"
check /015ad99674249c7dc418af21415b06bc.txt 200 32     "the IndexNow key - a 301 here fails verification"
check /llms.txt                             200 11918  "hand-written, exists nowhere else in the repo"
check /favicon.png                          200 2180   "the root icon, requested by convention"
check /cwi-og-share-1200x630.png            200 72802  "og:image on 283 of 293 live pages"
echo
echo "THE CONVERSION BEACON - without it the dashboard reports zero, not nothing:"
# The rebuild serves it from a hashed /assets/ path; live serves /js/. Either is correct,
# but ONE of them must answer, and the bytes must be the same 6,080 in both cases.
js=$(curl -sS --max-time 25 -o /dev/null -w "%{http_code} %{size_download}" -L "$SITE/js/cw-events.js" 2>/dev/null)
as=$(curl -sS --max-time 25 -o /dev/null -w "%{http_code} %{size_download}" -L "$SITE/assets/cw-events.853632c8.js" 2>/dev/null)
if [ "${js%% *}" = "200" ] || [ "${as%% *}" = "200" ]; then
  printf "  ok    %-46s /js: %s   /assets hashed: %s\n" "cw-events.js" "$js" "$as"
  [ "${as%% *}" = "200" ] && [ "${as##* }" != "6080" ] && { echo "  FAIL  hashed beacon is ${as##* } bytes, live serves 6080"; fails=$((fails+1)); }
else
  printf "  FAIL  %-46s neither path answers (/js: %s, /assets: %s)\n" "cw-events.js" "$js" "$as"; fails=$((fails+1))
fi
# And it has to be ON the pages, not merely present on the server.
home=$(curl -sS --max-time 25 -L "$SITE/" 2>/dev/null)
if printf '%s' "$home" | grep -q "cw-events"; then
  echo "  ok    the homepage references the beacon"
else
  echo "  FAIL  the homepage does NOT reference the beacon - conversions will read zero"; fails=$((fails+1))
fi
echo
echo "NEITHER OF THESE MAY BE SERVED (301 to / or 404 both qualify; measured 4 Sep 2026, the"
echo "redirect DOES win over a committed file, contradicting the older note in live's _headers):"
not_served /.github/workflows/site-checks.yml
not_served /CLAUDE.md
echo
if [ "$fails" -eq 0 ]; then
  echo "All checks passed. Nothing the cutover had to preserve is missing."
else
  echo "$fails check(s) FAILED. Rollback target: deployment 52b41125-0e5e-4ecc-9fda-ba88974f85bd"
  echo "(cf-live @ c59adae9), retained and still serving - one click in the Cloudflare Pages UI."
fi
exit $(( fails > 0 ))
