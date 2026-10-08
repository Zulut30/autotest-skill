"""Approved baseline comparison under matching browser conditions."""

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from .errors import Blocked


def compare(root, baseline, current_image, conditions):
    project = Path(root).resolve()
    path = (project / baseline).resolve()
    if project not in path.parents or not path.is_file() or path.stat().st_size > 10_000_000:
        raise Blocked("Approved visual baseline is unavailable or outside the project")
    metadata = Path(str(path) + ".json")
    if not metadata.is_file() or metadata.stat().st_size > 20000:
        raise Blocked("Visual baseline requires browser-condition metadata")
    approved = json.loads(metadata.read_text())
    if any(approved.get(key) != value for key, value in conditions.items()):
        raise Blocked("Visual baseline conditions differ from the current run")
    with Image.open(path) as expected, Image.open(current_image) as actual:
        if expected.size != actual.size:
            raise Blocked("Visual baseline dimensions differ from the current viewport")
        diff = ImageChops.difference(expected.convert("RGB"), actual.convert("RGB"))
        ratio = sum(ImageStat.Stat(diff).sum) / (expected.width * expected.height * 3 * 255)
    return {"difference_ratio": ratio, "metric": "normalized mean absolute RGB difference"}
