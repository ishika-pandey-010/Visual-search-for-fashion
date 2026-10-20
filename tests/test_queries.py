"""US-03 Labelled query photos. Each test name cites the UAT case it automates."""
import io

import pandas as pd
import pytest
from PIL import Image

from vsearch.queries import (
    ALLOWED_LICENSES,
    LABEL_COLUMNS,
    SOURCE_COLUMNS,
    assign_splits,
    attribution_text,
    build_queries,
    check,
    has_exif,
    prepare_image,
    write_vocabulary,
)

VOCAB_TYPES = {"in_catalogue": ["Shirts", "Jeans"], "out_of_catalogue": ["Sarees"]}


def photo_bytes(size=(1200, 900), exif=None, colour=(120, 60, 30)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, colour)
    if exif is not None:
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def gps_exif(orientation=None):
    exif = Image.Exif()
    exif[0x8825] = {2: (12.0, 58.0, 0.0)}  # GPSInfo: a latitude
    exif[0x010F] = "PhoneMaker"  # Make
    if orientation:
        exif[0x0112] = orientation
    return exif


@pytest.fixture
def vocab(tmp_path):
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame({
        "product_id": [1, 2, 3],
        "article_type": ["Shirts", "Jeans", "Shirts"],
        "base_colour": ["Blue", "Navy Blue", "White"],
    }).to_csv(manifest, index=False)
    out = tmp_path / "vocabulary.csv"
    write_vocabulary(manifest, ["Sarees"], out)
    return out


def labels_row(qid, kind="in_catalogue", type_="Shirts", colour="Blue", split="", source="openverse"):
    return {"query_id": qid, "kind": kind, "article_type": type_, "base_colour": colour,
            "split": split, "source": source, "notes": "worn"}


def source_row(qid, license="by"):
    return {"query_id": qid, "source": "openverse", "source_id": f"ov-{qid}", "title": f"Photo {qid}",
            "creator": "Someone", "creator_url": "https://example.org/someone",
            "landing_url": f"https://example.org/{qid}", "license": license, "license_version": "2.0",
            "license_url": "https://creativecommons.org/licenses/by/2.0/",
            "changes": "resized to 640 px; re-encoded as JPEG"}


def write_set(folder, labels, sources, photos=None, attribution=True):
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(labels, columns=LABEL_COLUMNS).to_csv(folder / "labels.csv", index=False)
    pd.DataFrame(sources, columns=SOURCE_COLUMNS).to_csv(folder / "sources.csv", index=False)
    for qid in photos if photos is not None else [r["query_id"] for r in labels]:
        (folder / f"{qid}.jpg").write_bytes(prepare_image(photo_bytes()))
    if attribution:
        (folder / "ATTRIBUTION.md").write_text(attribution_text(pd.DataFrame(sources, columns=SOURCE_COLUMNS)))


@pytest.fixture
def good_set(tmp_path):
    folder = tmp_path / "queries"
    labels = [labels_row("q001"), labels_row("q002", type_="Jeans", colour="Navy Blue"),
              labels_row("q003", kind="out_of_catalogue", type_="Sarees", colour=""),
              labels_row("q004", kind="not_fashion", type_="", colour="")]
    write_set(folder, labels, [source_row(r["query_id"]) for r in labels])
    return folder


def test_vocabulary_lists_catalogue_types_reserved_types_and_catalogue_colours(vocab):
    v = pd.read_csv(vocab)
    assert set(v[v.field == "article_type"].query("kind == 'in_catalogue'").value) == {"Shirts", "Jeans"}
    assert set(v[v.field == "article_type"].query("kind == 'out_of_catalogue'").value) == {"Sarees"}
    assert set(v[v.field == "base_colour"].value) == {"Blue", "Navy Blue", "White"}


def test_tc_eval_01_given_a_complete_set_when_checked_then_it_passes(good_set, vocab):
    result = check(good_set, vocab)
    assert result.errors == []


