#!/usr/bin/env python3
"""Submit a ComfyUI API workflow, wait for completion, and print its history JSON."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def request_json(url: str, data: dict | None = None) -> dict:
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def parse_value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--set", action="append", default=[], metavar="NODE.INPUT=VALUE")
    parser.add_argument("--set-file", action="append", default=[], metavar="NODE.INPUT=PATH")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    workflow = json.loads(args.workflow.read_text())
    for override in args.set:
        address, raw_value = override.split("=", 1)
        node, input_name = address.split(".", 1)
        workflow[node]["inputs"][input_name] = parse_value(raw_value)
    for override in args.set_file:
        address, path = override.split("=", 1)
        node, input_name = address.split(".", 1)
        workflow[node]["inputs"][input_name] = Path(path).read_text().strip()

    client_id = str(uuid.uuid4())
    queued = request_json(f"{args.server}/prompt", {"prompt": workflow, "client_id": client_id})
    prompt_id = queued["prompt_id"]
    deadline = time.monotonic() + args.timeout

    while time.monotonic() < deadline:
        history = request_json(f"{args.server}/history/{prompt_id}")
        if prompt_id in history:
            item = history[prompt_id]
            status = item.get("status", {})
            if status.get("status_str") == "error":
                print(json.dumps(item, indent=2))
                return 1
            if status.get("completed"):
                print(json.dumps(item, indent=2))
                return 0
        time.sleep(2)

    raise TimeoutError(f"ComfyUI prompt {prompt_id} did not complete within {args.timeout}s")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as error:
        print(error.read().decode(errors="replace"))
        raise
