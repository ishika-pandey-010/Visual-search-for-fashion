"""Shared fixtures. Unit tests never download anything (D-20): this file generates a tiny
labels table and images table in the same shapes `vsearch.catalogue.load_sources()` returns."""
import io

import pandas as pd
import pytest
from PIL import Image

from vsearch.catalogue import CATALOGUE_TYPES, RESERVED_TYPES

COLOURS = ["Black", "White", "Blue", "Navy Blue", "Red", "Green"]
PER_TYPE_IN_FIXTURE = 6


def jpeg(colour_index, size=(384, 512)):
    """A solid-colour JPEG; each product gets a different colour so images differ."""
    rgb = ((colour_index * 37) % 256, (colour_index * 91) % 256, (colour_index * 53) % 256)
    buf = io.BytesIO()
    Image.new("RGB", size, rgb).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def keep_the_real_manifest_safe(tmp_path, monkeypatch):
    """No unit test may write the committed eval/catalogue-manifest.csv (it happened once, see
    docs/session-logs/2026-10-20-catalogue.md)."""
    monkeypatch.setattr("vsearch.catalogue.MANIFEST", tmp_path / "guarded-manifest.csv")


@pytest.fixture
def sources():
    """(labels, images, expected) with one of every kind of bad row the build must drop."""
    labels, images = [], []
    pid = 1000
    for type_ in CATALOGUE_TYPES + RESERVED_TYPES:
        for i in range(PER_TYPE_IN_FIXTURE):
            pid += 1
            labels.append({
                "id": pid, "gender": "Women" if i % 2 else "Men", "masterCategory": "Apparel",
                "subCategory": "Topwear", "articleType": type_, "baseColour": COLOURS[i % len(COLOURS)],
                "productDisplayName": f"{type_} {pid}",
            })
            images.append({"product_id": pid, "image_bytes": jpeg(pid)})

    bad = {}
    # a catalogue-type product with no colour label
    labels[0]["baseColour"] = None
    bad["no_label"] = labels[0]["id"]
    # a catalogue-type product whose image is missing from the image source
    bad["no_image"] = labels[1]["id"]
    images = [r for r in images if r["product_id"] != bad["no_image"]]
    # a catalogue-type product whose image is too small (short side 150 px)
    bad["image_too_small"] = labels[2]["id"]
    next(r for r in images if r["product_id"] == bad["image_too_small"])["image_bytes"] = jpeg(3, (150, 200))
    # a catalogue-type product whose image bytes aren't an image
    bad["image_unreadable"] = labels[3]["id"]
    next(r for r in images if r["product_id"] == bad["image_unreadable"])["image_bytes"] = b"not a jpeg"
    # an image with no label row at all
    images.append({"product_id": 999999, "image_bytes": jpeg(9)})
    # a product of a type that is neither catalogue nor reserved
    labels.append({**labels[5], "id": 888888, "articleType": "Socks", "productDisplayName": "Socks"})
    images.append({"product_id": 888888, "image_bytes": jpeg(8)})

    return pd.DataFrame(labels), pd.DataFrame(images), bad