@pytest.mark.parametrize("break_it, expected", [
    (lambda f: (f / "q002.jpg").unlink(), "q002: labelled but no photo"),
    (lambda f: (f / "q099.jpg").write_bytes(prepare_image(photo_bytes())), "q099.jpg: photo has no label row"),
    (lambda f: _edit_label(f, "q001", base_colour="Sky"), "q001: colour 'Sky' isn't in the vocabulary"),
    (lambda f: _edit_label(f, "q001", article_type="Sarees"), "q001: 'Sarees' isn't a catalogue type"),
    (lambda f: _edit_label(f, "q003", article_type="Shirts"), "q003: 'Shirts' isn't a reserved type"),
    (lambda f: _edit_label(f, "q004", article_type="Shirts"), "q004: not_fashion photos have no type or colour"),
    (lambda f: _edit_label(f, "q001", kind="clothes"), "q001: kind 'clothes' isn't one of"),
    (lambda f: _edit_label(f, "q002", query_id="q001"), "q001: appears more than once"),
])
def test_tc_eval_01_given_a_broken_set_when_checked_then_the_error_names_the_photo(good_set, vocab, break_it, expected):
    """Given one thing wrong with the set, when checked, then an error names the photo and the problem."""
    break_it(good_set)
    errors = check(good_set, vocab).errors
    assert any(expected in e for e in errors), errors


def _edit_label(folder, qid, **changes):
    labels = pd.read_csv(folder / "labels.csv", dtype=str, keep_default_na=False)
    for col, value in changes.items():
        labels.loc[labels.query_id == qid, col] = value
    labels.to_csv(folder / "labels.csv", index=False)


def test_tc_eval_02_given_a_phone_photo_with_gps_when_prepared_then_no_exif_survives(tmp_path):
    """Given a photo with GPS and camera EXIF, when prepared for the set, then the stored file has
    no EXIF at all, and the check would have caught the original."""
    original = tmp_path / "original.jpg"
    original.write_bytes(photo_bytes(exif=gps_exif()))
    assert has_exif(original)
    prepared = tmp_path / "prepared.jpg"
    prepared.write_bytes(prepare_image(original.read_bytes()))
    assert not has_exif(prepared)


def test_tc_eval_02_given_a_photo_with_exif_in_the_set_when_checked_then_it_fails(good_set, vocab):
    (good_set / "q001.jpg").write_bytes(photo_bytes(exif=gps_exif()))
    assert any("q001.jpg: has EXIF metadata" in e for e in check(good_set, vocab).errors)


def test_prepared_photo_is_640_on_its_long_side_cropped_and_upright():
    """D-27: cropped by fractions of the frame, then 640 px on the long side; EXIF rotation applied
    before it's dropped, so a portrait phone photo stays portrait."""
    out = Image.open(io.BytesIO(prepare_image(photo_bytes((2000, 1000)))))
    assert out.size == (640, 320)
    cropped = Image.open(io.BytesIO(prepare_image(photo_bytes((2000, 1000)), crop=(0.5, 0.0, 1.0, 1.0))))
    assert cropped.size == (640, 640)
    rotated = Image.open(io.BytesIO(prepare_image(photo_bytes((1200, 900), exif=gps_exif(orientation=6)))))
    assert rotated.size == (480, 640)
    small = Image.open(io.BytesIO(prepare_image(photo_bytes((400, 300)))))
    assert small.size == (400, 300)  # never upscaled


def test_tc_eval_03_given_new_photos_when_split_then_each_kind_is_about_30_percent_dev():
    labels = pd.DataFrame([labels_row(f"q{i:03d}") for i in range(1, 41)] +
                          [labels_row(f"n{i:03d}", kind="not_fashion", type_="", colour="") for i in range(1, 11)])
    split = assign_splits(labels, seed=2026)
    assert set(split["split"]) == {"dev", "test"}
    assert (split.query("kind == 'in_catalogue'").split == "dev").sum() == 12
    assert (split.query("kind == 'not_fashion'").split == "dev").sum() == 3
    assert split.equals(assign_splits(labels, seed=2026))  # same seed, same answer


