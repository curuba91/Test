#!/usr/bin/env python3
"""
Personalisierter Stiftehalter mit Name.
Erzeugt eine STL- und 3MF-Datei eines Stiftehalters (abgerundeter Becher)
mit erhaben aufgesetztem Namen auf der Vorderseite.

Inspiriert von "Personalized Pen Holders with Name" (MakerWorld).
Parametrisch - Name und Maße frei einstellbar.
"""
import numpy as np
import trimesh
from trimesh.creation import extrude_polygon
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

# ----------------------------------------------------------------------
# Parameter
# ----------------------------------------------------------------------
NAME            = "Joris"
WIDTH           = 80.0     # Breite (X) in mm
DEPTH           = 70.0     # Tiefe  (Y) in mm
HEIGHT          = 95.0     # Hoehe  (Z) in mm
WALL            = 3.0      # Wandstaerke in mm
FLOOR           = 3.0      # Bodenstaerke in mm
CORNER_R        = 12.0     # Eckenradius in mm
LETTER_HEIGHT   = 24.0     # Buchstabenhoehe in mm
EMBOSS          = 1.8      # Wie weit der Name heraussteht in mm
FONT_PATH       = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SEG             = 64       # Segmente fuer runde Ecken

# ----------------------------------------------------------------------
# 1) Koerper: abgerundetes Rechteck (Stadium/Squircle) als Becher
# ----------------------------------------------------------------------
def rounded_rect(w, d, r, seg=SEG):
    """Abgerundetes Rechteck zentriert um den Ursprung -> shapely Polygon."""
    r = min(r, w / 2.0, d / 2.0)
    hx, hy = w / 2.0 - r, d / 2.0 - r
    pts = []
    # vier Eckmittelpunkte mit jeweiligem Bogen
    corners = [( hx,  hy, 0),
               (-hx,  hy, 90),
               (-hx, -hy, 180),
               ( hx, -hy, 270)]
    for cx, cy, a0 in corners:
        for i in range(seg // 4 + 1):
            a = np.radians(a0 + 90.0 * i / (seg // 4))
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    return Polygon(pts)

outer_poly = rounded_rect(WIDTH, DEPTH, CORNER_R)
inner_poly = rounded_rect(WIDTH - 2 * WALL, DEPTH - 2 * WALL, max(CORNER_R - WALL, 1.0))

# Aussenkoerper voll, Innenkoerper als Aushoehlung (ab Bodenhoehe)
outer = extrude_polygon(outer_poly, HEIGHT)
inner = extrude_polygon(inner_poly, HEIGHT)       # bis ganz oben offen
inner.apply_translation([0, 0, FLOOR])            # Boden stehen lassen

body = outer.difference(inner)

# ----------------------------------------------------------------------
# 2) Name als erhabene Geometrie (even-odd Fuellung fuer Loecher in o,a,..)
# ----------------------------------------------------------------------
def text_polygon(text, font_path):
    fp = FontProperties(fname=font_path)
    tp = TextPath((0, 0), text, size=100, prop=fp)
    rings = [Polygon(p) for p in tp.to_polygons() if len(p) >= 3 and Polygon(p).is_valid]
    # even-odd Regel: symmetrische Differenz aller Ringe
    geom = None
    for ring in rings:
        geom = ring if geom is None else geom.symmetric_difference(ring)
    return unary_union(geom)

txt = text_polygon(NAME, FONT_PATH)

# skalieren auf gewuenschte Buchstabenhoehe + zentrieren
minx, miny, maxx, maxy = txt.bounds
scale = LETTER_HEIGHT / (maxy - miny)
txt = affinity.scale(txt, xfact=scale, yfact=scale, origin=(0, 0))
minx, miny, maxx, maxy = txt.bounds
txt = affinity.translate(txt, xoff=-(minx + maxx) / 2.0, yoff=-(miny + maxy) / 2.0)

# pruefen ob Name auf die Vorderseite passt, sonst verkleinern
tw = maxx - minx
max_w = WIDTH - 2 * CORNER_R * 0.4 - 6
if tw * 1.0 > max_w:
    f = max_w / tw
    txt = affinity.scale(txt, xfact=f, yfact=f, origin=(0, 0))

def extrude_multi(geom, height):
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    parts = [extrude_polygon(p, height) for p in polys if p.area > 0]
    return trimesh.util.concatenate(parts)

# In X spiegeln, damit der Name auf der -Y-Aussenflaeche korrekt lesbar ist
txt = affinity.scale(txt, xfact=-1.0, yfact=1.0, origin=(0, 0))

text_mesh = extrude_multi(txt, EMBOSS)

# Text steht zunaechst in der XY-Ebene (Dicke entlang +Z).
# Aufrichten: um X-Achse +90Grad -> Dicke zeigt nach -Y (Vorderseite)
text_mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0]))
# auf die Vorderseite setzen: Ruecken des Textes 0.4mm in die Wand (Verschmelzung),
# Rest steht erhaben heraus.
OVERLAP = 0.4
text_mesh.apply_translation([0, -DEPTH / 2.0 + OVERLAP, HEIGHT * 0.55])

# ----------------------------------------------------------------------
# 3) Vereinen & Export
# ----------------------------------------------------------------------
result = body.union(text_mesh)
result.merge_vertices()
result.remove_degenerate_faces() if hasattr(result, "remove_degenerate_faces") else None
result.fix_normals()

assert result.is_watertight, "WARNUNG: Mesh ist nicht wasserdicht!"
print("Watertight:", result.is_watertight, "| Volumen mm^3:", round(result.volume, 1))
print("Bounding box (mm):", np.round(result.extents, 1))

result.export("/home/user/Test/pen_holder_Joris.stl")
result.export("/home/user/Test/pen_holder_Joris.3mf")
print("Exportiert: pen_holder_Joris.stl / .3mf")
