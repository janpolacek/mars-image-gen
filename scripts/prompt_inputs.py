"""Compose visible prompts from the manifest, leaving background lore out."""

def style(config, scene=False):
    if scene:
        return '\n\n'.join([config['photo_style'], config['planet']['visual_description'], config['scene_style']])
    return '\n\n'.join([config['photo_style'], config['reference_style']])

def canonical(config, vehicle):
    parts = [config['reference_camera'], vehicle.get('reference_pose', '')]
    if vehicle.get('assets'):
        parts.append('Use supplied images only for these design details: ' + '; '.join(a['instruction'] for a in vehicle['assets']))
    return '\n'.join(p for p in parts if p)

def angle(camera, vehicle=None):
    # This LoRA expects its trained camera vocabulary, not the FLUX identity/style prose.
    views = ['front view', 'front-right quarter view', 'right side view', 'back-right quarter view',
             'back view', 'back-left quarter view', 'left side view', 'front-left quarter view']
    elevations = ['low-angle shot', 'eye-level shot', 'elevated shot', 'high-angle shot']
    distances = ['close-up', 'medium shot', 'wide shot']
    valid = {f'{v} {e} {d}' for v in views for e in elevations for d in distances}
    if camera not in valid:
        raise ValueError('Unsupported Qwen camera descriptor: '+camera)
    return '<sks> '+camera

def scene(description):
    return ('The reference images show the same vehicle on a studio background. Use them for vehicle identity only. '
            'Apply the requested action and weathering without redesigning the vehicle.\n' + description)
