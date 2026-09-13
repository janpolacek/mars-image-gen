#!/usr/bin/env bash
set -euo pipefail

COMFY_ROOT=${COMFY_ROOT:-"$HOME/ai/comfyui/app"}

download_model() {
  local url=$1
  local destination=$2
  local expected_sha256=$3
  local partial="${destination}.partial"

  mkdir -p "$(dirname "$destination")"
  if [[ -f "$destination" ]] && echo "$expected_sha256  $destination" | sha256sum --check --status; then
    printf 'Already verified: %s\n' "$destination"
    return
  fi

  curl --fail --location --retry 8 --retry-all-errors --continue-at - --output "$partial" "$url"
  echo "$expected_sha256  $partial" | sha256sum --check
  mv "$partial" "$destination"
  printf 'Installed: %s\n' "$destination"
}

download_model \
  'https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/resolve/main/flux-2-klein-4b-fp8.safetensors' \
  "$COMFY_ROOT/models/diffusion_models/flux-2-klein-4b-fp8.safetensors" \
  '97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6'

download_model \
  'https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors' \
  "$COMFY_ROOT/models/text_encoders/qwen_3_4b.safetensors" \
  '6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a'

download_model \
  'https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors' \
  "$COMFY_ROOT/models/vae/flux2-vae.safetensors" \
  'd64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5'

printf 'Mars Mission FLUX.2 Klein model pack verified.\n'
