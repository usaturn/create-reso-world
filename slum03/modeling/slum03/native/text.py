"""Fixed parent-local labels, never below an AR driven mesh."""
from modeling.slum03.types import Layout
from .common import add_child, node, slot_key_by_name, walk, yaw


def add_labels(manifest: dict, layout: Layout) -> None:
    for label in layout.labels:
        parent_key = slot_key_by_name(manifest, label.parent_name)
        parent = next(n for n in walk(manifest) if n['slot']['key'] == parent_key)
        child = node(f'label-{label.key}', f'Slum03 label {label.key}', label.offset,
                     yaw(label.yaw_deg))
        child['slot']['parent'] = f'$slot:{parent_key}'
        child['components'].append({'key': f'label-{label.key}-text',
                                    'type': 'FrooxEngine.TextRenderer',
                                    'fields': {'Text': label.text, 'Size': label.height,
                                               'Color': list(label.color),
                                               'HorizontalAlign': 'Center',
                                               'VerticalAlign': 'Middle'}})
        add_child(parent, child)
