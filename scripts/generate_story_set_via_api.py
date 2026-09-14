#!/usr/bin/env python3
"""Run the story set from any machine that can reach ComfyUI's HTTP API."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from workflow_factory import build
from angle_workflow import build as build_angle
import prompt_inputs


def request(url: str, data: dict | None = None) -> dict:
    payload = None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}), timeout=60) as response:
        body = response.read()
        return json.loads(body) if body else {}


def run(server: str, graph: dict, timeout: int = 3600, job_path=None, resume=False) -> dict:
    fingerprint = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()
    if resume and job_path and job_path.exists():
        job = json.loads(job_path.read_text())
        if job['graph_sha256'] != fingerprint:
            raise RuntimeError('Interrupted job inputs changed; inspect and archive its record first')
        prompt_id = job['prompt_id']
        history = request(f'{server}/history/{prompt_id}')
        queue = request(f'{server}/queue')
        queued = any(row[1] == prompt_id for row in queue['queue_running'] + queue['queue_pending'])
        if prompt_id not in history and not queued:
            raise RuntimeError(f'Cannot locate interrupted job {prompt_id}. Check remote output before moving {job_path} aside and retrying.')
    else:
        prompt_id = request(f"{server}/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})["prompt_id"]
        if job_path:
            job_path.write_text(json.dumps({'prompt_id': prompt_id, 'graph_sha256': fingerprint})+'\n')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = request(f"{server}/history/{prompt_id}").get(prompt_id)
        if record:
            if record.get('status', {}).get('status_str') == 'error':
                raise RuntimeError(json.dumps(record, indent=2))
            if record.get('status', {}).get('completed'):
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
    parser.add_argument('--stage', choices=['all', 'canonical', 'references', 'angles', 'scenes'], default='all')
    parser.add_argument('--vehicle', help='Run only this vehicle slug')
    parser.add_argument('--resume', action='store_true', help='Reuse locally successful images only when their exact graph still matches')
    args = parser.parse_args()
    root, server = args.root.resolve(), args.server.rstrip("/")
    config = json.loads((root / "story_set.json").read_text())
    if args.vehicle and args.vehicle not in {v['slug'] for v in config['vehicles']}:
        parser.error('Unknown vehicle slug: '+args.vehicle)
    for _, camera in config['reference_angles']:
        prompt_inputs.angle(camera)
    queue = request(f'{server}/queue')
    if queue['queue_running'] or queue['queue_pending']:
        raise RuntimeError('Queue is busy; inspect existing jobs before starting the story runner')
    loaded_family = None
    reference_hashes = {}
    def upload_reference(content, filename, subfolder):
        remote = upload(server, content, filename, subfolder)
        reference_hashes[remote] = hashlib.sha256(content).hexdigest()
        return remote
    for vehicle in config["vehicles"]:
        if args.vehicle and vehicle['slug'] != args.vehicle:
            continue
        slug, refs = vehicle["slug"], {}
        base = root / 'stories' / slug
        def execute(name, instruction, references, scene=False):
            nonlocal loaded_family
            folder = 'scenes' if scene else 'references'
            is_angle = not scene and name != 'canonical'
            family = 'qwen' if is_angle else 'flux'
            photo_style = '' if is_angle else prompt_inputs.style(config, scene)
            prefix = f'mars-ai-stories/stories/{slug}/{folder}/{name}'
            if is_angle:
                graph, output = build_angle(references[0], instruction, prefix)
            else:
                graph, output = build(vehicle['identity'], instruction, photo_style, references, prefix, scene=scene)
            directory = base / 'runs'
            directory.mkdir(parents=True, exist_ok=True)
            destination = base / folder / f'{name}.png'
            graph_path = directory / f'{name}.api.json'
            history_path = directory / f'{name}.history.json'
            inputs_path = directory / f'{name}.inputs.json'
            hashes = {path: reference_hashes[path] for path in references}
            if args.resume and destination.exists() and graph_path.exists() and history_path.exists():
                previous = json.loads(history_path.read_text())
                if json.loads(graph_path.read_text()) != graph:
                    raise RuntimeError(f'{slug}/{name}: inputs changed; archive old output before resuming')
                saved_inputs = json.loads(inputs_path.read_text()) if inputs_path.exists() else {}
                if saved_inputs.get('reference_sha256', {}) != hashes:
                    raise RuntimeError(f'{slug}/{name}: reference content changed or lacks provenance; regenerate this output')
                if previous.get('status', {}).get('status_str') == 'success' and previous['status'].get('completed'):
                    print(f'{slug}: {name} reused (matching successful graph)', flush=True)
                    return upload_reference(destination.read_bytes(), f'{name}.png', f'mars-ai-stories/stories/{slug}/{folder}') if not scene else None
            (directory / f'{name}.inputs.json').write_text(json.dumps({
                'vehicle': vehicle['identity'], 'instruction': instruction,
                'style': photo_style, 'references': references,
                'reference_sha256': hashes, 'model_family': family,
                'planet_id': config['planet']['id'], 'mission': vehicle.get('mission'),
                'stage': 'scene' if scene else ('canonical' if name == 'canonical' else 'angle')
            }, indent=2)+'\n')
            (directory / f'{name}.api.json').write_text(json.dumps(graph, indent=2)+'\n')
            if loaded_family != family:
                request(server+'/free', {'unload_models': True, 'free_memory': True})
                loaded_family = family
            record = run(server, graph, job_path=directory/f'{name}.job.json', resume=args.resume)
            content = download(server, image_info(record, output))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            (directory / f'{name}.history.json').write_text(json.dumps(record, indent=2)+'\n')
            print(f'{slug}: {name} complete', flush=True)
            return upload_reference(content, f'{name}.png', f'mars-ai-stories/stories/{slug}/{folder}') if not scene else None
        if args.stage == 'scenes':
            for angle, _ in config['reference_angles']:
                path = base / 'references' / f'{angle}.png'
                refs[angle] = upload_reference(path.read_bytes(), path.name, f'mars-ai-stories/stories/{slug}/references')
            for name, scene in vehicle['scenes']:
                execute(name, prompt_inputs.scene(scene), list(refs.values()), scene=True)
            continue
        assets = []
        for asset in vehicle.get('assets', []) if args.stage != 'angles' else []:
            path = (root / asset['path']).resolve()
            assets.append(upload_reference(path.read_bytes(), path.name, f'mars-ai-stories/stories/{slug}/assets'))
        instruction = prompt_inputs.canonical(config, vehicle)
        if args.stage == 'angles':
            path = base / 'references' / 'canonical.png'
            canonical = upload_reference(path.read_bytes(), path.name, f'mars-ai-stories/stories/{slug}/references')
        else:
            canonical = execute('canonical', instruction, assets)
        if args.stage == 'canonical':
            continue
        cameras = config['reference_angles']
        for angle, camera in cameras:
            refs[angle] = execute(angle, prompt_inputs.angle(camera, vehicle), [canonical])
        if args.stage in ('angles', 'references'):
            continue
        for name, scene in vehicle['scenes']:
            execute(name, prompt_inputs.scene(scene), list(refs.values()), scene=True)


if __name__ == "__main__":
    main()
