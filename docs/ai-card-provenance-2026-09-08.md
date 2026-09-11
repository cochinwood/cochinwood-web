# AI card provenance review — 8 September 2026

This is a source and file review for the four AI-assisted Wood Encyclopedia card assets. It is an evidence record, not a C2PA assertion or legal opinion.

## What the delivered files say

The sixteen WebP variants for Melia dubia, Neem, Sal and Kadam carry an unsigned XMP packet with IPTC `DigitalSourceType` set to `http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`. Each packet names the OpenAI built-in image tool, records the source URL and calls the image an AI-assisted visual. It intentionally contains no creator or ownership attribution and no C2PA/JUMBF manifest, signature or Content Credentials claim. Twelve variants for Melia dubia, Sal and Kadam remain eligible for directory rendering. The four Neem variants are retained as withheld evidence and are not rendered or listed in the image sitemap pending permission.

`tools/ai_card_provenance.py` is the idempotent writer and verifier. Its read-only mode checks every declared responsive and master SHA-256 value as well as XMP and C2PA/JUMBF markers. `tools/test_ai_card_provenance.py` includes stale-hash, malformed/duplicate-XMP and C2PA fixtures, plus a write-mode fixture that proves the encoded image payload remains unchanged while hashes refresh. The content manifests retain the native-output and source-reference hashes independently of the delivered WebP hash.

## Neem source review

The real botanical reference on the Neem species page is the current Wikimedia Commons file *Neem Tree in Rajasthan, India.jpg*, uploaded as the author's own work by TheSlumPanda under CC BY-SA 4.0. Its file page explicitly allows sharing and adapting with attribution and ShareAlike. The website's local WebP is a proportional technical derivative; its existing attribution, source link and CC BY-SA licence record remain intact.

The AI card's separate visual reference is Deore et al. (2020), Plant Archives 20(2), Figure 6. The current Plant Archives policy says that authors retain copyright while it permits cited reuse, distribution and reproduction. It does not establish permission to create and publish a source-guided generated derivative. The retained Neem asset is therefore rights-ambiguous and withheld from public rendering and the image sitemap pending written permission from the relevant rightsholder. This is a risk-management decision, not a conclusion about infringement. The Wikimedia botanical reference is a separate CC BY-SA 4.0 work and does not provide a rights basis for the Deore figure.

## Sitemap treatment

The website's image sitemap has one standards-oriented purpose: discovery of images actually shown in indexed HTML. It emits only `image:loc`; it does not emit deprecated caption, title, geolocation or unstandardised provenance tags. The withheld Neem variants are absent because no rendered HTML references them. Since it has no field for an AI-provenance assertion, the sitemap is retained for eligible image discovery while visible HTML and embedded XMP carry the disclosure. This change does not claim that any search engine reads or trusts the XMP.

## Primary records

- Wikimedia Commons, [Neem Tree in Rajasthan, India.jpg](https://commons.wikimedia.org/wiki/File:Neem_Tree_in_Rajasthan,_India.jpg), current author, source and CC BY-SA 4.0 declaration.
- Creative Commons, [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode), including its adaptation and attribution terms.
- Plant Archives, [Deore et al. source PDF](https://www.plantarchives.org/20-2/3399-3404%20%286263%29.pdf) and [current copyright and licensing policy](https://www.plantarchives.org/publicationethics.html).
- IPTC, [guidance for synthetic media metadata](https://iptc.org/news/iptc-publishes-metadata-guidance-for-ai-generated-synthetic-media/), which recommends the `trainedAlgorithmicMedia` URI used here.
