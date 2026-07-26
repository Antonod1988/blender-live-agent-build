LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

scn = bpy.context.scene

# --- wipe the default scene -------------------------------------------------
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

C_CARRIAGE = get_coll("Carriage")
C_WHEELS = get_coll("Wheels", C_CARRIAGE)
C_BODY = get_coll("Body", C_CARRIAGE)
C_GEAR = get_coll("Undercarriage", C_CARRIAGE)
C_DETAIL = get_coll("Details", C_CARRIAGE)
C_ROAD = get_coll("Road")
C_ENV = get_coll("Environment")
C_LIGHT = get_coll("Lighting")

# --- world: dusk sky + haze -------------------------------------------------
world = bpy.data.worlds.get("FantasyDusk") or bpy.data.worlds.new("FantasyDusk")
scn.world = world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld")
bg = nt.nodes.new("ShaderNodeBackground")
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(6.5)
sky.sun_rotation = math.radians(205.0)
sky.sun_intensity = 0.35
sky.altitude = 250.0
sky.air_density = 1.9
sky.dust_density = 4.2
sky.ozone_density = 1.4
bg.inputs["Strength"].default_value = 1.0
nt.links.new(sky.outputs[0], bg.inputs[0])
nt.links.new(bg.outputs[0], out.inputs[0])

# volumetric haze so the low sun rakes through the scene
vol = nt.nodes.new("ShaderNodeVolumeScatter")
vol.inputs["Color"].default_value = (0.85, 0.78, 0.70, 1.0)
vol.inputs["Density"].default_value = 0.0045
vol.inputs["Anisotropy"].default_value = 0.55
nt.links.new(vol.outputs[0], out.inputs["Volume"])
sky.location, bg.location, out.location, vol.location = (-500, 200), (-200, 200), (100, 100), (-200, -150)

# --- key light: low golden sun ---------------------------------------------
sun_data = bpy.data.lights.new("SunKey", "SUN")
sun_data.energy = 5.2
sun_data.angle = math.radians(1.6)
sun_data.color = (1.0, 0.80, 0.55)
sun = bpy.data.objects.new("SunKey", sun_data)
sun.rotation_euler = (math.radians(76.0), 0.0, math.radians(38.0))
sun.location = (-14.0, 10.0, 9.0)
link(sun, C_LIGHT)

# cool bounce from the opposite side so shadows keep detail
fill_data = bpy.data.lights.new("SkyFill", "AREA")
fill_data.energy = 260.0
fill_data.size = 9.0
fill_data.color = (0.55, 0.68, 1.0)
fill = bpy.data.objects.new("SkyFill", fill_data)
fill.location = (6.0, -9.0, 6.5)
fill.rotation_euler = (math.radians(52.0), 0.0, math.radians(28.0))
link(fill, C_LIGHT)

# --- camera: 3/4 hero angle from the roadside ------------------------------
cam_data = bpy.data.cameras.new("HeroCam")
cam_data.lens = 52.0
cam_data.sensor_width = 36.0
cam_data.dof.use_dof = True
cam_data.dof.aperture_fstop = 3.2
cam = bpy.data.objects.new("HeroCam", cam_data)
cam.location = (7.4, -6.6, 2.35)
link(cam, C_LIGHT)

target = empty("CamTarget", (0.15, 0.0, 1.30), C_LIGHT, kind="SPHERE", size=0.2)
trk = cam.constraints.new("TRACK_TO")
trk.target = target
trk.track_axis = "TRACK_NEGATIVE_Z"
trk.up_axis = "UP_Y"
cam_data.dof.focus_object = target
scn.camera = cam

# --- render settings --------------------------------------------------------
scn.render.engine = "BLENDER_EEVEE_NEXT"
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.render.film_transparent = False
ee = scn.eevee
for attr, value in (
    ("taa_render_samples", 96),
    ("taa_samples", 12),
    ("use_raytracing", True),
    ("use_shadows", True),
    ("use_volumetric_lights", True),
    ("volumetric_start", 0.2),
    ("volumetric_end", 120.0),
    ("volumetric_tile_size", "4"),
    ("use_bloom", True),
    ("shadow_ray_count", 2),
    ("shadow_step_count", 6),
):
    try:
        setattr(ee, attr, value)
    except (AttributeError, TypeError):
        pass
try:
    ee.ray_tracing_options.use_denoise = True
    ee.ray_tracing_options.resolution_scale = "1"
except (AttributeError, TypeError):
    pass

scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Medium High Contrast"
scn.render.image_settings.file_format = "PNG"

# --- viewport: look through the hero camera, material preview ---------------
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.shading.type = "MATERIAL"
        space.shading.use_scene_world = False
        space.shading.use_scene_lights = False
        space.overlay.show_floor = True
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
        space.clip_end = 500.0
        space.region_3d.view_perspective = "CAMERA"
        space.lens = 40

__result__ = {
    "collections": [c.name for c in bpy.data.collections],
    "camera": cam.name,
    "engine": scn.render.engine,
}
print(__result__)
