"""Build API and editable graphs from the same node definitions."""
import json


def build(identity, instruction, style, references, prefix, seed=410101, scene=False):
    graph = {}
    def add(kind, title=None, **inputs):
        key = str(len(graph) + 1)
        graph[key] = {'class_type': kind, 'inputs': inputs, '_meta': {'title': title or kind}}
        return [key, 0]
    # These are the current public Flux.2 Klein weights; the former 9B/8B
    # filenames were never published by the model provider.
    model = add('UNETLoader', unet_name='flux-2-klein-base-4b.safetensors', weight_dtype='default')
    clip = add('CLIPLoader', clip_name='qwen_3_4b.safetensors', type='flux2', device='cpu')
    vae = add('VAELoader', vae_name='flux2-vae.safetensors')
    a = add('PrimitiveStringMultiline', 'Vehicle description', value=identity)
    b = add('PrimitiveStringMultiline', 'Scene description' if scene else 'Camera / reference instructions', value=instruction)
    c = add('PrimitiveStringMultiline', 'Shared realism and photography', value=style)
    # Put the edit/camera task first; identity describes what is being edited.
    ab = add('StringConcatenate', string_a=b, string_b=a, delimiter='\n\n')
    text = add('StringConcatenate', string_a=ab, string_b=c, delimiter='\n\n')
    positive = add('CLIPTextEncode', clip=clip, text=text)
    # Base is not guidance-distilled: encode an empty negative prompt for CFG.
    negative = add('CLIPTextEncode', 'Empty negative prompt (Base CFG)', clip=clip, text='')
    for path in references:
        pixels = add('LoadImage', 'Reference: ' + path, image=path)
        pixels = add('ImageScaleToTotalPixels', image=pixels, upscale_method='lanczos', megapixels=0.6, resolution_steps=1)
        latent = add('VAEEncode', pixels=pixels, vae=vae)
        positive = add('ReferenceLatent', conditioning=positive, latent=latent)
        negative = add('ReferenceLatent', conditioning=negative, latent=latent)
    width, height = (1344, 768) if scene else (1152, 864)
    latent = add('EmptyFlux2LatentImage', width=width, height=height, batch_size=1)
    noise = add('RandomNoise', noise_seed=seed)
    guider = add('CFGGuider', model=model, positive=positive, negative=negative, cfg=5.0)
    sampler = add('KSamplerSelect', sampler_name='euler')
    sigmas = add('Flux2Scheduler', steps=20, width=width, height=height)
    samples = add('SamplerCustomAdvanced', noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=latent)
    pixels = add('VAEDecode', samples=samples, vae=vae)
    output = add('SaveImage', images=pixels, filename_prefix=prefix)
    return graph, output[0]


def ui_graph(graph, schema):
    nodes, links = [], []
    for key, spec in graph.items():
        definition = schema[spec['class_type']]
        inputs, widgets = [], []
        for name, value in spec['inputs'].items():
            slot = len(inputs)
            if isinstance(value, list):
                source, output = value
                kind = schema[graph[source]['class_type']]['output'][output]
                link = len(links) + 1
                links.append([link, int(source), output, int(key), slot, kind])
                inputs.append({'name': name, 'type': kind, 'link': link})
            else:
                desc = definition['input'].get('required', {}).get(name, definition['input'].get('optional', {}).get(name))
                kind = 'COMBO' if isinstance(desc[0], list) else desc[0]
                inputs.append({'name': name, 'type': kind, 'widget': {'name': name}, 'link': None})
                widgets.append(value)
                if spec['class_type'] == 'RandomNoise' or (spec['class_type'] == 'KSampler' and name == 'seed'):
                    widgets.append('fixed')
        if spec['class_type'] == 'LoadImage':
            widgets.append('image')
        i = int(key)-1
        nodes.append({'id': int(key), 'type': spec['class_type'], 'title': spec['_meta']['title'],
                      'pos': [(i//5)*470, (i%5)*340], 'size': [420, 300], 'flags': {}, 'order': i, 'mode': 0,
                      'inputs': inputs, 'outputs': [{'name': name, 'type': kind, 'links': []} for name, kind in zip(definition['output_name'], definition['output'])],
                      'properties': {'Node name for S&R': spec['class_type']}, 'widgets_values': widgets})
    by_id = {node['id']: node for node in nodes}
    for link, source, slot, *_ in links:
        by_id[source]['outputs'][slot]['links'].append(link)
    return {'version': 0.4, 'last_node_id': len(nodes), 'last_link_id': len(links), 'nodes': nodes, 'links': links, 'groups': [], 'config': {}, 'extra': {}}
