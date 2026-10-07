"""Generate tiny real GLBs with Blender; never download assets or call Meshy."""

import argparse
import sys
from pathlib import Path

import bpy


def create(output, case):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = bpy.data.materials.new("FixtureMaterial")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    albedo = bpy.data.images.new("AsymmetricAlbedo", width=2, height=2, alpha=True)
    albedo.colorspace_settings.name = "sRGB"
    albedo.pixels[:] = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1]
    albedo.pack()
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = albedo
    material.node_tree.links.new(node.outputs["Color"], shader.inputs["Base Color"])
    mr = bpy.data.images.new("PackedMR", width=2, height=2, alpha=True)
    mr.colorspace_settings.name = "Non-Color"
    mr.pixels[:] = [0.1, 0.25, 0.75, 1] * 4
    mr.pack()
    mr_node = material.node_tree.nodes.new("ShaderNodeTexImage")
    mr_node.image = mr
    separate = material.node_tree.nodes.new("ShaderNodeSeparateColor")
    material.node_tree.links.new(mr_node.outputs["Color"], separate.inputs["Color"])
    material.node_tree.links.new(separate.outputs["Blue"], shader.inputs["Metallic"])
    material.node_tree.links.new(separate.outputs["Green"], shader.inputs["Roughness"])
    if case == "transparency":
        shader.inputs["Alpha"].default_value = 0.5
        material.surface_render_method = "DITHERED"
    if case == "transmission":
        shader.inputs["Transmission Weight"].default_value = 0.6
    parent = bpy.data.objects.new("FixtureHierarchy", None)
    bpy.context.collection.objects.link(parent)
    parent.location = (2, -1, 0.5)
    for name, location in (("LowerPart", (1, 0, 2)), ("UpperPart", (3, 0, 4))):
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object
        obj.name = name
        obj.parent = parent
        obj.location = location
        obj.data.materials.append(material)
        if case == "animation":
            obj.keyframe_insert(data_path="location", frame=1)
            obj.location.x += 1
            obj.keyframe_insert(data_path="location", frame=10)
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", default="opaque")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    create(args.output, args.case)
