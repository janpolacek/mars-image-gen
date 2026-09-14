# Mars AI Stories

Mars AI Stories is a code-driven toolset for building coherent visual lore: describe a planet, an expedition, a vehicle and its exploration events, then render vehicle references and scenes through ComfyUI.

The included Mars vehicles are prompt examples only. Generated images, model weights, access tokens and machine-specific configuration are intentionally excluded from this repository.

## What it generates

The same shared workflows run for every vehicle:

1. `01a-canonical` creates one clean canonical vehicle reference from a description and optional detail images.
2. `01b-angle` derives front-left, side and rear-right reference views from that canonical image.
3. `02-scene` uses the three reference views plus a scene description to create an exploration image.

The pipeline stores generated files under `stories/<vehicle>/` locally:

```text
stories/<vehicle>/
├── references/
│   ├── canonical.png
│   ├── front-left.png
│   ├── side.png
│   └── rear-right.png
└── scenes/
    ├── 01-landing.png
    ├── 02-investigation.png
    └── 03-years-later.png
```

Those files are ignored by Git. Review and select generated images yourself before treating any detail as story canon.

## Requirements

- A working ComfyUI installation reachable through its HTTP API.
- The model files referenced by the workflow JSON installed in that ComfyUI instance.
- Python 3.11+; the runtime scripts use only the standard library.

The workflow JSON names the required model files. Model licences apply separately from this repository's MIT licence.

## Configure a world

Edit `story_set.json`.

- `planet.visual_description` is the visible terrain and atmosphere for scenes.
- `planet.lore` and `mission` keep background context; they are not automatically added to visual prompts.
- `identity` defines the stable vehicle shape, locomotion or propulsion, materials, instruments and front/rear landmarks.
- `reference_pose` defines the canonical studio reference.
- `reference_angles` defines the three requested derived views.
- `scenes` defines one visible action or moment per image.

Keep a vehicle description concrete and mechanically simple: one body type, one propulsion or locomotion system, a small fixed instrument set, and clear attachment points. Optional `assets` are reference images for a specific detail, such as a camera housing or wheel construction; they are used only for the canonical stage.

## Add a vehicle

Add an object to `vehicles` in `story_set.json`; do not copy or create a workflow per vehicle. Use an unused, folder-safe ID such as `vehicle-04-orbiter`.

```json
{
  "id": "vehicle-04-orbiter",
  "name": "ORBITER-04",
  "mission": "One sentence of mission context.",
  "identity": "Short concrete description of body, locomotion, instruments, materials and limits.",
  "assets": [],
  "reference_pose": "White seamless studio background, front-left quarter view.",
  "reference_angles": [
    ["front-left", "front-left quarter view high-angle shot medium shot"],
    ["side", "left side view eye-level shot medium shot"],
    ["rear-right", "back-right quarter view eye-level shot medium shot"]
  ],
  "scenes": [
    {"id": "01-landing", "description": "One visible landing moment."},
    {"id": "02-investigation", "description": "One visible investigation moment."},
    {"id": "03-years-later", "description": "One visible aged-but-maintained moment."}
  ]
}
```

## Run

Set the ComfyUI address, then generate one vehicle or all configured vehicles:

```sh
export MARS_SERVER=http://127.0.0.1:8188

# Optional: refresh the editable UI workflow examples for one vehicle.
python3 scripts/build_ui_workflows.py --server "$MARS_SERVER" --vehicle vehicle-04-orbiter

# Canonical reference, three views and three scenes.
python3 -u scripts/generate_story_set_via_api.py \
  --server "$MARS_SERVER" --stage all --vehicle vehicle-04-orbiter
```

For a manual reference-selection step, run the stages separately:

```sh
python3 scripts/generate_story_set_via_api.py --server "$MARS_SERVER" --stage references --vehicle vehicle-04-orbiter
# Review the three files in stories/vehicle-04-orbiter/references/.
python3 scripts/generate_story_set_via_api.py --server "$MARS_SERVER" --stage scenes --vehicle vehicle-04-orbiter
```

Available stages are `canonical`, `references`, `angles`, `scenes` and `all`. Use `--resume` only after an interruption: it reuses a result only if the exact graph and source-image hashes match.

## Workflows and run records

`workflows/` contains the reusable API and UI workflow JSON for the three stages. They are examples to inspect or import into ComfyUI; the Python runner builds the same graphs from `story_set.json`.

During generation, `stories/<vehicle>/runs/` may contain an ignored audit trail:

| File | Meaning |
| --- | --- |
| `*.api.json` | Exact ComfyUI graph submitted for one image. |
| `*.inputs.json` | Resolved prompt text and source-image hashes. |
| `*.job.json` | Submission ID and graph hash, written immediately after queueing. |
| `*.history.json` | Final ComfyUI execution record. |

They are useful for reproducing or recovering a render but are not inputs for adding a new vehicle. Delete them together with a finished local batch when they are no longer needed.

## Repository layout

```text
story_set.json                         Editable planet, vehicle and scene inputs
workflows/                             Shared ComfyUI API and UI workflow JSON
scripts/generate_story_set_via_api.py  Batch runner
scripts/build_ui_workflows.py          Populate UI workflow examples from the manifest
scripts/workflow_factory.py            Canonical and scene graph builder
scripts/angle_workflow.py              Camera-view graph builder
scripts/prompt_inputs.py               Shared prompt composition
```

## Public repository hygiene

Do not commit generated imagery, detail assets, model files, logs, access tokens, machine addresses or ComfyUI run records. `.gitignore` excludes these local artifacts by default.

License: [MIT](LICENSE). The repository does not grant rights to third-party models or generated content.
