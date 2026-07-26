import sys

sys.settrace(None)
LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())


def ground_shader(name, col_a, col_b, col_c, rough=0.93, gravel=0.35, grain=0.18,
                  voronoi_scale=45.0):
    """Layered dirt shader: broad patches + gravel bump + fine grain."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    out.location, bsdf.location = (400, 0), (100, 0)

    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1500, 0)

    # broad tonal patches
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 1.6
    n1.inputs["Detail"].default_value = 9.0
    n1.inputs["Roughness"].default_value = 0.55
    n1.location = (-1200, 250)
    nt.links.new(coord.outputs["Object"], n1.inputs["Vector"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-950, 250)
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.38, tuple(col_a) + (1.0,)
    e[1].position, e[1].color = 0.62, tuple(col_b) + (1.0,)
    mid = ramp.color_ramp.elements.new(0.50)
    mid.color = tuple(col_c) + (1.0,)
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])

    # fine speckle darkening
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 28.0
    n2.inputs["Detail"].default_value = 12.0
    n2.location = (-1200, -50)
    nt.links.new(coord.outputs["Object"], n2.inputs["Vector"])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.28
    mix.location = (-650, 200)
    nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    nt.links.new(n2.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])

    # roughness breakup
    rmap = nt.nodes.new("ShaderNodeMapRange")
    rmap.inputs["From Min"].default_value = 0.0
    rmap.inputs["From Max"].default_value = 1.0
    rmap.inputs["To Min"].default_value = max(0.0, rough - 0.10)
    rmap.inputs["To Max"].default_value = min(1.0, rough + 0.06)
    rmap.location = (-650, -100)
    nt.links.new(n2.outputs["Fac"], rmap.inputs["Value"])
    nt.links.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.25

    # gravel-scale bump
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "F1"
    vor.inputs["Scale"].default_value = voronoi_scale
    vor.location = (-1200, -350)
    nt.links.new(coord.outputs["Object"], vor.inputs["Vector"])
    b1 = nt.nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = gravel
    b1.inputs["Distance"].default_value = 0.02
    b1.location = (-900, -350)
    nt.links.new(vor.outputs["Distance"], b1.inputs["Height"])

    # fine grain on top
    n3 = nt.nodes.new("ShaderNodeTexNoise")
    n3.inputs["Scale"].default_value = 220.0
    n3.inputs["Detail"].default_value = 10.0
    n3.location = (-900, -600)
    nt.links.new(coord.outputs["Object"], n3.inputs["Vector"])
    b2 = nt.nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = grain
    b2.inputs["Distance"].default_value = 0.006
    b2.location = (-600, -500)
    nt.links.new(n3.outputs["Fac"], b2.inputs["Height"])
    nt.links.new(b1.outputs["Normal"], b2.inputs["Normal"])
    nt.links.new(b2.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# damp packed road bed - darker, greyer, gravelly
ground_shader(
    "Ground.Roadbed",
    col_a=(0.052, 0.043, 0.033),
    col_b=(0.098, 0.082, 0.062),
    col_c=(0.070, 0.058, 0.044),
    rough=0.90, gravel=0.55, grain=0.22, voronoi_scale=55.0,
)
# verge: dustier and a touch warmer, with dry-grass tint
ground_shader(
    "Ground.Dirt",
    col_a=(0.062, 0.053, 0.031),
    col_b=(0.088, 0.082, 0.044),
    col_c=(0.048, 0.046, 0.026),
    rough=0.95, gravel=0.30, grain=0.30, voronoi_scale=30.0,
)
# stones: cooler grey, chipped
ground_shader(
    "Stone.Cobble",
    col_a=(0.055, 0.055, 0.054),
    col_b=(0.105, 0.104, 0.098),
    col_c=(0.078, 0.077, 0.074),
    rough=0.72, gravel=0.22, grain=0.30, voronoi_scale=90.0,
)

scn = bpy.context.scene
sun = bpy.data.objects["SunKey"]
sun.data.energy = 3.0
bpy.data.objects["SkyFill"].data.energy = 360.0
scn.view_settings.look = "AgX - Medium Contrast"

__result__ = {"shaders": ["Ground.Roadbed", "Ground.Dirt", "Stone.Cobble"]}
print(__result__)
