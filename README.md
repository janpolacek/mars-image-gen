# Mars Mission Generator — ComfyUI setup

Local FLUX.2 Klein workflows for visually continuous fictional Mars missions. This setup deliberately does **not** train a LoRA. Generated PNGs are first-pass candidates; review mechanical correctness and cross-scene identity before treating any as final.

## Story collection

`story_set.json` defines three original rover families and their three scene beats. Run `scripts/generate_story_set.py` on the WSL workstation to create, for each vehicle, three canonical reference views and these scenes: first message after landing, rock investigation, and a dusty three-years-later mission moment.

```text
stories/
  vehicle-01-atlas/{references,scenes}/
  vehicle-02-taiga/{references,scenes}/
  vehicle-03-vanguard/{references,scenes}/
```

The vehicle directions use broad regional or comic-book visual cues only. They do not depict real agencies, trademarks, franchise characters, logos, flags, or readable markings. Generated images are ignored by Git until deliberately curated for a separately licensed image release.

| Folder | Vehicle direction | Scenes |
|---|---|---|
| `vehicle-01-atlas` | Original American aerospace-inspired rover | landing, rock investigation, three years later |
| `vehicle-02-taiga` | Original Russian engineering-inspired rover | landing, rock investigation, three years later |
| `vehicle-03-vanguard` | Original superhero-comic-inspired rover | landing, rock investigation, three years later |

## Installed locations

- Project: `<project-root>/mars-ai-stories`
- ComfyUI: `<COMFY_ROOT>`
- Editable workflows: `<COMFY_ROOT>/user/default/workflows/`
- ComfyUI reference inputs: `<COMFY_ROOT>/input/mars-ai-stories/references/`
- Generated outputs: `<COMFY_ROOT>/output/mars-ai-stories/`

The project also keeps API-format equivalents under `workflows/api/` for repeatable execution.

## Models

| Model | Source and version | ComfyUI path | Size |
|---|---|---|---:|
| `flux-2-klein-4b-fp8.safetensors` | [Black Forest Labs FLUX.2 Klein 4B FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8), repository revision `5b4408e59397a4a37ccb46afe426d8ed86379441` | `models/diffusion_models/` | 4.07 GB |
| `qwen_3_4b.safetensors` | [Comfy-Org FLUX.2 Klein split files](https://huggingface.co/Comfy-Org/flux2-klein/tree/main/split_files/text_encoders) | `models/text_encoders/` | 8.04 GB |
| `flux2-vae.safetensors` | [Comfy-Org FLUX.2 VAE](https://huggingface.co/Comfy-Org/flux2-dev/tree/main/split_files/vae) | `models/vae/` | 336 MB |

`scripts/install_models.sh` downloads missing files, resumes interrupted transfers, and verifies SHA-256 checksums. Total disk use is approximately 12.45 GB. The 4B model is Apache-2.0 licensed; review each upstream repository for its current terms.

## Verified runtime

- Windows 11 host with Ubuntu 24.04 under WSL2
- NVIDIA GeForce RTX 5060, 8151 MiB VRAM, Windows driver 616.64
- ComfyUI `0.35.0`, git commit `c75d8c966c29cb0392259af791f43373315b72db`
- Python `3.12.3`
- PyTorch `2.14.0+cu130`
- `comfy-kitchen 0.2.33`, `comfy-aimdo 0.5.3`
- No custom nodes are required by either Mars workflow; every generation node is native ComfyUI.

The service reserves 1 GB VRAM and disables asynchronous offloading. The text encoder is explicitly loaded on CPU; ComfyUI performs ordinary model/CPU offloading as needed. WSL currently has about 25 GiB RAM and 24 GiB swap available.

## Workflow 1 — Canonical Rover References

Open `Mars Mission - 01 - Canonical Rover References.json`.

Purpose: text description → one ARES-01 reference candidate. Three clearly titled text nodes keep the editing boundary explicit: change `CAMERA VIEW / ANGLE` only; keep `Vehicle identity` and `Reference photo style` stable.

Verified defaults:

- FLUX.2 Klein 4B FP8 distilled
- 896×672 latent; batch 1
- Euler sampler; FLUX.2 scheduler; 4 steps; CFG 1.0
- Qwen text encoder on CPU
- Output prefix: `mars-ai-stories/references/ARES01_reference_front_left`

The workflow now exposes three separate text inputs: stable `Vehicle identity`, editable `CAMERA VIEW / ANGLE`, and stable `Reference photo style`. Change only the camera-view input when producing front-left, exact-side, and rear-right candidates. The prompt examples under `prompts/` explicitly request three distinct airless woven metallic-mesh wheels per side. For a later selection run, set seed control to randomize and queue approximately 20 runs per view. Mechanical correctness matters more than drama.

After selecting better images, copy them into ComfyUI input storage with these exact names:

```text
input/mars-ai-stories/references/ARES01_reference_front_left.png
input/mars-ai-stories/references/ARES01_reference_side.png
input/mars-ai-stories/references/ARES01_reference_rear_right.png
```

## Workflow 2 — Multi-Reference Scene

Open `Mars Mission - 02 - Multi-Reference Scene.json`.

Purpose: three ARES-01 reference images + scenario text → a new mission photograph. Each input is resized to about 0.6 MP, VAE-encoded, and attached to both positive and zeroed-negative conditioning through a chained native `ReferenceLatent` node. This is FLUX.2 Klein's native multi-reference path, not an SDXL IP-Adapter.

Verified defaults:

- Three fixed `LoadImage` inputs using root-level aliases of the approved
  references, which ComfyUI's media picker can reopen reliably. The organized
  copies and API workflow use the stable nested input names above.
- 896×504 requested wide latent; decoded test output was 896×496 after model alignment
- Euler sampler; FLUX.2 scheduler; 4 steps; CFG 1.0
- Output prefix: `mars-ai-stories/scenes/ARES01_scene_ridge_test`

The workflow exposes separate `Vehicle identity`, `SCENE DESCRIPTION`, and `Photo style` text inputs. Change only `SCENE DESCRIPTION` for new mission moments such as a crater, hill, valley, or storm. Keep the reference files, vehicle identity, and photo style unchanged almost all the time. Replacing a canonical set requires only overwriting the three input files with the same exact names and reopening or refreshing the workflow.

## 8 GB VRAM notes

- Prefer the distilled FP8 model and four steps. The Base checkpoint is not used by these workflows.
- Keep the text encoder on CPU and retain the service's 1 GB VRAM reservation.
- Start references at 896×672 and scenes at 896×504. Raise resolution only after a successful run.
- Each reference is reduced to 0.6 MP before multi-reference encoding.
- Observed generation time was roughly 25–63 seconds for reference runs (cold model load included) and 22 seconds for the warmed three-reference ridge scene.
- On OOM: clear the queue, restart ComfyUI, reduce references to 0.4 MP, then lower scene resolution to 768×432. Do not increase steps or resolution until the reduced workflow is stable.

## Validation record

On 2026-09-13 the following completed on the RTX 5060:

1. Workflow 1 executed with the distilled FP8 model.
2. The first front-left, side, and rear-right test outputs were retained as requested.
3. All three exact input files were uploaded and chained into Workflow 2.
4. Workflow 2 generated `ARES01_scene_ridge_test.png` successfully with no missing model or node error.
5. After prompt splitting, both API workflows generated successfully through native `ConditioningCombine` nodes; Workflow 2 reopened with its three approved reference aliases selected and no validation errors.

These are workflow-smoke-test images, not approved final canonical references. Numerical wheel accuracy and cross-view identity remain selection criteria for the later 20-candidate manual review.
