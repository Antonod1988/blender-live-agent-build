"""Stage 2 - scrap materials. Nothing clean, nothing new, nothing matching."""
import bpy


def principled(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    out.location, bsdf.location = (300, 0), (0, 0)
    return m, nt, bsdf


def scrap_metal(name, base, rust, metallic=1.0, rough=0.62, rust_amount=0.55,
                dent=0.45, scale=3.5):
    """Painted or bare plate eaten by rust, with hammered dents in the normal."""
    m, nt, bsdf = principled(name)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    coord.location = (-1300, 0)

    # rust breakup: large blotches multiplied by fine speckle
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = 12.0
    n1.inputs["Roughness"].default_value = 0.62
    n1.location = (-1050, 220)
    nt.links.new(coord.outputs["Object"], n1.inputs["Vector"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-820, 220)
    ramp.color_ramp.interpolation = "EASE"
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.42 + (1.0 - rust_amount) * 0.2, tuple(base) + (1.0,)
    e[1].position, e[1].color = 0.62 + (1.0 - rust_amount) * 0.2, tuple(rust) + (1.0,)
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # rust is dielectric and rough; paint is metal and smoother
    met = nt.nodes.new("ShaderNodeMapRange")
    met.inputs["To Min"].default_value = metallic
    met.inputs["To Max"].default_value = max(0.0, metallic - 0.85)
    met.location = (-560, 60)
    nt.links.new(n1.outputs["Fac"], met.inputs["Value"])
    nt.links.new(met.outputs["Result"], bsdf.inputs["Metallic"])

    rgh = nt.nodes.new("ShaderNodeMapRange")
    rgh.inputs["To Min"].default_value = rough
    rgh.inputs["To Max"].default_value = min(1.0, rough + 0.3)
    rgh.location = (-560, -110)
    nt.links.new(n1.outputs["Fac"], rgh.inputs["Value"])
    nt.links.new(rgh.outputs["Result"], bsdf.inputs["Roughness"])

    # hammered dents, then fine pitting on top
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 14.0
    n2.inputs["Detail"].default_value = 4.0
    n2.location = (-1050, -320)
    nt.links.new(coord.outputs["Object"], n2.inputs["Vector"])
    b1 = nt.nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = dent
    b1.inputs["Distance"].default_value = 0.05
    b1.location = (-760, -320)
    nt.links.new(n2.outputs["Fac"], b1.inputs["Height"])

    n3 = nt.nodes.new("ShaderNodeTexNoise")
    n3.inputs["Scale"].default_value = 190.0
    n3.inputs["Detail"].default_value = 10.0
    n3.location = (-1050, -560)
    nt.links.new(coord.outputs["Object"], n3.inputs["Vector"])
    b2 = nt.nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = 0.30
    b2.inputs["Distance"].default_value = 0.004
    b2.location = (-500, -420)
    nt.links.new(n3.outputs["Fac"], b2.inputs["Height"])
    nt.links.new(b1.outputs["Normal"], b2.inputs["Normal"])
    nt.links.new(b2.outputs["Normal"], bsdf.inputs["Normal"])
    return m


made = []
# they paint it red because red ones go faster. it is not a good paint job.
made.append(scrap_metal("Orc.PaintRed", base=(0.185, 0.017, 0.012),
                        rust=(0.075, 0.030, 0.014), rough=0.52, rust_amount=0.62,
                        dent=0.55, scale=2.6))
made.append(scrap_metal("Orc.PaintYellow", base=(0.30, 0.155, 0.012),
                        rust=(0.085, 0.038, 0.016), rough=0.56, rust_amount=0.55, scale=3.2))
made.append(scrap_metal("Orc.Plate", base=(0.055, 0.052, 0.050),
                        rust=(0.090, 0.038, 0.018), rough=0.66, rust_amount=0.68,
                        dent=0.62, scale=2.2))
made.append(scrap_metal("Orc.Rust", base=(0.098, 0.042, 0.019),
                        rust=(0.055, 0.024, 0.012), rough=0.86, rust_amount=0.80,
                        dent=0.70, scale=5.0))
made.append(scrap_metal("Orc.Brass", base=(0.52, 0.36, 0.13),
                        rust=(0.13, 0.10, 0.045), rough=0.42, rust_amount=0.45, scale=6.0))
made.append(scrap_metal("Orc.Steel", base=(0.28, 0.28, 0.30),
                        rust=(0.10, 0.055, 0.028), rough=0.38, rust_amount=0.35, scale=7.0))
made.append(scrap_metal("Orc.Soot", base=(0.020, 0.019, 0.018),
                        rust=(0.040, 0.030, 0.022), rough=0.92, rust_amount=0.5, scale=4.0))

m, nt, b = principled("Orc.Rubber")
b.inputs["Base Color"].default_value = (0.021, 0.020, 0.020, 1.0)
b.inputs["Roughness"].default_value = 0.78
made.append(m)

m, nt, b = principled("Orc.Leather")
b.inputs["Base Color"].default_value = (0.058, 0.031, 0.017, 1.0)
b.inputs["Roughness"].default_value = 0.72
made.append(m)

m, nt, b = principled("Orc.Bone")
b.inputs["Base Color"].default_value = (0.42, 0.38, 0.29, 1.0)
b.inputs["Roughness"].default_value = 0.58
made.append(m)

m, nt, b = principled("Orc.Glass")
b.inputs["Base Color"].default_value = (0.55, 0.58, 0.52, 1.0)
b.inputs["Roughness"].default_value = 0.22
b.inputs["Transmission Weight"].default_value = 0.85
b.inputs["IOR"].default_value = 1.5
made.append(m)

m, nt, b = principled("Orc.Fire")
b.inputs["Emission Color"].default_value = (1.0, 0.42, 0.10, 1.0)
b.inputs["Emission Strength"].default_value = 12.0
b.inputs["Base Color"].default_value = (0.4, 0.15, 0.05, 1.0)
made.append(m)

m, nt, b = principled("Orc.Ground")
b.inputs["Base Color"].default_value = (0.072, 0.058, 0.040, 1.0)
b.inputs["Roughness"].default_value = 0.95
b.inputs["Specular IOR Level"].default_value = 0.25
made.append(m)

__result__ = {"materials": [x.name for x in made]}
