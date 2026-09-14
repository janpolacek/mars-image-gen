"""Shared Qwen camera stage; settings match the user-approved ATLAS test."""

def build(reference, prompt, prefix, seed=410101):
    g = {}
    def add(kind, **inputs):
        key = str(len(g)+1)
        g[key] = {'class_type': kind, 'inputs': inputs, '_meta': {'title': kind}}
        return [key, 0]
    model = add('UNETLoader', unet_name='qwen_image_edit_2511_fp8mixed.safetensors', weight_dtype='default')
    # No 2511 multiple-angles LoRA has been published. Camera instructions in
    # the prompt drive the angle edit; the official 2511 Lightning LoRA below
    # keeps the stage practical on local hardware.
    model = add('LoraLoaderModelOnly', model=model, lora_name='Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors', strength_model=1.0)
    model = add('ModelSamplingAuraFlow', model=model, shift=3.1)
    model = add('CFGNorm', model=model, strength=1.0)
    clip = add('CLIPLoader', clip_name='qwen_2.5_vl_7b_fp8_scaled.safetensors', type='qwen_image', device='cpu')
    vae = add('VAELoader', vae_name='qwen_image_vae.safetensors')
    pixels = add('LoadImage', image=reference)
    pixels = add('FluxKontextImageScale', image=pixels)
    positive = add('TextEncodeQwenImageEditPlus', clip=clip, vae=vae, image1=pixels, prompt=prompt)
    negative = add('TextEncodeQwenImageEditPlus', clip=clip, vae=vae, image1=pixels, prompt='')
    positive = add('FluxKontextMultiReferenceLatentMethod', conditioning=positive, reference_latents_method='index_timestep_zero')
    negative = add('FluxKontextMultiReferenceLatentMethod', conditioning=negative, reference_latents_method='index_timestep_zero')
    latent = add('VAEEncode', pixels=pixels, vae=vae)
    latent = add('KSampler', model=model, positive=positive, negative=negative, latent_image=latent,
                 seed=seed, steps=4, cfg=1.0, sampler_name='euler', scheduler='simple', denoise=1.0)
    pixels = add('VAEDecode', samples=latent, vae=vae)
    output = add('SaveImage', images=pixels, filename_prefix=prefix)
    return g, output[0]
