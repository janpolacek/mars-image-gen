#!/usr/bin/env python3
"""Build editable ComfyUI UI workflows from the checked API graphs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "workflows" / "api"
UI_DIR = ROOT / "workflows"

OUTPUTS = {
    "UNETLoader": [("MODEL", "MODEL")],
    "CLIPLoader": [("CLIP", "CLIP")],
    "VAELoader": [("VAE", "VAE")],
    "CLIPTextEncode": [("CONDITIONING", "CONDITIONING")],
    "ConditioningZeroOut": [("CONDITIONING", "CONDITIONING")],
    "ConditioningCombine": [("CONDITIONING", "CONDITIONING")],
    "LoadImage": [("IMAGE", "IMAGE"), ("MASK", "MASK")],
    "ImageScaleToTotalPixels": [("IMAGE", "IMAGE")],
    "VAEEncode": [("LATENT", "LATENT")],
    "ReferenceLatent": [("CONDITIONING", "CONDITIONING")],
    "EmptyFlux2LatentImage": [("LATENT", "LATENT")],
    "RandomNoise": [("NOISE", "NOISE")],
    "CFGGuider": [("GUIDER", "GUIDER")],
    "KSamplerSelect": [("SAMPLER", "SAMPLER")],
    "Flux2Scheduler": [("SIGMAS", "SIGMAS")],
    "SamplerCustomAdvanced": [("output", "LATENT"), ("denoised_output", "LATENT")],
    "VAEDecode": [("IMAGE", "IMAGE")],
    "SaveImage": [("images", "IMAGE")],
}

INPUT_ORDER = {
    "UNETLoader": ["unet_name", "weight_dtype"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "VAELoader": ["vae_name"],
    "CLIPTextEncode": ["clip", "text"],
    "ConditioningZeroOut": ["conditioning"],
    "ConditioningCombine": ["conditioning_1", "conditioning_2"],
    "LoadImage": ["image"],
    "ImageScaleToTotalPixels": ["image", "upscale_method", "megapixels", "resolution_steps"],
    "VAEEncode": ["pixels", "vae"],
    "ReferenceLatent": ["conditioning", "latent"],
    "EmptyFlux2LatentImage": ["width", "height", "batch_size"],
    "RandomNoise": ["noise_seed"],
    "CFGGuider": ["model", "positive", "negative", "cfg"],
    "KSamplerSelect": ["sampler_name"],
    "Flux2Scheduler": ["steps", "width", "height"],
    "SamplerCustomAdvanced": ["noise", "guider", "sampler", "sigmas", "latent_image"],
    "VAEDecode": ["samples", "vae"],
    "SaveImage": ["images", "filename_prefix"],
}

INPUT_TYPES = {
    "clip": "CLIP", "conditioning": "CONDITIONING", "conditioning_1": "CONDITIONING", "conditioning_2": "CONDITIONING", "latent": "LATENT",
    "pixels": "IMAGE", "vae": "VAE", "model": "MODEL", "positive": "CONDITIONING",
    "negative": "CONDITIONING", "noise": "NOISE", "guider": "GUIDER",
    "sampler": "SAMPLER", "sigmas": "SIGMAS", "latent_image": "LATENT",
    "samples": "LATENT", "images": "IMAGE", "image": "IMAGE",
}

POSITIONS_01 = {
    1: (-900, -80), 2: (-900, 120), 3: (-900, 340), 4: (-520, -60),
    5: (-80, 210), 6: (-520, 520), 7: (-80, 520), 8: (180, 40),
    9: (180, 420), 10: (180, 560), 11: (500, 160), 12: (820, 160), 13: (1100, 160),
    14: (-520, -300), 15: (-520, 230), 16: (-80, -100), 17: (180, 100),
}

POSITIONS_02 = {
    1: (-1180, -180), 2: (-1180, 20), 3: (-1180, 240), 4: (-820, -180), 5: (-380, 80),
    6: (-1180, 520), 7: (-860, 520), 8: (-540, 520), 9: (-220, 460), 10: (-220, 620),
    11: (-1180, 860), 12: (-860, 860), 13: (-540, 860), 14: (80, 460), 15: (80, 620),
    16: (-1180, 1200), 17: (-860, 1200), 18: (-540, 1200), 19: (380, 460), 20: (380, 620),
    21: (380, 900), 22: (700, 900), 23: (700, 460), 24: (700, 1080), 25: (700, 1240),
    26: (1020, 650), 27: (1340, 650), 28: (1660, 650),
    29: (-820, 80), 30: (-820, 340), 31: (-380, -80), 32: (-80, 80),
}

UI_REFERENCE_OUTPUTS = {
    "mars-ai-stories/references/ARES01_reference_front_left.png":
        "ARES01_reference_front_left.png",
    "mars-ai-stories/references/ARES01_reference_side.png":
        "ARES01_reference_side.png",
    "mars-ai-stories/references/ARES01_reference_rear_right.png":
        "ARES01_reference_rear_right.png",
}


def node_title(workflow: str, node_id: int, class_type: str) -> str | None:
    if class_type == "CLIPTextEncode":
        if workflow == "01":
            return {4: "Vehicle identity - keep stable", 14: "EDIT CAMERA VIEW / ANGLE", 15: "Reference photo style - keep stable"}[node_id]
        return {4: "Vehicle identity - keep stable", 29: "EDIT SCENE DESCRIPTION", 30: "Photo style - keep stable"}[node_id]
    if workflow == "02" and class_type == "LoadImage":
        return {6: "Reference 1 - front-left", 11: "Reference 2 - side", 16: "Reference 3 - rear-right"}[node_id]
    return None


def build(api_path: Path, ui_path: Path, workflow: str) -> None:
    api = json.loads(api_path.read_text())
    positions = POSITIONS_01 if workflow == "01" else POSITIONS_02
    link_ids: dict[tuple[str, int, str, int], int] = {}
    source_links: dict[tuple[str, int], list[int]] = {}
    next_link = 1

    for target_id, spec in api.items():
        for target_slot, name in enumerate(INPUT_ORDER[spec["class_type"]]):
            value = spec["inputs"].get(name)
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                source_id, source_slot = value
                key = (source_id, source_slot, target_id, target_slot)
                link_ids[key] = next_link
                source_links.setdefault((source_id, source_slot), []).append(next_link)
                next_link += 1

    nodes = []
    links = []
    for target_id, spec in api.items():
        class_type = spec["class_type"]
        inputs = []
        widgets = []
        for target_slot, name in enumerate(INPUT_ORDER[class_type]):
            value = spec["inputs"].get(name)
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                source_id, source_slot = value
                link_id = link_ids[(source_id, source_slot, target_id, target_slot)]
                input_type = INPUT_TYPES[name]
                inputs.append({"name": name, "type": input_type, "link": link_id})
                links.append([link_id, int(source_id), source_slot, int(target_id), target_slot, input_type])
            else:
                if class_type == "LoadImage" and name == "image":
                    if workflow == "02":
                        value = UI_REFERENCE_OUTPUTS[value]
                    inputs.extend([
                        {"localized_name": "image", "name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                        {"localized_name": "choose file to upload", "name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
                    ])
                    widgets.extend([value, "image"])
                    continue
                widget_type = "STRING" if isinstance(value, str) else ("FLOAT" if isinstance(value, float) else "INT")
                inputs.append({"name": name, "type": widget_type, "widget": {"name": name}, "link": None})
                widgets.append(value)
                if class_type == "RandomNoise" and name == "noise_seed":
                    widgets.append("fixed")
        outputs = []
        for slot, (name, output_type) in enumerate(OUTPUTS[class_type]):
            outputs.append({"name": name, "type": output_type, "links": source_links.get((target_id, slot)) or None})
        x, y = positions[int(target_id)]
        node = {
            "id": int(target_id), "type": class_type, "pos": [x, y], "size": [300, 150],
            "flags": {}, "order": int(target_id) - 1, "mode": 0, "inputs": inputs, "outputs": outputs,
            "properties": {"cnr_id": "comfy-core", "ver": "0.8.2", "Node name for S&R": class_type},
            "widgets_values": widgets,
        }
        title = node_title(workflow, int(target_id), class_type)
        if title:
            node["title"] = title
        nodes.append(node)

    graph = {
        "id": f"mars-mission-{workflow}", "revision": 0, "last_node_id": max(map(int, api)),
        "last_link_id": next_link - 1, "nodes": nodes, "links": links,
        "groups": ([{"id": 1, "title": "Persistent rover identity and photography style", "bounding": [-850, -230, 760, 520], "color": "#3f789e", "font_size": 22, "flags": {}}] if workflow == "01" else [
            {"id": 1, "title": "Three canonical references - all define ARES-01", "bounding": [-1220, 470, 1360, 910], "color": "#3f789e", "font_size": 22, "flags": {}},
            {"id": 2, "title": "Scenario prompt - edit SCENARIO only", "bounding": [-850, -230, 780, 500], "color": "#b58b2a", "font_size": 22, "flags": {}},
        ]),
        "config": {}, "extra": {"frontendVersion": "1.52.7", "workflowRendererVersion": "LG"}, "version": 0.4,
    }
    ui_path.write_text(json.dumps(graph, indent=2) + "\n")


build(API_DIR / "Mars Mission - 01 - Canonical Rover References.api.json", UI_DIR / "Mars Mission - 01 - Canonical Rover References.json", "01")
build(API_DIR / "Mars Mission - 02 - Multi-Reference Scene.api.json", UI_DIR / "Mars Mission - 02 - Multi-Reference Scene.json", "02")
