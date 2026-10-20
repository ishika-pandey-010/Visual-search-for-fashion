# Glossary

Terms used across the spec, PRD, stories, eval plan and UAT sheet. If a doc uses a word differently from this page, the doc is wrong.

| Term | Meaning |
| --- | --- |
| **Catalogue** | The searchable set of about 5,000 products: 10 article types, at most 500 each (D-03). |
| **Product** | One catalogue row: ID, article type, base colour, gender, name, image. |
| **Article type** | The source's product type, such as `Shirts` or `Casual Shoes`. One of the two halves of the relevance rule. |
| **Base colour** | The source's colour name for a product, as written (46 values). `Navy Blue` and `Blue` are different colours under the strict rule. |
| **Reserved types** | Sarees, Watches and Sunglasses: real product types kept out of the catalogue so the no-match path can be tested. |
| **Query photo** | A real phone photo used in the eval, labelled with type and colour, in `eval/queries/`. |
| **Dev / test split** | The one-time division of query photos. Dev is for tuning; test is for the reported number and is read once per milestone. |
| **Embedding** | The 512-number vector a model produces for an image. Similar-looking images get vectors pointing in similar directions. |
| **Cosine similarity / score** | How closely two embeddings point the same way, from −1 to 1. With L2-normalised vectors it equals the inner product, which FAISS computes. |
| **Index** | The FAISS file holding every catalogue embedding for one model, searched exactly (D-05). |
| **Relevant** | A result with the same article type and base colour as the query's label (D-06). |
| **Type-only rule** | The looser rule: same article type, any colour. Reported beside the strict rule. |
| **Top-10 match rate / Recall@10** | Share of query photos with at least one relevant result in the top 10. Strictly a hit rate (see [eval-plan.md](eval-plan.md) §4). |
| **Precision@10** | Relevant results among the ten, divided by ten. |
| **MRR** | Mean reciprocal rank: 1 ÷ the rank of the first relevant result, averaged; 0 when there is none. |
| **Random baseline** | Ten products drawn at random per query. Shows what the metrics score with no model at all. |
| **Similarity floor** | The score under which the top result is too weak to show, so the shopper sees "No close match" (D-09). |
| **No close match** | The panel shown instead of results when the top score is under the floor. |
| **Quality warning** | The non-blocking banner for blurry or dark photos (D-14). |
| **p50 / p95** | The latency that half, or 95%, of requests come in under. |
| **Server time / end to end** | Time inside `/search`, versus time from sending the request to having the parsed response. |
| **Search session** | One `search_submitted` event and everything until the next one. |
| **Search click-through** | Share of search sessions with results in which the shopper opens at least one result. The experiment's primary metric. |
| **Layout variant** | A or B, assigned by a PostHog feature flag; `fallback` when the flag couldn't load. |
| **Directional result** | An experiment result from fewer searches than the plan needs. Reported, but not treated as proof (D-13). |
