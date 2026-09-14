---
name: mars-story-toolset
description: Build coherent planet, expedition, vehicle and exploration-scene inputs, then generate local reference and scene images with this repository's shared ComfyUI workflows.
---

# Mars story toolset

Read the root `README.md` before changing inputs or running generation. `story_set.json` is the source of truth. Mars and its sample vehicles are examples, not a required setting.

## Authoring

- Keep background canon separate from visible instructions. `planet.lore` and a vehicle `mission` are context; only visible descriptions belong in an image prompt.
- Maintain one stable vehicle identity: silhouette, material palette, propulsion or locomotion, fixed instruments and front/rear orientation.
- Use one readable action per scene, with terrain, camera position, lighting and a specific wear state.
- Prefer concrete relationships over extra parts. Tools must attach to the vehicle and interact plausibly with their target.
- Optional assets guide a detail in the canonical stage only. Do not use them to redesign the vehicle in later scenes.

## Execution

The shared stages are canonical reference, derived camera views and scenes. `scripts/generate_story_set_via_api.py` runs them through the ComfyUI HTTP API; `scripts/build_ui_workflows.py` produces matching editable UI examples.

Run `references` before `scenes` when the user wants to select views manually. Use `--resume` only after an interrupted job; it verifies graph and source-image equality before reuse. Do not submit a duplicate while the original job might still be running.

Generated files and records remain under ignored `stories/<vehicle>/`. Never put generated images, detail assets, access tokens, local paths or server addresses into the repository.

## Handoff

Report generated-file locations and execution status, but do not claim that an image is realistic, mechanically consistent or an approved canon choice without user review.