def test_tc_eval_03_given_an_assigned_split_when_photos_are_added_then_old_ones_keep_theirs():
    """Given a split already assigned, when 5 photos are added and the split step runs again, then
    every old photo keeps its split and only the 5 new ones are assigned."""
    first = assign_splits(pd.DataFrame([labels_row(f"q{i:03d}") for i in range(1, 21)]), seed=2026)
    grown = pd.concat([first, pd.DataFrame([labels_row(f"q{i:03d}") for i in range(21, 26)])], ignore_index=True)
    second = assign_splits(grown, seed=2026)
    pd.testing.assert_series_equal(second["split"][:20], first["split"], check_names=False)
    assert set(second["split"][20:]) <= {"dev", "test"}


def test_tc_eval_15_given_a_set_when_checked_then_counts_print_and_thin_types_warn(good_set, vocab):
    """Given a set where Jeans has one test photo, when checked, then counts by kind and type are
    reported and there's a warning that Jeans has fewer than 4 test photos."""
    labels = assign_splits(pd.read_csv(good_set / "labels.csv", dtype=str, keep_default_na=False), seed=2026)
    labels.to_csv(good_set / "labels.csv", index=False)
    result = check(good_set, vocab)
    assert result.counts["kind"] == {"in_catalogue": 2, "out_of_catalogue": 1, "not_fashion": 1}
    assert any("Jeans has 1" in w or "Jeans has 0" in w for w in result.warnings)


def test_tc_eval_16_given_a_photo_under_a_non_commercial_licence_when_checked_then_it_fails(good_set, vocab):
    """Given one photo's licence changed to by-nc, when checked, then the check fails naming it."""
    sources = pd.read_csv(good_set / "sources.csv", dtype=str, keep_default_na=False)
    sources.loc[sources.query_id == "q002", "license"] = "by-nc"
    sources.to_csv(good_set / "sources.csv", index=False)
    (good_set / "ATTRIBUTION.md").write_text(attribution_text(sources))
    assert any("q002: licence 'by-nc' isn't allowed" in e for e in check(good_set, vocab).errors)
    assert ALLOWED_LICENSES == {"cc0", "pdm", "by", "by-sa"}


def test_tc_eval_16_given_a_web_photo_with_no_credit_when_checked_then_it_fails(good_set, vocab):
    sources = pd.read_csv(good_set / "sources.csv", dtype=str, keep_default_na=False)
    sources.loc[sources.query_id == "q001", "creator"] = ""
    sources[sources.query_id != "q002"].to_csv(good_set / "sources.csv", index=False)
    errors = check(good_set, vocab).errors
    assert any("q001: no creator" in e for e in errors), errors
    assert any("q002: web photo with no row in sources.csv" in e for e in errors), errors


def test_tc_eval_16_given_a_stale_attribution_file_when_checked_then_it_fails(good_set, vocab):
    (good_set / "ATTRIBUTION.md").write_text("# Attribution\n")
    assert any("ATTRIBUTION.md is out of date" in e for e in check(good_set, vocab).errors)


def test_attribution_credits_title_creator_source_licence_and_changes():
    text = attribution_text(pd.DataFrame([source_row("q001")], columns=SOURCE_COLUMNS))
    for part in ("q001", "Photo q001", "Someone", "https://example.org/q001", "CC BY 2.0", "resized to 640 px"):
        assert part in text


