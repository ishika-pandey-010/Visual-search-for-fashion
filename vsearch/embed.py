"""Image embeddings from the two models compared in this project (D-04).

Both load the same way: a pinned snapshot from Hugging Face (D-19), opened with open_clip's
`local-dir:` loader. Only the image tower is used.
"""
import os

import numpy as np

# US-02: the two models, pinned to commit SHAs. Checked 2026-10-20.
MODELS = {
    "openclip": {
        "label": "OpenCLIP ViT-B-32 (laion2b_s34b_b79k)",
        "repo": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
        "revision": "1a25a446712ba5ee05982a381eed697ef9b435cf",
    },
    "fashionclip": {
        "label": "Marqo-FashionCLIP (ViT-B-16)",
        "repo": "Marqo/marqo-fashionCLIP",
        "revision": "44f4c655124ed71e90cbf528d82f508d69d8a81b",
    },
}
WEIGHT_FILES = ["open_clip_config.json", "open_clip_model.safetensors"]


class ClipEmbedder:
    """`embed(images)` returns float32 vectors of length 1, one row per PIL image. CPU only (D-17)."""

    def __init__(self, key, threads=None):
        import open_clip
        import torch
        from huggingface_hub import snapshot_download

        self.key = key
        spec = MODELS[key]
        threads = threads or int(os.environ.get("VSEARCH_TORCH_THREADS", 0)) or None
        if threads:
            torch.set_num_threads(threads)
        self._torch = torch
        path = snapshot_download(spec["repo"], revision=spec["revision"], allow_patterns=WEIGHT_FILES)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(f"local-dir:{path}", device="cpu")
        self.model.eval()
        with torch.no_grad():
            probe = self.model.encode_image(torch.zeros(1, 3, *self._input_size()))
        self.dim = int(probe.shape[1])

    def _input_size(self):
        size = self.model.visual.image_size
        return size if isinstance(size, (tuple, list)) else (size, size)

    def describe(self):
        return {"model": self.key, **MODELS[self.key], "dim": self.dim,
                "torch_threads": self._torch.get_num_threads()}

    def embed(self, images):
        torch = self._torch
        batch = torch.stack([self.preprocess(img.convert("RGB")) for img in images])
        with torch.no_grad():
            vectors = self.model.encode_image(batch).float()
        vectors = torch.nn.functional.normalize(vectors, dim=-1)
        return vectors.numpy().astype(np.float32)
