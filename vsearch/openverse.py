"""Collect candidate query photos from Openverse for review (D-26).

Only CC0, public-domain-mark, CC BY and CC BY-SA photographs are requested, and the results are
checked again here. Anonymous access allows 20 requests a minute and 200 a day, so requests are
spaced 3.5 s apart. Candidates land in data/candidates/ (git-ignored) with their credits; the ones
chosen for the eval are recorded in eval/queries/selections.csv.

Usage:  uv run python -m vsearch.openverse collect eval/openverse-terms.csv
        uv run python -m vsearch.openverse sheets
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw

from vsearch.queries import ALLOWED_LICENSES, CANDIDATES

API = "https://api.openverse.org/v1/images/"
USER_AGENT = "vsearch-eval/0.1 (portfolio project; https://github.com/ishika-pandey-010/Visual-search-for-fashion)"
PAGE_SIZE = 20
PAUSE = 3.5
SEARCH_TIMEOUT = 120  # an uncached query took 56 s on 2026-10-21
CANDIDATE_COLUMNS = ["source_id", "group", "term", "title", "creator", "creator_url", "landing_url",
                     "license", "license_version", "license_url", "provider", "image_url", "width", "height"]


def search(term, page=1, opener=urlopen):
    """One page of results, keeping only allowed licences and nothing marked mature."""
    params = {"q": term, "page": page, "page_size": PAGE_SIZE, "license": ",".join(sorted(ALLOWED_LICENSES)),
              "category": "photograph", "mature": "false"}
    request = Request(f"{API}?{urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with opener(request, timeout=SEARCH_TIMEOUT) as response:
        results = json.load(response)["results"]
    return [r for r in results if r["license"] in ALLOWED_LICENSES and not r.get("mature")]


def collect(terms_csv, out=CANDIDATES, opener=urlopen, pause=PAUSE):
    """Search each (group, term, pages) row and download every new candidate image."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    index = out / "candidates.csv"
    seen = set()
    if index.exists():
        with open(index, newline="") as f:
            seen = {r["source_id"] for r in csv.DictReader(f)}
    new = 0
    needs_header = not index.exists() or index.stat().st_size == 0
    with open(terms_csv, newline="") as f, open(index, "a", newline="") as idx:
        writer = csv.DictWriter(idx, fieldnames=CANDIDATE_COLUMNS)
        if needs_header:
            writer.writeheader()
        for row in csv.DictReader(f):
            for page in range(1, int(row["pages"]) + 1):
                results = None
                for _ in range(2):
                    try:
                        results = search(row["term"], page, opener)
                        break
                    except OSError:  # TimeoutError and URLError are both OSError
                        time.sleep(pause)
                time.sleep(pause)
                if results is None:
                    print(f"{row['group']}: '{row['term']}' page {page} failed twice; skipped", file=sys.stderr)
                    continue
                for r in results:
                    if r["id"] in seen:
                        continue
                    try:
                        req = Request(r["url"], headers={"User-Agent": USER_AGENT})
                        with opener(req, timeout=30) as response:
                            (out / f"{r['id']}.jpg").write_bytes(response.read())
                    except OSError as e:
                        print(f"  skipped {r['id']}: {e}", file=sys.stderr)
                        continue
                    seen.add(r["id"])
                    new += 1
                    writer.writerow({
                        "source_id": r["id"], "group": row["group"], "term": row["term"],
                        "title": r.get("title") or "Untitled", "creator": r.get("creator") or "",
                        "creator_url": r.get("creator_url") or "", "landing_url": r["foreign_landing_url"],
                        "license": r["license"], "license_version": r.get("license_version") or "",
                        "license_url": r.get("license_url") or "", "provider": r.get("provider") or "",
                        "image_url": r["url"], "width": r.get("width") or "", "height": r.get("height") or "",
                    })
                print(f"{row['group']}: '{row['term']}' page {page}: {len(results)} results", flush=True)
    return new


def contact_sheet(paths, out, cols=5, thumb=220, labels=None):
    """A grid of numbered thumbnails, for reviewing candidates by eye."""
    rows = -(-len(paths) // cols)
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + 24)), "white")
    draw = ImageDraw.Draw(sheet)
    for n, path in enumerate(paths):
        x, y = (n % cols) * thumb, (n // cols) * (thumb + 24)
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((thumb - 6, thumb - 6))
                sheet.paste(img, (x + (thumb - img.width) // 2, y + (thumb - img.height) // 2))
        except OSError:
            draw.text((x + 10, y + thumb // 2), "unreadable", fill="red")
        draw.text((x + 4, y + thumb + 4), labels[n] if labels else str(n), fill="black")
    sheet.save(out, quality=85)


def sheets(out=CANDIDATES, per_sheet=20):
    """One contact sheet per group, 20 thumbnails each, labelled by candidate row number."""
    with open(Path(out) / "candidates.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    folder = Path(out) / "sheets"
    folder.mkdir(exist_ok=True)
    groups = {}
    for n, r in enumerate(rows):
        groups.setdefault(r["group"], []).append((n, r))
    for group, items in groups.items():
        for start in range(0, len(items), per_sheet):
            chunk = items[start:start + per_sheet]
            name = f"{group.replace(' ', '_')}-{start // per_sheet + 1}.jpg"
            contact_sheet([Path(out) / f"{r['source_id']}.jpg" for _, r in chunk], folder / name,
                          labels=[str(n) for n, _ in chunk])
    return folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("terms_csv")
    sub.add_parser("sheets")
    args = parser.parse_args(argv)
    if args.command == "collect":
        print(f"Downloaded {collect(args.terms_csv)} new candidates into {CANDIDATES}/")
    else:
        print(f"Wrote contact sheets to {sheets()}/")


if __name__ == "__main__":
    main()