def test_given_selections_when_queries_are_built_then_photos_labels_and_credits_are_written(tmp_path, vocab):
    """Given candidates and a labelling record, when the set is built, then each selection becomes a
    prepared photo, a label row and a credit; a rebuild keeps splits already assigned."""
    cand_dir = tmp_path / "candidates"
    cand_dir.mkdir()
    candidates = []
    for n in range(3):
        cid = f"ov-{n}"
        (cand_dir / f"{cid}.jpg").write_bytes(photo_bytes((1600, 1200), exif=gps_exif()))
        candidates.append({**source_row(f"x{n}"), "source_id": cid, "group": "Shirts", "term": "shirt"})
    pd.DataFrame(candidates).to_csv(cand_dir / "candidates.csv", index=False)
    selections = tmp_path / "selections.csv"
    pd.DataFrame([
        {"query_id": "q001", "candidate_id": "ov-0", "kind": "in_catalogue", "article_type": "Shirts",
         "base_colour": "Blue", "crop": "", "notes": "hanger"},
        {"query_id": "q002", "candidate_id": "ov-1", "kind": "in_catalogue", "article_type": "Jeans",
         "base_colour": "Navy Blue", "crop": "0.25 0 0.75 1", "notes": "worn; cropped below the face"},
        {"query_id": "q003", "candidate_id": "ov-2", "kind": "not_fashion", "article_type": "",
         "base_colour": "", "crop": "", "notes": "mug"},
    ]).to_csv(selections, index=False)
    out = tmp_path / "queries"
    build_queries(selections, cand_dir, out)

    assert sorted(p.name for p in out.glob("q*.jpg")) == ["q001.jpg", "q002.jpg", "q003.jpg"]
    assert not has_exif(out / "q001.jpg")
    assert Image.open(out / "q002.jpg").size == (427, 640)  # middle half of 1600×1200 is 800×1200; 640 long side
    sources = pd.read_csv(out / "sources.csv", dtype=str, keep_default_na=False)
    assert "cropped" in sources.set_index("query_id").loc["q002", "changes"]
    assert check(out, vocab).errors == []

    labels = assign_splits(pd.read_csv(out / "labels.csv", dtype=str, keep_default_na=False), seed=2026)
    labels.to_csv(out / "labels.csv", index=False)
    build_queries(selections, cand_dir, out)
    rebuilt = pd.read_csv(out / "labels.csv", dtype=str, keep_default_na=False)
    assert rebuilt["split"].tolist() == labels["split"].tolist()


def test_tc_eval_16_given_a_cc0_photo_with_no_named_creator_when_checked_then_it_passes(good_set, vocab):
    """CC0 and the public-domain mark don't require credit, and rawpixel's CC0 photos name no
    creator. Only BY and BY-SA photos must name one; the credit line says the creator isn't named."""
    sources = pd.read_csv(good_set / "sources.csv", dtype=str, keep_default_na=False)
    sources.loc[sources.query_id == "q001", ["creator", "license"]] = ["", "cc0"]
    sources.to_csv(good_set / "sources.csv", index=False)
    (good_set / "ATTRIBUTION.md").write_text(attribution_text(sources))
    assert check(good_set, vocab).errors == []
    assert "creator not named" in attribution_text(sources)


def test_tc_eval_03_given_thin_types_when_split_then_each_type_keeps_at_least_4_test_photos():
    """Splits are stratified by type within in-catalogue photos, and a type never gives up a test
    photo below 4 to make its dev share: 5 photos split 1/4, 8 split 2/6, 4 split 0/4."""
    rows = ([labels_row(f"k{i}", type_="Kurtas") for i in range(5)] +
            [labels_row(f"t{i}", type_="Tops") for i in range(8)] +
            [labels_row(f"j{i}", type_="Jeans") for i in range(4)])
    split = assign_splits(pd.DataFrame(rows), seed=2026)
    counts = split.groupby(["article_type", "split"]).size().unstack(fill_value=0)
    assert counts.loc["Kurtas"].to_dict() == {"dev": 1, "test": 4}
    assert counts.loc["Tops"].to_dict() == {"dev": 2, "test": 6}
    assert counts.loc["Jeans", "test"] == 4 and counts.loc["Jeans"].get("dev", 0) == 0


def test_tc_eval_01_the_committed_query_set_passes_every_check():
    """The real set in eval/queries/ is committed, so CI checks it on every push: labels, EXIF,
    licences, credits and that every in-catalogue type has at least 4 test photos."""
    from vsearch.queries import QUERIES, VOCABULARY

    result = check(QUERIES, VOCABULARY)
    assert result.errors == []
    assert result.warnings == []
    labels = pd.read_csv(QUERIES / "labels.csv", dtype=str, keep_default_na=False)
    assert set(labels["split"]) == {"dev", "test"}
