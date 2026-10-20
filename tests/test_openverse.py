"""Collecting candidate query photos from Openverse (D-26). No network: the HTTP opener is faked."""
import io
import json
from urllib.parse import parse_qs, urlparse

from PIL import Image

from vsearch.openverse import contact_sheet, search


class FakeOpener:
    def __init__(self, results):
        self.results = results
        self.urls = []

    def __call__(self, request, timeout=None):
        self.urls.append(request.full_url)
        return io.BytesIO(json.dumps({"results": self.results}).encode())


def result(id_, license="by", mature=False):
    return {"id": id_, "license": license, "license_version": "2.0", "mature": mature,
            "url": f"https://img.example/{id_}.jpg", "title": id_, "creator": "c", "creator_url": "",
            "foreign_landing_url": f"https://example.org/{id_}", "license_url": "", "source": "flickr"}


def test_search_asks_only_for_allowed_licences_and_photographs():
    opener = FakeOpener([])
    search("checked shirt", page=2, opener=opener)
    query = parse_qs(urlparse(opener.urls[0]).query)
    assert query["q"] == ["checked shirt"] and query["page"] == ["2"]
    assert set(query["license"][0].split(",")) == {"cc0", "pdm", "by", "by-sa"}
    assert query["category"] == ["photograph"] and query["mature"] == ["false"]


def test_search_drops_any_result_with_a_disallowed_licence_or_marked_mature():
    """The API filter should already do this; the check stops a filter change upstream from
    letting an NC, ND or mature result into the candidates."""
    opener = FakeOpener([result("a"), result("b", "by-nc"), result("c", "by-nd"), result("d", mature=True),
                         result("e", "cc0")])
    assert [r["id"] for r in search("shirt", opener=opener)] == ["a", "e"]


def test_contact_sheet_lays_out_numbered_thumbnails(tmp_path):
    paths = []
    for n in range(7):
        p = tmp_path / f"{n}.jpg"
        Image.new("RGB", (800, 600), (n * 30, 80, 120)).save(p)
        paths.append(p)
    out = tmp_path / "sheet.jpg"
    contact_sheet(paths, out, cols=4, thumb=200)
    assert Image.open(out).size == (4 * 200, 2 * (200 + 24))


def test_given_one_search_times_out_twice_when_collecting_then_that_term_is_skipped_and_the_rest_run(tmp_path, capsys):
    """Uncached Openverse queries can take close to a minute. A search that times out is retried
    once; if it fails again, collection reports it and moves on to the next term."""
    from vsearch.openverse import collect

    terms = tmp_path / "terms.csv"
    terms.write_text("group,term,pages\nShirts,slow term,1\nJeans,jeans,1\n")
    calls = []

    def opener(request, timeout=None):
        calls.append(request.full_url)
        if "slow+term" in request.full_url:
            raise TimeoutError("The read operation timed out")
        if "api.openverse.org" in request.full_url:
            return io.BytesIO(json.dumps({"results": [result("j1")]}).encode())
        buf = io.BytesIO()
        Image.new("RGB", (50, 50)).save(buf, format="JPEG")
        return io.BytesIO(buf.getvalue())

    new = collect(terms, tmp_path / "cands", opener=opener, pause=0)
    assert new == 1 and (tmp_path / "cands" / "j1.jpg").exists()
    assert sum("slow+term" in u for u in calls) == 2
    assert "Shirts: 'slow term' page 1 failed twice" in capsys.readouterr().err


def test_given_a_run_that_saved_nothing_when_collecting_again_then_the_index_has_one_header(tmp_path):
    from vsearch.openverse import collect

    terms = tmp_path / "terms.csv"
    terms.write_text("group,term,pages\nShirts,slow term,1\n")

    def opener(request, timeout=None):
        raise TimeoutError("timed out")

    collect(terms, tmp_path / "cands", opener=opener, pause=0)
    collect(terms, tmp_path / "cands", opener=opener, pause=0)
    lines = (tmp_path / "cands" / "candidates.csv").read_text().splitlines()
    assert lines.count(lines[0]) == 1 and lines[0].startswith("source_id,")
