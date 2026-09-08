# AI card provenance review — 8 September 2026

This is a source and file review for the four AI-assisted Wood Encyclopedia cards. It is an evidence record, not a C2PA assertion or legal opinion.

## What the delivered files say

The sixteen WebP card variants for Melia dubia, Neem, Sal and Kadam now carry an unsigned XMP packet with IPTC `DigitalSourceType` set to `http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`. Each packet names the OpenAI built-in image tool, records the source URL and calls the image an AI-assisted visual. It intentionally contains no creator or ownership attribution and no C2PA/JUMBF manifest, signature or Content Credentials claim.

`tools/ai_card_provenance.py` is the idempotent writer and verifier. `tools/test_ai_card_provenance.py` checks every declared responsive file, source URL and SHA-256 value, and refuses a C2PA container claim. The content manifests retain the native-output and source-reference hashes independently of the delivered WebP hash.

## Neem source review

The real botanical reference on the Neem species page is the current Wikimedia Commons file *Neem Tree in Rajasthan, India.jpg*, uploaded as the author's own work by TheSlumPanda under CC BY-SA 4.0. Its file page explicitly allows sharing and adapting with attribution and ShareAlike. The website's local WebP is a proportional technical derivative; its existing attribution, source link and CC BY-SA licence record remain intact.

The AI card's separate visual reference is Deore et al. (2020), Plant Archives 20(2), Figure 6. The current Plant Archives copyright and licensing policy states that authors retain copyright while the publisher allows anyone to reuse, distribute and reproduce content when the original is properly cited. The site records this accurately as a publisher reuse policy requiring citation, rather than a Creative Commons licence. The generated card is clearly labelled as an illustrative reconstruction and is not represented as a verified specimen, a photographed Cochin Wood product or a documentary wood-grain record.

## Sitemap treatment

The website's image sitemap has one standards-oriented purpose: discovery of images actually shown in indexed HTML. It emits only `image:loc`; it does not emit deprecated caption, title, geolocation or unstandardised provenance tags. Since it has no field for an AI-provenance assertion, the sitemap is retained for image discovery while the visible HTML and embedded XMP carry the disclosure. This change does not claim that any search engine reads or trusts the XMP.

## Primary records

- Wikimedia Commons, [Neem Tree in Rajasthan, India.jpg](https://commons.wikimedia.org/wiki/File:Neem_Tree_in_Rajasthan,_India.jpg), current author, source and CC BY-SA 4.0 declaration.
- Creative Commons, [CC BY-SA 4.0 legal code](https://creativecommons.org/licenses/by-sa/4.0/legalcode), including its adaptation and attribution terms.
- Plant Archives, [Deore et al. source PDF](https://www.plantarchives.org/20-2/3399-3404%20%286263%29.pdf) and [current copyright and licensing policy](https://www.plantarchives.org/publicationethics.html).
- IPTC, [guidance for synthetic media metadata](https://iptc.org/news/iptc-publishes-metadata-guidance-for-ai-generated-synthetic-media/), which recommends the `trainedAlgorithmicMedia` URI used here.
