#!/usr/bin/env python3
"""Build docs/traceability.md and check that every ID links up.

Reads:  docs/PRD.md (FR-/NFR-), docs/user-stories.md (US-),
        docs/uat/test-cases.csv (TC-), docs/risk-log.md (R-),
        test names that cite a TC ID:
          tests/**/test_*.py          def test_tc_srch_01_...()   -> TC-SRCH-01
          web/src/**/*.test.ts(x)     it("TC-SRCH-01: ...")
          e2e/**/*.spec.ts            test("TC-SRCH-01: ...")
        US- tags in comments under vsearch/, eval/ and web/src/ (where a story is built)
Writes: docs/traceability.md
Exits 1 if a link is broken or a Must requirement has no story or test.

Usage:  python3 scripts/docs_check.py          # write + check
        python3 scripts/docs_check.py --check  # check only, write nothing
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REQ_RE = re.compile(r"\b(?:FR|NFR)-\d{2}\b")
TC_RE = re.compile(r"\bTC-[A-Z]+-\d{2}\b")
US_RE = re.compile(r"\bUS-\d{2}\b")
TS_TEST_RE = re.compile(r"""\b(?:it|test)(?:\.\w+)?\(\s*(["'`])(.+?)\1""")
PY_TEST_RE = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(")
PY_TC_RE = re.compile(r"tc_([a-z]+)_(\d{2})")


def read_requirements():
    reqs = {}
    for line in (DOCS / "PRD.md").read_text().splitlines():
        m = re.match(r"\|\s*((?:FR|NFR)-\d{2})\s*\|\s*(.+?)\s*\|\s*(Must|Should|Could|Won't)\s*\|", line)
        if m:
            reqs[m.group(1)] = {"text": m.group(2), "priority": m.group(3)}
    return reqs


def read_stories():
    stories, current = {}, None
    for line in (DOCS / "user-stories.md").read_text().splitlines():
        m = re.match(r"###\s+(US-\d{2})\s+(.+)", line)
        if m:
            current = m.group(1)
            stories[current] = {"title": m.group(2).strip(), "reqs": [], "milestone": ""}
            continue
        if current and not stories[current]["reqs"] and REQ_RE.search(line):
            stories[current]["reqs"] = REQ_RE.findall(line)
            milestone = re.search(r"\bM\d\b", line)
            stories[current]["milestone"] = milestone.group(0) if milestone else ""
    return stories


def read_cases():
    with open(DOCS / "uat" / "test-cases.csv", newline="") as f:
        return list(csv.DictReader(f))


def expand_tc_ranges(text):
    """'TC-NFR-01 – TC-NFR-04' -> the four IDs; plain IDs pass through."""
    ids = []
    for a, b in re.findall(r"(TC-[A-Z]+-\d{2})\s*[–-]\s*(TC-[A-Z]+-\d{2})", text):
        prefix, start, end = a[:-2], int(a[-2:]), int(b[-2:])
        ids += [f"{prefix}{n:02d}" for n in range(start, end + 1)]
    return sorted(set(ids) | set(TC_RE.findall(text)))


def read_risks():
    risks = {}
    for line in (DOCS / "risk-log.md").read_text().splitlines():
        m = re.match(r"\|\s*(R-\d{2})\s*\|\s*(.+?)\s*\|", line)
        if m:
            risks[m.group(1)] = {"text": m.group(2), "tcs": expand_tc_ranges(line)}
    return risks


def _files(folder, patterns):
    base = ROOT / folder
    if not base.exists():
        return []
    found = set()
    for pattern in patterns:
        found |= {p for p in base.rglob(pattern) if "node_modules" not in p.parts}
    return sorted(found)


def read_automated_tests():
    """Every test whose name cites a TC ID: [(tc, 'path:line', name)]."""
    found = []
    for path in _files("tests", ["test_*.py"]):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            m = PY_TEST_RE.match(line)
            if m:
                for module, num in PY_TC_RE.findall(m.group(1)):
                    found.append((f"TC-{module.upper()}-{num}", f"{path.relative_to(ROOT)}:{n}", m.group(1)))
    for folder, patterns in (("web/src", ["*.test.ts", "*.test.tsx"]), ("e2e", ["*.spec.ts"])):
        for path in _files(folder, patterns):
            for n, line in enumerate(path.read_text().splitlines(), 1):
                m = TS_TEST_RE.search(line)
                if m:
                    for tc in TC_RE.findall(m.group(2)):
                        found.append((tc, f"{path.relative_to(ROOT)}:{n}", m.group(2)))
    return found


def read_code_tags():
    """Where each story is built: US ID -> ['path:line', ...], first tag per file."""
    tags = defaultdict(list)
    sources = _files("vsearch", ["*.py"]) + _files("eval", ["*.py"])
    sources += [p for p in _files("web/src", ["*.ts", "*.tsx"]) if ".test." not in p.name]
    for path in sources:
        seen = set()
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if "#" not in line and "//" not in line and "*" not in line:
                continue
            for us in US_RE.findall(line):
                if us not in seen:
                    seen.add(us)
                    tags[us].append(f"{path.relative_to(ROOT)}:{n}")
    return tags


def main():
    check_only = "--check" in sys.argv
    reqs, stories, cases, risks = read_requirements(), read_stories(), read_cases(), read_risks()
    automated, code_tags = read_automated_tests(), read_code_tags()
    case_ids = {c["id"] for c in cases}
    case_story = {c["id"]: c["story"] for c in cases}
    errors = []

    duplicates = [i for i, n in Counter(c["id"] for c in cases).items() if n > 1]
    for d in duplicates:
        errors.append(f"test case {d} appears more than once in the UAT sheet")

    tc_to_tests = defaultdict(list)
    for tc, where, name in automated:
        if tc not in case_ids:
            errors.append(f"{where} cites unknown test case {tc}")
        tc_to_tests[tc].append((where, name))
    for us in code_tags:
        if us not in stories:
            errors.append(f"{code_tags[us][0]} tags unknown story {us}")

    req_to_stories = defaultdict(list)
    for us, s in stories.items():
        if not s["reqs"]:
            errors.append(f"{us} names no FR/NFR")
        for r in s["reqs"]:
            if r not in reqs:
                errors.append(f"{us} names unknown requirement {r}")
            req_to_stories[r].append(us)

    story_to_cases, req_to_cases = defaultdict(list), defaultdict(list)
    for c in cases:
        ref = c["story"]
        if ref in stories:
            story_to_cases[ref].append(c["id"])
            for r in stories[ref]["reqs"]:
                req_to_cases[r].append(c["id"])
        elif ref in reqs:
            req_to_cases[ref].append(c["id"])
        else:
            errors.append(f"{c['id']} names unknown story/requirement {ref}")

    tc_to_risks = defaultdict(list)
    for rid, r in risks.items():
        for tc in r["tcs"]:
            if tc not in case_ids:
                errors.append(f"{rid} cites unknown test case {tc}")
            tc_to_risks[tc].append(rid)

    for us in stories:
        if not story_to_cases[us]:
            errors.append(f"{us} has no UAT case")
    for rid, r in reqs.items():
        if r["priority"] == "Must" and not req_to_stories[rid] and not req_to_cases[rid]:
            errors.append(f"Must requirement {rid} has no story and no test case")

    if errors:
        print("Traceability errors:", *errors, sep="\n  ")
    if check_only:
        sys.exit(1 if errors else 0)

    out = [
        "# Traceability matrix",
        "",
        "Generated by `scripts/docs_check.py` from the PRD, user stories, UAT sheet and risk log. "
        "Do not edit by hand; run `make docs`.",
        "",
        "## Requirement → story → test → risk",
        "",
        "Automated: how many of the row's UAT cases have at least one automated test citing them.",
        "",
        "| Req | Priority | Requirement | Stories | UAT cases | Automated | Risks |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rid, r in reqs.items():
        tcs = sorted(set(req_to_cases[rid]))
        rks = sorted({rk for tc in tcs for rk in tc_to_risks[tc]})
        auto = sum(1 for tc in tcs if tc_to_tests[tc])
        short = r["text"] if len(r["text"]) <= 70 else r["text"][:67].rstrip() + "…"
        out.append(
            f"| {rid} | {r['priority']} | {short} | {', '.join(req_to_stories[rid]) or '—'} "
            f"| {', '.join(tcs) or '—'} | {auto} of {len(tcs)} | {', '.join(rks) or '—'} |"
        )

    out += [
        "",
        "## Story → code",
        "",
        "Found from `US-nn` tags in comments under `vsearch/`, `eval/` and `web/src/`.",
        "",
        "| Story | Title | Milestone | Built in |",
        "| --- | --- | --- | --- |",
    ]
    for us, s in stories.items():
        where = "<br>".join(f"`{w}`" for w in code_tags.get(us, [])) or "—"
        out.append(f"| {us} | {s['title']} | {s['milestone']} | {where} |")

    out += [
        "",
        "## UAT case → automated test",
        "",
        "Found from TC IDs in test names under `tests/` (pytest), `web/src/` (Vitest) and `e2e/` (Playwright). "
        "An automated pass is not a UAT pass: UAT status in the next section comes only from the UAT sheet.",
        "",
        "| UAT case | Story | Test | Where |",
        "| --- | --- | --- | --- |",
    ]
    for c in cases:
        for where, name in tc_to_tests.get(c["id"], []):
            label = name.replace("|", "\\|")
            out.append(f"| {c['id']} | {case_story[c['id']]} | {label} | `{where}` |")
    not_automated = [c["id"] for c in cases if not tc_to_tests[c["id"]]]
    out += ["", f"UAT cases with no automated test yet ({len(not_automated)}): {', '.join(not_automated) or 'none'}."]

    status = Counter(c["status"] for c in cases)
    by_module = defaultdict(Counter)
    for c in cases:
        by_module[c["module"]][c["status"]] += 1
    statuses = sorted(status)
    out += [
        "",
        "## UAT sheet status",
        "",
        "| Module | Cases | " + " | ".join(statuses) + " |",
        "| --- | --- | " + " | ".join("---" for _ in statuses) + " |",
    ]
    for mod, cnt in by_module.items():
        out.append(f"| {mod} | {sum(cnt.values())} | " + " | ".join(str(cnt[s]) for s in statuses) + " |")
    out.append(f"| **Total** | **{len(cases)}** | " + " | ".join(f"**{status[s]}**" for s in statuses) + " |")

    must = [r for r, v in reqs.items() if v["priority"] == "Must"]
    covered = [r for r in must if req_to_cases[r]]
    out += [
        "",
        "## Coverage",
        "",
        f"- Requirements: {len(reqs)} ({len(must)} Must); Must requirements with at least one UAT case: {len(covered)} of {len(must)}",
        f"- Stories: {len(stories)}; with at least one UAT case: {sum(1 for s in stories if story_to_cases[s])} of {len(stories)}",
        f"- Risks: {len(risks)}; risks with a proving test: {sum(1 for r in risks.values() if r['tcs'])}",
        f"- UAT cases with an automated test: {len(cases) - len(not_automated)} of {len(cases)}",
        f"- Link errors: {len(errors)}",
        "",
    ]
    (DOCS / "traceability.md").write_text("\n".join(out))
    print(f"Wrote docs/traceability.md ({len(reqs)} reqs, {len(stories)} stories, {len(cases)} cases, {len(risks)} risks)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
