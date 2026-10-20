#!/usr/bin/env python3
"""Generate the README Results table (CLAUDE.md rule 4: no metric typed by hand).

Reads:  eval/results/<YYYY-MM-DD>.json        retrieval metrics, no-match rates, model choice (make eval)
        eval/results/bench-<YYYY-MM-DD>.json  latency (make bench)
        docs/usability.md                     raw session table (rows added only after real sessions)
        docs/ab-test.md                       experiment export (filled only after it runs)
        docs/uat/test-cases.csv               UAT status per case
Writes: the block between <!-- results:start --> and <!-- results:end --> in README.md

Usage:  python3 scripts/results.py          # rewrite README.md
        python3 scripts/results.py --check  # fail if README.md is stale
"""
import csv
import json
import math
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
START, END = "<!-- results:start -->", "<!-- results:end -->"
SYSTEMS = (("random", "Random"), ("openclip", "OpenCLIP ViT-B-32"), ("fashionclip", "Marqo-FashionCLIP"))

# Pre-registered experiment inputs; keep in step with docs/ab-test-plan.md §5.
AB_BASELINE_CTR = 0.40
AB_MIN_EFFECT = 0.10
Z_ALPHA, Z_POWER = 1.959964, 0.841621  # two-sided 0.05, power 0.80


def latest(pattern):
    files = sorted(RESULTS.glob(pattern)) if RESULTS.exists() else []
    if not files:
        return None, None
    return json.loads(files[-1].read_text()), files[-1].relative_to(ROOT)


def catalogue_row():
    manifest = ROOT / "eval" / "catalogue-manifest.csv"
    if not manifest.exists():
        return ("Catalogue searched", "Not built yet (M1)", "`eval/catalogue-manifest.csv`")
    with open(manifest, newline="") as f:
        rows = list(csv.DictReader(f))
    types = {r["article_type"] for r in rows}
    return ("Catalogue searched", f"{len(rows):,} products across {len(types)} article types",
            "`eval/catalogue-manifest.csv`")


def eval_rows():
    data, src = latest("[0-9][0-9][0-9][0-9]-*.json")
    if not data:
        return [
            catalogue_row(),
            ("Top-10 match rate (Recall@10), test photos",
             "Not run yet: no `eval/results/<date>.json` (M2)", "`eval/results/`"),
            ("Precision@10 and MRR, test photos", "Not run yet (M2)", "`eval/results/`"),
            ("No close match (similarity floor)", "Not run yet (M2–M3)", "`eval/results/`"),
            ("Model chosen by the D-08 rule", "Not chosen yet (M3)", "`eval/results/`"),
        ]
    src_md = f"`{src}`"
    cat, q = data["catalogue"], data["queries"]
    rows = [
        ("Catalogue searched", f"{cat['products']:,} products across {cat['article_types']} article types", src_md),
        ("Labelled query photos (openly licensed web photos, D-26)",
         f"{q.get('dev', 0)} dev" + (f", {q['test']} test" if "test" in q else ", test not read yet"), src_md),
    ]
    by_key = {(r["system"], r["split"], r["rule"]): r for r in data["rows"]}

    def cell(metric, rule="strict"):
        parts = []
        for key, label in SYSTEMS:
            r = by_key.get((key, "test", rule))
            if not r:
                continue
            value = f"{label} {r[metric]:.2f}"
            ci = r.get(f"{metric}_ci")
            if ci:
                value += f" ({ci[0]:.2f}–{ci[1]:.2f})"
            parts.append(value)
        return " · ".join(parts) or "Test split not read yet (dev-only run; target set first, PRD Q3)"

    rows.append(("Top-10 match rate (Recall@10), test photos, same type and colour", cell("recall_at_10"), src_md))
    dev = []
    for key, label in SYSTEMS:
        r = by_key.get((key, "dev", "strict"))
        if r:
            dev.append(f"{label} {r['recall_at_10']:.2f} ({r['recall_at_10_ci'][0]:.2f}–{r['recall_at_10_ci'][1]:.2f})")
    if dev:
        rows.append((f"Top-10 match rate on the {q.get('dev', 0)} dev photos (the tuning split, not the result)",
                     " · ".join(dev), src_md))
    rows.append(("Top-10 match rate, same type only", cell("recall_at_10", "type_only"), src_md))
    rows.append(("Precision@10, test photos", cell("precision_at_10"), src_md))
    rows.append(("MRR, test photos", cell("mrr"), src_md))
    nm = data.get("no_match")
    if nm:
        rows.append((
            "No close match (similarity floor)",
            f"{nm['in_catalogue_answered']:.0%} of {nm['n_in']} in-catalogue photos answered; "
            f"{nm['out_of_catalogue_rejected']:.0%} of {nm['n_out']} other photos told 'no close match'",
            src_md,
        ))
    choice = data.get("model_choice")
    if choice:
        rows.append(("Model chosen by the D-08 rule", f"{choice['chosen']}: {choice['reason']}", src_md))
    return rows


