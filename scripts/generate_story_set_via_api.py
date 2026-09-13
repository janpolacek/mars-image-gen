#!/usr/bin/env python3
"""Run the story set from any machine that can reach ComfyUI's HTTP API."""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from generate_story_set import CAMERAS


def request(url: str, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}), timeout=60) as response:
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


def image_info(record: dict, node: str) -> dict:
    return record["outputs"][node]["images"][0]


def download(server: str, image: dict) -> bytes:
    query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
    with urllib.request.urlopen(f"{server}/view?{query}", timeout=120) as response:
        return response.read()


def upload(server: str, content: bytes, filename: str, subfolder: str) -> str:
    boundary = f"----mars-ai-stories-{uuid.uuid4().hex}"
    parts = []
    def field(name: str, value: str) -> None:
        parts.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), value.encode(), b"\r\n"])
    field("subfolder", subfolder)
    field("overwrite", "true")
    parts.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode(), f"Content-Type: {mimetypes.guess_type(filename)[0] or 'application/octet-stream'}\r\n\r\n".encode(), content, b"\r\n", f"--{boundary}--\r\n".encode()])
    req = urllib.request.Request(f"{server}/upload/image", data=b"".join(parts), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.load(response)
    return "/".join(part for part in [result.get("subfolder", subfolder), result["name"]] if part)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    args = parser.parse_args()
    root, server = args.root.resolve(), args.server.rstrip("/")
    config = json.loads((root / "story_set.json").read_text())
    w1 = json.loads((root / "workflows/api/Mars Mission - 01 - Canonical Rover References.api.json").read_text())
    w2 = json.loads((root / "workflows/api/Mars Mission - 02 - Multi-Reference Scene.api.json").read_text())

    for vehicle in config["vehicles"]:
        slug, refs = vehicle["slug"], {}
        for camera_slug, camera in CAMERAS:
            graph = copy.deepcopy(w1)
            graph["4"]["inputs"]["text"], graph["14"]["inputs"]["text"], graph["15"]["inputs"]["text"] = vehicle["identity"], camera, config["photo_style"]
            graph["13"]["inputs"]["filename_prefix"] = f"mars-ai-stories/stories/{slug}/references/{slug}-{camera_slug}"
            image = image_info(run(server, graph), "13")
            reference_subfolder = f"mars-ai-stories/stories/{slug}/references"
            refs[camera_slug] = upload(server, download(server, image), f"{camera_slug}.png", reference_subfolder)
            print(f"{slug}: reference {camera_slug}", flush=True)
        for scene_slug, scene in vehicle["scenes"]:
            graph = copy.deepcopy(w2)
            graph["4"]["inputs"]["text"], graph["29"]["inputs"]["text"], graph["30"]["inputs"]["text"] = vehicle["identity"], scene, config["photo_style"]
            graph["6"]["inputs"]["image"], graph["11"]["inputs"]["image"], graph["16"]["inputs"]["image"] = refs["front-left"], refs["side"], refs["rear-right"]
            graph["28"]["inputs"]["filename_prefix"] = f"mars-ai-stories/stories/{slug}/scenes/{scene_slug}"
            run(server, graph)
            print(f"{slug}: scene {scene_slug}", flush=True)


if __name__ == "__main__":
    main()
