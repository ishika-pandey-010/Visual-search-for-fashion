# Competitive analysis

Research date: 2026-10-20. Sources are each company's own pages where possible, otherwise launch coverage, so feature claims are the makers' descriptions, not tested behaviour. Several of these launched in 2017–2019, and the products may have changed since.

## Products shoppers already use

| Product | How it works (per the source) | What we took | Where we differ |
| --- | --- | --- | --- |
| [ASOS Style Match](https://www.asos.com/us/customer-care/product-stock/how-does-your-style-match-feature-work) | A camera icon in the app's search bar; take or upload a photo and similar products appear. ASOS says it looks at colour, pattern and garment type, and that the image isn't stored or shown in the device's gallery. Launch coverage put the searchable range at about 85,000 products ([Fox Business](https://www.foxbusiness.com/features/asos-style-match-is-like-shazam-for-fashion), [VentureBeat](https://venturebeat.com/business/asos-lets-fashionistas-everywhere-find-new-clothes-using-just-photos)) | Entry point where search already is (FR-01). Saying plainly that the photo isn't kept (FR-15, D-12). Type and colour as the first test of "similar" (D-06) | No published accuracy or speed numbers; we publish both |
| [Amazon StyleSnap](https://www.aboutamazon.com/news/retail/stylesnap-will-change-the-way-you-shop-forever) | Launched 2019 in the Amazon app: upload a photo or screenshot of an outfit and get similar items. Amazon says computer vision and deep learning find the clothing in a picture whatever its background or setting, and that results also weigh brand, price range and reviews ([ecommerceBytes](https://www.ecommercebytes.com/2019/06/06/amazon-helps-fashion-shoppers-with-visual-search/)) | Screenshots are a first-class input, not only camera photos (P2, FR-01) | Our catalogue has no price or reviews, so ranking is visual only (PRD §8). That keeps the eval about what the model sees |
| [Pinterest Lens and Shop the Look](https://www.socialmediatoday.com/social-business/how-pinterests-new-shop-look-pins-work-and-potential-brand-opportunities) | Lens is a camera search for Pins. Shop the Look puts dots on the items in a fashion Pin; Pinterest described object detection finding the products, visual search pulling candidates, and fashion-trained human curators confirming the best matches. Matches look similar rather than being the exact product | The name and the idea of acting on one item in a look. Similar-not-identical as the promise | No detection in v1; the shopper crops (D-10). No human curation; the similarity floor is our guard against bad matches (D-09) |
| [Google Lens](https://lens.google/howlensworks/) | Google says Lens generates several possible results and ranks them by probable relevance. When it can't tell what you mean it may show only the single closest match, and for products it may use signals such as user ratings | Ranking several candidates, and a different answer when confidence is low | Lens narrows to its best guess when unsure; we tell the shopper nothing is close and let them choose to see more (FR-05). The catalogue is one shop's, not the web |

## Models and open-source work

| Source | What it tells us |
| --- | --- |
| [Marqo-FashionCLIP](https://huggingface.co/Marqo/marqo-fashionCLIP) ([GitHub](https://github.com/marqo-ai/marqo-FashionCLIP)) | Apache 2.0, fine-tuned from ViT-B-16 (`laion2b_s34b_b88k`), loads in open_clip as `hf-hub:Marqo/marqo-fashionCLIP`. The published benchmarks are text-to-image and category-to-product. No image-to-image numbers, and nothing on phone photos. That's the gap our eval measures (D-04) |
| [OpenCLIP](https://github.com/mlfoundations/open_clip) | Generic ViT-B-32 weights trained on LAION-2B; the baseline every fashion model claims to beat. We check that claim on our own photos rather than taking it from a benchmark table |
| [CLIP4Cir demo](https://github.com/ABaldrati/CLIP4CirDemo) | Fashion retrieval from an image plus a text edit ("like this, but red"). Shows where the product could go next; out of scope for v1 (PRD §8) |

## What nobody publishes

None of the shopper-facing products say how often their results are relevant on real photos, how long a search takes, or what happens when the catalogue has nothing close. Those three are exactly what this project measures and puts in the README, next to a random baseline so the numbers mean something.