def bench_rows(chosen):
    data, src = latest("bench-*.json")
    if not data:
        return [("Latency p50 / p95", "Not run yet: no `eval/results/bench-<date>.json` (M3)", "`eval/results/`")]
    rows = []
    for m in data["models"]:
        if chosen and m["model"] != chosen:
            continue
        rows.append((
            f"Latency p50 / p95, {m['model']} ({data['requests']} requests, {data['cpu']})",
            f"server {m['p50_ms']['server']:.0f} / {m['p95_ms']['server']:.0f} ms · "
            f"end to end {m['p50_ms']['end_to_end']:.0f} / {m['p95_ms']['end_to_end']:.0f} ms",
            f"`{src}`",
        ))
    return rows


def md_table(path, heading):
    """Rows of the first table under `heading` as dicts; [] if none."""
    text = (ROOT / path).read_text()
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []
    split = lambda ln: [c.strip() for c in ln.strip("|").split("|")]
    header = split(lines[0])
    return [dict(zip(header, split(ln))) for ln in lines[2:] if any(split(ln))]


def usability_rows():
    rows = md_table("docs/usability.md", "Raw data")
    src = "`docs/usability.md`"
    if not rows:
        return [("Usability test", "Not run yet: no sessions in `docs/usability.md` (M5)", src)]
    shoppers = sorted({r["Code"] for r in rows})
    done = [r for r in rows if r["Success"].lower().startswith("y")]
    times = []
    for r in done:
        mm, ss = r["Time (mm:ss)"].split(":")
        times.append(int(mm) * 60 + int(ss))
    median = f"{int(statistics.median(times)) // 60}:{int(statistics.median(times)) % 60:02d}" if times else "—"
    return [
        ("Usability sessions", f"{len(shoppers)} shoppers, {len(rows)} task attempts", src),
        ("Tasks completed without help", f"{len(done)} of {len(rows)}; median time {median} (mm:ss)", src),
    ]


def required_per_arm(p1=AB_BASELINE_CTR, delta=AB_MIN_EFFECT):
    p2 = p1 + delta
    pbar = (p1 + p2) / 2
    n = (Z_ALPHA * math.sqrt(2 * pbar * (1 - pbar)) + Z_POWER * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(n / delta**2)


def ab_rows():
    rows = {r["Variant"]: r for r in md_table("docs/ab-test.md", "Export")}
    src = "`docs/ab-test.md`"
    need = required_per_arm()
    if "A" not in rows or "B" not in rows:
        return [("Layout experiment click-through (A vs B)",
                 f"Not run yet (M5). Needs {need} searches with results per layout to detect a "
                 f"{AB_MIN_EFFECT * 100:.0f}-point change in click-through", src)]
    n = {k: int(rows[k]["Searches with results"]) for k in "AB"}
    c = {k: int(rows[k]["Searches with a click"]) for k in "AB"}
    ctr = {k: c[k] / n[k] for k in "AB"}
    pool = (c["A"] + c["B"]) / (n["A"] + n["B"])
    se = math.sqrt(pool * (1 - pool) * (1 / n["A"] + 1 / n["B"]))
    p = math.erfc(abs(ctr["B"] - ctr["A"]) / se / math.sqrt(2)) if se else 1.0
    powered = min(n.values()) >= need
    verdict = "powered" if powered else f"directional only: fewer than the {need} per layout the plan needs"
    return [(
        "Layout experiment click-through (A vs B)",
        f"A {ctr['A']:.0%} of {n['A']} · B {ctr['B']:.0%} of {n['B']} · p = {p:.2f} ({verdict})",
        src,
    )]


def uat_rows():
    with open(ROOT / "docs" / "uat" / "test-cases.csv", newline="") as f:
        cases = list(csv.DictReader(f))
    executed = [c for c in cases if c["status"] != "Not run"]
    passed = sum(1 for c in executed if c["status"] == "Pass")
    value = f"{len(executed)} of {len(cases)} executed, {passed} passed" if executed else f"Not run yet: 0 of {len(cases)} executed"
    return [("UAT cases executed / passed", value, "`docs/uat/test-cases.csv`")]


def build():
    data, _ = latest("[0-9][0-9][0-9][0-9]-*.json")
    chosen = (data or {}).get("model_choice", {}).get("chosen")
    rows = eval_rows() + bench_rows(chosen) + usability_rows() + ab_rows() + uat_rows()
    out = [
        START,
        "<!-- Generated by scripts/results.py from eval/results/, docs/usability.md, docs/ab-test.md "
        "and docs/uat/test-cases.csv. Run `make docs`; don't edit. -->",
        "",
        "| Metric | Value | Produced by |",
        "| --- | --- | --- |",
    ]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    out.append(END)
    return "\n".join(out)


def main():
    readme = ROOT / "README.md"
    text = readme.read_text()
    if START not in text or END not in text:
        sys.exit("README.md has no results markers")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: build(), text, flags=re.S)
    if "--check" in sys.argv:
        if new != text:
            print("README Results are stale; run `make docs` and commit README.md")
            sys.exit(1)
        return
    readme.write_text(new)
    print("Wrote README.md Results")


if __name__ == "__main__":
    main()
