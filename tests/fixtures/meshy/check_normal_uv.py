"""Inspect real saved/imported normal data; offline bpy probes, not mocks."""

import argparse
import json
import sys
from pathlib import Path

import bpy


def snapshot():
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    material = bpy.data.materials["FixtureMaterial"]
    shader = material.node_tree.nodes.get("Principled BSDF")
    normal = shader.inputs["Normal"].links[0].from_node
    texture = normal.inputs["Color"].links[0].from_node
    return {
        "normal": {
            "uv_map": normal.uv_map,
            "space": normal.space,
            "strength": normal.inputs["Strength"].default_value,
            "strength_linked": normal.inputs["Strength"].is_linked,
            "vector_linked": texture.inputs["Vector"].is_linked,
            "image_space": texture.image.colorspace_settings.name,
            "image_packed": bool(texture.image.packed_file),
            "image_size": list(texture.image.size),
            "pixels": list(texture.image.pixels),
        },
        "shared_material": all(list(o.data.materials) == [material] for o in meshes),
        "meshes": {
            o.name: {
                "parent": o.parent.name if o.parent else None,
                "active_uv": o.data.uv_layers.active.name,
                "uvs": [
                    {
                        "name": uv.name,
                        "render": uv.active_render,
                        "coords": [c for point in uv.data for c in point.uv],
                    }
                    for uv in o.data.uv_layers
                ],
            }
            for o in meshes
        },
    }


def inspect(source, normal_image):
    saved = snapshot()
    image = bpy.data.images.load(str(normal_image))
    image.colorspace_settings.name = "Non-Color"
    pixels = list(image.pixels)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    return {"saved": saved, "original": snapshot(), "exported_pixels": pixels}


def safety(case):
    # Mesh datablocks and real node links model material bindings without mocks.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from meshy_blender import Rejected, adapt_material

    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = bpy.data.materials.new("SafetyMaterial")
    if bpy.app.version < (5, 0, 0):
        material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    image = bpy.data.images.new("SafetyNormal", width=2, height=2, alpha=True)
    image.colorspace_settings.name = "Non-Color"
    image.pixels[:] = [
        0.25,
        0.5,
        1,
        1,
        0.5,
        0.75,
        1,
        1,
        0.75,
        0.25,
        1,
        1,
        0.5,
        0.5,
        1,
        1,
    ]
    image.pack()
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.65
    normal.space = "TANGENT"
    normal.uv_map = "PaintedUV"
    links.new(texture.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    layers = [("PaintedUV",)]
    if case == "mismatch":
        layers = [("DifferentUV",)]
    elif case in {"multiple_named", "empty_multiple", "legacy_empty_multiple"}:
        layers = [("PaintedUV", "OtherUV")]
    elif case == "unknown_named":
        layers = []
    elif case == "no_uv":
        layers = [()]
    elif case == "shared_mismatch_late":
        layers = [("PaintedUV",), ("DifferentUV",)]
    elif case == "shared_mismatch_early":
        layers = [("DifferentUV",), ("PaintedUV",)]
    elif case == "shared_match":
        layers = [("PaintedUV",), ("PaintedUV",)]
    elif case == "shared_empty_distinct":
        layers = [("PaintedUV",), ("DifferentUV",)]
    if case == "fake_user":
        material.use_fake_user = True
    graph_cases = {
        "object_space",
        "linked_strength",
        "missing_color",
        "alpha_output",
        "indirect_image",
        "linked_vector",
        "non_flat",
        "non_repeat",
        "non_linear",
        "srgb_normal",
    }
    if case in graph_cases or case in {
        "empty_single",
        "empty_multiple",
        "shared_empty_distinct",
        "legacy_empty",
        "legacy_empty_multiple",
    }:
        normal.uv_map = ""
    if case == "object_space":
        normal.space = "OBJECT"
    elif case == "linked_strength":
        value = nodes.new("ShaderNodeValue")
        links.new(value.outputs[0], normal.inputs["Strength"])
    elif case == "missing_color":
        links.remove(normal.inputs["Color"].links[0])
    elif case == "alpha_output":
        links.new(texture.outputs["Alpha"], normal.inputs["Color"])
    elif case == "indirect_image":
        rgb = nodes.new("ShaderNodeRGB")
        links.new(rgb.outputs[0], normal.inputs["Color"])
    elif case in {"linked_vector", "named_linked_vector"}:
        uv = nodes.new("ShaderNodeUVMap")
        links.new(uv.outputs["UV"], texture.inputs["Vector"])
    elif case == "non_flat":
        texture.projection = "BOX"
    elif case == "non_repeat":
        texture.extension = "EXTEND"
    elif case == "non_linear":
        texture.interpolation = "Closest"
    elif case in {"srgb_normal", "named_srgb_normal"}:
        image.colorspace_settings.name = "sRGB"
    users = []
    for index, names in enumerate(layers):
        mesh = bpy.data.meshes.new(f"User{index}")
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        mesh.materials.append(material)
        for name in names:
            layer = mesh.uv_layers.new(name=name)
            for point, coord in zip(
                layer.data, [(0.1, 0.2), (0.9, 0.2), (0.1, 0.8)], strict=True
            ):
                point.uv = coord
        if names:
            mesh.uv_layers.active_index = 0
        users.append(mesh)

    def state():
        return {
            "uv_map": normal.uv_map,
            "strength": normal.inputs["Strength"].default_value,
            "pixels": list(image.pixels),
            "uvs": [
                [list(point.uv) for layer in m.uv_layers for point in layer.data]
                for m in users
            ],
        }

    before = state()
    reason, label = None, None
    try:
        if case.startswith("legacy_"):
            adapt_material(material, {}, {})
        else:
            adapt_material(material, {}, {}, mesh_users=users)
    except Rejected as error:
        reason, label = error.reason, error.name
    return {
        "accepted": reason is None,
        "reason": reason,
        "material": label,
        "before": before,
        "after": state(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--normal-image", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    result = safety(args.case) if args.case else inspect(args.source, args.normal_image)
    args.output.write_text(json.dumps(result))
