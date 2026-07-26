LIB = r"C:\path\to\blender-live-agent-build\scripts\lib.py"
exec(open(LIB, encoding="utf-8").read(), globals())

made = []


def M(*a, **kw):
    m = mat(*a, **kw)
    made.append(m.name)
    return m


# ---- coachwork -------------------------------------------------------------
lacquer = M("Lacquer.Burgundy", base=(0.115, 0.014, 0.028), metallic=0.0, rough=0.13,
            spec=0.6, coat=1.0)
add_noise_bump(lacquer, scale=180.0, detail=6.0, strength=0.05)

M("Lacquer.Black", base=(0.018, 0.016, 0.020), rough=0.11, coat=1.0, spec=0.6)

panel = M("Panel.Inlay", base=(0.055, 0.020, 0.030), rough=0.22, coat=0.7)
add_noise_bump(panel, scale=90.0, detail=8.0, strength=0.10)

# ---- metals ----------------------------------------------------------------
gold = M("Gold.Ornament", base=(1.0, 0.735, 0.28), metallic=1.0, rough=0.18)
add_noise_bump(gold, scale=260.0, detail=6.0, strength=0.06)

M("Gold.Dark", base=(0.62, 0.44, 0.16), metallic=1.0, rough=0.34)

brass = M("Brass.Fittings", base=(0.85, 0.63, 0.28), metallic=1.0, rough=0.28)
add_noise_bump(brass, scale=180.0, detail=6.0, strength=0.09)

iron = M("Iron.Black", base=(0.030, 0.029, 0.032), metallic=1.0, rough=0.44)
add_noise_bump(iron, scale=120.0, detail=8.0, strength=0.18)

tire = M("Iron.Tyre", base=(0.052, 0.048, 0.046), metallic=1.0, rough=0.55)
add_noise_bump(tire, scale=70.0, detail=9.0, strength=0.30)

steel = M("Steel.Spring", base=(0.16, 0.16, 0.17), metallic=1.0, rough=0.30)
M("Silver.Trim", base=(0.86, 0.88, 0.92), metallic=1.0, rough=0.20)

# ---- timber ----------------------------------------------------------------
oak = M("Wood.Oak", base=(0.24, 0.135, 0.062), rough=0.46, spec=0.4)
add_color_variation(oak, (0.235, 0.128, 0.058), (0.135, 0.070, 0.032), scale=3.0, detail=9.0)
add_noise_bump(oak, scale=45.0, detail=10.0, strength=0.22, distortion=1.6)

ebony = M("Wood.Ebony", base=(0.048, 0.030, 0.024), rough=0.36)
add_noise_bump(ebony, scale=60.0, detail=9.0, strength=0.15, distortion=1.2)

# ---- soft goods ------------------------------------------------------------
leather = M("Leather.Black", base=(0.035, 0.031, 0.030), rough=0.52, spec=0.45, sheen=0.15)
add_noise_bump(leather, scale=260.0, detail=10.0, strength=0.35, distortion=0.8)

M("Leather.Tan", base=(0.16, 0.085, 0.042), rough=0.58, sheen=0.10)

velvet = M("Velvet.Crimson", base=(0.24, 0.020, 0.045), rough=0.85, sheen=0.9)
add_noise_bump(velvet, scale=320.0, detail=6.0, strength=0.12)

M("Rope.Hemp", base=(0.30, 0.235, 0.135), rough=0.85)
M("Cloth.Canvas", base=(0.26, 0.225, 0.175), rough=0.80, sheen=0.3)

# ---- glass & light ---------------------------------------------------------
M("Glass.Window", base=(0.86, 0.90, 0.94), rough=0.03, transmission=1.0, ior=1.48,
  alpha=0.12, metallic=0.0)
M("Glass.Lantern", base=(1.0, 0.94, 0.82), rough=0.10, transmission=1.0, ior=1.46,
  alpha=0.22)
M("Flame.Core", base=(1.0, 0.62, 0.22), emission=(1.0, 0.56, 0.18), emission_strength=95.0,
  rough=1.0)
M("Crystal.Arcane", base=(0.25, 0.55, 1.0), emission=(0.30, 0.62, 1.0), emission_strength=14.0,
  rough=0.08, transmission=0.85, ior=1.7, alpha=0.55)

# ---- ground ----------------------------------------------------------------
dirt = M("Ground.Dirt", base=(0.115, 0.086, 0.058), rough=0.92, spec=0.2)
add_color_variation(dirt, (0.135, 0.100, 0.066), (0.062, 0.046, 0.032), scale=6.0, detail=12.0)
add_noise_bump(dirt, scale=28.0, detail=14.0, strength=0.55, distortion=1.4)

roadbed = M("Ground.Roadbed", base=(0.155, 0.128, 0.098), rough=0.95, spec=0.2)
add_color_variation(roadbed, (0.175, 0.145, 0.112), (0.085, 0.068, 0.052), scale=14.0, detail=12.0)
add_noise_bump(roadbed, scale=55.0, detail=14.0, strength=0.65, distortion=1.8)

cobble = M("Stone.Cobble", base=(0.105, 0.104, 0.100), rough=0.72, spec=0.35)
add_color_variation(cobble, (0.125, 0.122, 0.115), (0.058, 0.058, 0.060), scale=20.0, detail=8.0)
add_noise_bump(cobble, scale=90.0, detail=10.0, strength=0.40)

boulder = M("Stone.Boulder", base=(0.088, 0.086, 0.082), rough=0.80)
add_noise_bump(boulder, scale=25.0, detail=12.0, strength=0.55, distortion=1.5)

grass = M("Plant.Grass", base=(0.058, 0.098, 0.028), rough=0.62, sheen=0.4,
          transmission=0.10)
add_color_variation(grass, (0.070, 0.115, 0.030), (0.115, 0.105, 0.038), scale=2.5, detail=6.0)

M("Plant.Bark", base=(0.062, 0.048, 0.036), rough=0.85)
add_noise_bump(bpy.data.materials["Plant.Bark"], scale=40.0, detail=12.0, strength=0.6,
               distortion=2.0)
M("Plant.Foliage", base=(0.045, 0.078, 0.032), rough=0.70, transmission=0.12, sheen=0.3)

M("Water.Puddle", base=(0.045, 0.048, 0.042), rough=0.045, spec=0.9, ior=1.33)

__result__ = {"materials": len(made), "names": made}
print(__result__)
