#!/usr/bin/env python3
"""Generate canonical rover views and three multi-reference story scenes per rover."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import time
import urllib.request
import uuid
from pathlib import Path


CAMERAS = [
    ("front-left", "CAMERA VIEW: strict front-left three-quarter vehicle documentation view. Full rover at rover height; show the three near-side wheels and at least two far-side wheels."),
    ("side", "CAMERA VIEW: strict broadside vehicle documentation view. Full rover perpendicular to camera; all three near-side wheels are distinct, non-overlapping, and fully visible."),
    ("rear-right", "CAMERA VIEW: strict rear-right three-quarter vehicle documentation view. Full rover at rover height; show the three near-side wheels and at least two far-side wheels."),
]


def request(url: str, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}), timeout=30) as response:
        return json.load(response)


def run(server: str, graph: dict) -> dict:
    prompt_id = request(f"{server}/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})["prompt_id"]
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        record = request(f"{server}/history/{prompt_id}").get(prompt_id)
        if record and record.get("status", {}).get("completed"):
            if record["status"].get("status_str") == "error":
                raise RuntimeError(json.dumps(record, indent=2))
            return record
        time.sleep(2)
    raise TimeoutError(prompt_id)


def output_path(record: dict, node: str, output_root: Path) -> Path:
    image = record["outputs"][node]["images"][0]
    return output_root / image.get("subfolder", "") / image["filename"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--comfy-root", type=Path, required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    args = parser.parse_args()
    root = args.root.resolve()
    config = json.loads((root / "story_set.json").read_text())
    w1 = json.loads((root / "workflows/api/Mars Mission - 01 - Canonical Rover References.api.json").read_text())
    w2 = json.loads((root / "workflows/api/Mars Mission - 02 - Multi-Reference Scene.api.json").read_text())
    output_root, input_root = args.comfy_root / "output", args.comfy_root / "input"

    for vehicle in config["vehicles"]:
        slug = vehicle["slug"]
        references: dict[str, str] = {}
        for camera_slug, camera in CAMERAS:
            graph = copy.deepcopy(w1)
            graph["4"]["inputs"]["text"] = vehicle["identity"]
            graph["14"]["inputs"]["text"] = camera
            graph["15"]["inputs"]["text"] = config["photo_style"]
            graph["13"]["inputs"]["filename_prefix"] = f"mars-ai-stories/stories/{slug}/references/{slug}-{camera_slug}"
            record = run(args.server, graph)
            source = output_path(record, "13", output_root)
            relative = Path("mars-ai-stories") / "stories" / slug / "references" / f"{camera_slug}.png"
            destination = input_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            references[camera_slug] = relative.as_posix()
            print(f"{slug}: reference {camera_slug}: {source.name}", flush=True)

        for scene_slug, scene in vehicle["scenes"]:
            graph = copy.deepcopy(w2)
            graph["4"]["inputs"]["text"] = vehicle["identity"]
            graph["29"]["inputs"]["text"] = scene
            graph["30"]["inputs"]["text"] = config["photo_style"]
            graph["6"]["inputs"]["image"] = references["front-left"]
            graph["11"]["inputs"]["image"] = references["side"]
            graph["16"]["inputs"]["image"] = references["rear-right"]
            graph["28"]["inputs"]["filename_prefix"] = f"mars-ai-stories/stories/{slug}/scenes/{scene_slug}"
            record = run(args.server, graph)
            source = output_path(record, "28", output_root)
            print(f"{slug}: scene {scene_slug}: {source.name}", flush=True)


if __name__ == "__main__":
    main()
