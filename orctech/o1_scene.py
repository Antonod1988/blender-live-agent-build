"""Stage 1 - a harsh, dusty afternoon over a churned wasteland track."""
import bpy
import math

kit.workspace(r"D:\pythonProject4\blender-live-agent-build\orctech\_out")

with kit.stage("scene") as st:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    scn = bpy.context.scene

    # world: dirty ochre sky, sun low enough to rake the plating
    world = bpy.data.worlds.get("OrcSky") or bpy.data.worlds.new("OrcSky")
    scn.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(19.0)
    sky.sun_rotation = math.radians(118.0)
    sky.sun_intensity = 0.5
    sky.air_density = 0.9
    sky.dust_density = 5.5          # grit in the air, not romance
    sky.ozone_density = 0.6
    bg.inputs["Strength"].default_value = 0.62
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    sky.location, bg.location, out.location = (-500, 0), (-200, 0), (60, 0)

    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 6.0
    sun_d.angle = math.radians(2.4)
    sun_d.color = (1.0, 0.86, 0.66)
    sun = bpy.data.objects.new("Sun", sun_d)
    sun.rotation_euler = (math.radians(62.0), 0.0, math.radians(210.0))
    bpy.context.scene.collection.objects.link(sun)

    fill_d = bpy.data.lights.new("Fill", "AREA")
    fill_d.energy = 260.0
    fill_d.size = 14.0
    fill_d.color = (0.58, 0.68, 0.95)
    fill = bpy.data.objects.new("Fill", fill_d)
    fill.location = (8.0, -9.0, 6.0)
    fill.rotation_euler = (math.radians(56.0), 0.0, math.radians(42.0))
    bpy.context.scene.collection.objects.link(fill)

    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 44.0
    cam_d.dof.use_dof = True
    cam_d.dof.aperture_fstop = 4.0
    cam = bpy.data.objects.new("Cam", cam_d)
    cam.location = (9.6, -7.2, 2.3)
    bpy.context.scene.collection.objects.link(cam)

    tgt = bpy.data.objects.new("CamTarget", None)
    tgt.empty_display_type = "SPHERE"
    tgt.empty_display_size = 0.2
    tgt.location = (0.0, 0.0, 1.3)
    bpy.context.scene.collection.objects.link(tgt)
    trk = cam.constraints.new("TRACK_TO")
    trk.target = tgt
    trk.track_axis = "TRACK_NEGATIVE_Z"
    trk.up_axis = "UP_Y"
    cam_d.dof.focus_object = tgt
    scn.camera = cam

    scn.render.engine = "BLENDER_EEVEE_NEXT"
    scn.render.resolution_x, scn.render.resolution_y = 1920, 1080
    for attr, val in (("taa_render_samples", 96), ("use_raytracing", True),
                      ("use_shadows", True)):
        try:
            setattr(scn.eevee, attr, val)
        except (AttributeError, TypeError):
            pass
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.shading.type = "MATERIAL"
            sp.shading.use_scene_world = False
            sp.shading.use_scene_lights = False
            sp.clip_end = 500.0
            sp.region_3d.view_perspective = "CAMERA"

__result__ = {"stage": st.report(), "summary": kit.summary()}
