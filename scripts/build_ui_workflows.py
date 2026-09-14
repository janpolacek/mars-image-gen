#!/usr/bin/env python3
"""Build shared stage templates, never per-vehicle workflow copies."""
import argparse
import json
from pathlib import Path
from generate_story_set_via_api import request
from workflow_factory import build, ui_graph
from angle_workflow import build as build_angle
import prompt_inputs

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--server', default='http://127.0.0.1:8188')
    p.add_argument('--vehicle', default='vehicle-01-atlas', help='Populate shared templates with this vehicle input preset')
    args = p.parse_args()
    schema = request(args.server.rstrip('/') + '/object_info')
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'story_set.json').read_text())
    vehicle = next(v for v in config['vehicles'] if v['slug'] == args.vehicle)
    reference_root = f"mars-ai-stories/stories/{vehicle['slug']}/references"
    folder = root / 'workflows'
    folder.mkdir(exist_ok=True)
    stages = [
        ('01a-canonical', [f"mars-ai-stories/stories/{vehicle['slug']}/assets/{Path(a['path']).name}" for a in vehicle.get('assets', [])], False, prompt_inputs.canonical(config, vehicle)),
        ('01b-angle', [reference_root+'/canonical.png'], False,
         prompt_inputs.angle(dict(config['reference_angles'])['side'], vehicle)),
        ('02-scene', [f'{reference_root}/{angle}.png' for angle, _ in config['reference_angles']], True,
         prompt_inputs.scene(vehicle['scenes'][0][1]))]
    for name, refs, scene, instruction in stages:
        if name == '01b-angle':
            graph, _ = build_angle(refs[0], instruction, 'mars-ai-stories/manual/'+name)
        else:
            graph, _ = build(vehicle['identity'], instruction,
                             prompt_inputs.style(config, scene), refs, 'mars-ai-stories/manual/'+name, scene=scene)
        (folder / f'{name}.api.json').write_text(json.dumps(graph, indent=2)+'\n')
        (folder / f'{name}.json').write_text(json.dumps(ui_graph(graph, schema), indent=2)+'\n')
