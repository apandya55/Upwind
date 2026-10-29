"""Build UPWIND's lightweight accordion map asset with Blender.

Run from the repository root:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/create_unfolding_map.py

Outputs a source .blend, an animated glTF for the browser, and a poster render.
The texture is project-generated orientation artwork; it does not encode data.
"""
from __future__ import annotations
import math
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "frontend/public/landing/unfolding-map"
ASSET.mkdir(parents=True, exist_ok=True)
TEXTURE = ASSET / "panel-{index}.png"

# Clean scene while retaining no user data in the generated source.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1200
scene.render.resolution_y = 760
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(ASSET / "unfolding-map-poster.png")
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("Atlas World")
scene.world.color = (0.94, 0.95, 0.94)
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.96, 0.97, 0.96, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.1

# Materials with separate crops keep the geography continuous across seams.
def panel_material(index: int):
    mat = bpy.data.materials.new(f"Map panel {index + 1}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Roughness"].default_value = 0.82
    shader.inputs["Specular IOR Level"].default_value = 0.25
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(TEXTURE).format(index=index), check_existing=True)
    tex.interpolation = "Linear"
    texcoord = nodes.new("ShaderNodeTexCoord")
    # glTF exports UV coordinates; Blender's Generated coordinates are not a
    # portable glTF attribute and silently produce flat-color browser panels.
    links.new(texcoord.outputs["UV"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat

# Root hierarchy: each hinge is a child of the previous hinge so folds move as
# one connected accordion rather than as four independent cards.
width, height = 1.2, 2.4
root = bpy.data.objects.new("AccordionMap", None)
scene.collection.objects.link(root)
root.location = (-2.4, 0.0, 0.0)

hinges = []
panels = []
for index in range(4):
    hinge = bpy.data.objects.new(f"Hinge_{index + 1}", None)
    scene.collection.objects.link(hinge)
    hinge.parent = root if index == 0 else hinges[index - 1]
    hinge.location = (0.0 if index == 0 else width, 0.0, 0.0)
    hinges.append(hinge)

    mesh = bpy.data.meshes.new(f"Panel_{index + 1}_Mesh")
    verts = [(0, -height / 2, 0), (width, -height / 2, 0), (width, height / 2, 0), (0, height / 2, 0)]
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.polygons[0].loop_indices:
        uv_layer.data[loop].uv = ((0, 0), (1, 0), (1, 1), (0, 1))[mesh.loops[loop].vertex_index]
    panel = bpy.data.objects.new(f"MapPanel_{index + 1}", mesh)
    scene.collection.objects.link(panel)
    panel.parent = hinge
    panel.location = (0, 0, 0.035)
    panel.data.materials.append(panel_material(index))
    solid = panel.modifiers.new("Paper thickness", "SOLIDIFY")
    solid.thickness = 0.055
    bevel = panel.modifiers.new("Soft paper edge", "BEVEL")
    bevel.width = 0.025
    bevel.segments = 2
    panels.append(panel)

# Physical accordion pose at time 0, then a clean flat map at time 96.
folds = [0.0, math.radians(-28), math.radians(28), math.radians(-28)]
for index, hinge in enumerate(hinges):
    hinge.rotation_mode = "XYZ"
    hinge.rotation_euler[1] = folds[index]
    hinge.keyframe_insert(data_path="rotation_euler", index=1, frame=1)
    hinge.rotation_euler[1] = 0.0
    hinge.keyframe_insert(data_path="rotation_euler", index=1, frame=96)
    # Hold the final state for a stable handoff.
    hinge.keyframe_insert(data_path="rotation_euler", index=1, frame=144)

# A small marker on the illustrative Durham area. It is deliberately a visual
# anchor only; the HTML copy states that the texture is not a data layer.
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.07, depth=0.07, location=(3.43, -0.16, 0.16))
marker = bpy.context.object
marker.name = "Illustrative_Durham_Anchor"
marker.parent = root
marker.data.materials.append(panel_material(2))

# Ground for the poster only; hidden from exported glTF.
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.12))
ground = bpy.context.object
ground.name = "PosterGround"
gmat = bpy.data.materials.new("Poster ground")
gmat.diffuse_color = (0.94, 0.95, 0.92, 1)
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.94, 0.95, 0.92, 1)
gmat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
ground.data.materials.append(gmat)

# Soft three-quarter poster camera.
bpy.ops.object.camera_add(location=(0.5, -1.2, 9.0))
cam = bpy.context.object
cam.name = "PosterCamera"
scene.camera = cam
def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
point_at(cam, (0.0, 0.0, 0.0))
cam.data.lens = 42

bpy.ops.object.light_add(type="AREA", location=(1.5, -2.5, 6.5))
key = bpy.context.object
key.name = "Soft directional key"
key.data.energy = 260
key.data.shape = "DISK"
key.data.size = 5.0
point_at(key, (0, 0, 0))
bpy.ops.object.light_add(type="AREA", location=(-4, 2, 3.0))
fill = bpy.context.object
fill.data.energy = 110
fill.data.size = 4.0
point_at(fill, (0, 0, 0.2))

# Render poster before hiding ground and lights from runtime export.
scene.frame_set(1)
bpy.ops.render.render(write_still=True)

for obj in [ground, cam, key, fill]:
    obj.hide_render = True
    obj.hide_viewport = True
# Export only the animated map hierarchy, with embedded panel textures.
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET / "unfolding-map.blend"))
for obj in list(scene.objects):
    obj.select_set(obj.name.startswith("AccordionMap") or obj.name.startswith("Hinge_") or obj.name.startswith("MapPanel_") or obj.name.startswith("Evidence_") or obj.name.startswith("Illustrative_"))
bpy.ops.object.select_all(action="DESELECT")
for obj in scene.objects:
    if obj.name.startswith(("AccordionMap", "Hinge_", "MapPanel_", "Illustrative_")):
        obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.gltf(filepath=str(ASSET / "unfolding-map.glb"), export_format="GLB", export_animations=True, export_image_format="AUTO", use_selection=True)
print("Created", ASSET / "unfolding-map.blend")
print("Created", ASSET / "unfolding-map.glb")
print("Created", ASSET / "unfolding-map-poster.png")
