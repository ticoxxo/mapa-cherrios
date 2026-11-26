"""'Territorios' (realms): a visual grouping of the town's AGEBs into a few provinces for the zoomed-out view.

Juan José Ríos has no official open district layer, so realms are built by k-means on
population-weighted AGEB centroids (deterministic seed). Each realm is named after the
largest OSM neighbourhood inside it plus a Norteño compass title
(Comarca / Frontera / El Corazón). This is a *game construct*,
recorded as such in the manifest and shown as "agrupación visual, no oficial" in the UI.
"""
from __future__ import annotations

import math
import re
import random

from shapely.geometry import Point
from shapely.ops import polylabel, unary_union

from .common import CITY_CENTER

AGEBS_PER_REALM = 4  # a small town: about four barrios per territorio
SECTORS = ["del Norte", "del Nordeste", "del Oriente", "del Sudeste",  # clockwise from north
           "del Sur", "del Suroeste", "del Poniente", "del Noroeste"]
CENTER_TITLE = "El Corazón"
ROMAN = ["", " II", " III", " IV"]

# Sonoran palette: chile, turquesa, ocre, nopal, bugambilia, adobe, mezclilla, cuero,
# pitahaya, salvia, añil, palo fierro
TINCTURES = ["#a8462f", "#2f8a86", "#c7962f", "#6f7f3f", "#7c3f6a", "#c4672f",
             "#35607f", "#8b5a35", "#b0485f", "#7f8f5a", "#4b4f7a", "#b5895a"]
CHARGES = ["sun", "saguaro", "mountain", "river", "star", "tower", "horse", "wheat", "key", "crescent", "bird", "gear"]

KX = 111.320 * math.cos(math.radians(CITY_CENTER[0]))
KY = 110.574


def _km(pt):
    return ((pt[0] - CITY_CENTER[1]) * KX, (pt[1] - CITY_CENTER[0]) * KY)


def _kmeans(pts, weights, k, seed=7, iters=60):
    rnd = random.Random(seed)
    cents = [pts[rnd.randrange(len(pts))]]
    while len(cents) < k:  # k-means++ init
        d2 = [min((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 for c in cents) * w for p, w in zip(pts, weights)]
        r, acc = rnd.random() * sum(d2), 0.0
        for p, d in zip(pts, d2):
            acc += d
            if acc >= r:
                cents.append(p)
                break
    assign = [0] * len(pts)
    for _ in range(iters):
        assign = [min(range(k), key=lambda j: (p[0] - cents[j][0]) ** 2 + (p[1] - cents[j][1]) ** 2) for p in pts]
        new = []
        for j in range(k):
            idx = [i for i, a in enumerate(assign) if a == j]
            W = sum(weights[i] for i in idx) or 1
            new.append((sum(pts[i][0] * weights[i] for i in idx) / W,
                        sum(pts[i][1] * weights[i] for i in idx) / W) if idx else cents[j])
        if new == cents:
            break
        cents = new
    return assign


def build_realms(agebs: list[dict], loc_names: dict[str, str], places: list[dict], city_loc: str = "0001"):
    """Mutates each ageb dict with 'realm'; returns list of realm dicts with geometry.

    Weights are population when the census covers the zones, otherwise area (the current 2025 zones have
    no census figures yet)."""
    city = [a for a in agebs if a["loc"] == city_loc]
    pts = [_km(a["geom"].centroid.coords[0]) for a in city]
    w = [max(a.get("pop") or 0, 50) if any(c.get("pop") for c in city) else max(a["area_km2"], 0.01) for a in city]
    k = max(1, min(len(city), round(len(city) / AGEBS_PER_REALM)))
    assign = _kmeans(pts, w, k) if city else []
    for a, j in zip(city, assign):
        a["realm"] = f"R{j:02d}"
    for a in agebs:
        if a["loc"] != city_loc:
            a["realm"] = f"L{a['loc']}"
    # compass titles scale with the town: centre = inner quarter, comarca = up to 60 % of its radius
    radius = max((math.hypot(*p) for p in pts), default=1.0) or 1.0

    realms = {}
    for a in agebs:
        realms.setdefault(a["realm"], []).append(a)

    out = []
    used_titles: dict[str, int] = {}
    for rid, members in realms.items():
        geom = unary_union([m["geom"].buffer(0.00006) for m in members]).buffer(-0.00006).simplify(0.00008)
        main = max(geom.geoms, key=lambda g: g.area) if geom.geom_type == "MultiPolygon" else geom
        label = polylabel(main, tolerance=0.0005)
        pop = sum(m.get("pop") or 0 for m in members)
        r = {"id": rid, "geom": geom, "label": (label.x, label.y), "pop": pop,
             "area_km2": sum(m["area_km2"] for m in members), "n_ageb": len(members)}
        if rid.startswith("L"):
            nm = re.sub(r"\s*\(.*\)\s*$", "", loc_names.get(rid[1:], rid))
            r.update(title="Pueblo de " + nm, name=nm, name_basis="census_locality")
            out.append(r)
            continue
        else:
            x, y = _km((label.x, label.y))
            dist = math.hypot(x, y)
            if dist < 0.25 * radius or k == 1:
                t = CENTER_TITLE
            else:
                ang = (math.degrees(math.atan2(x, y)) + 360 + 22.5) % 360
                # inner ring = comarca, outer ring = frontera (each AGEB is a "barrio")
                t = ("Comarca " if dist < 0.6 * radius else "Frontera ") + SECTORS[int(ang // 45)]
            n = used_titles.get(t, 0)
            used_titles[t] = n + 1
            r.update(title=t + ROMAN[min(n, 3)])
            inside = [p for p in places if geom.contains(Point(p["lon"], p["lat"]))]
            if inside:
                # prefer suburbs, then the place nearest the label point
                inside.sort(key=lambda p: (p["rank"] != "suburb", Point(p["lon"], p["lat"]).distance(label)))
                r.update(name=inside[0]["name"], name_basis="osm_place_nearest_label")
            else:
                r.update(name=None, name_basis="compass_sector")
        out.append(r)

    # colour realms so neighbours differ (greedy, largest first)
    out.sort(key=lambda r: -r["pop"])
    for i, r in enumerate(out):
        taken = {o["color_i"] for o in out[:i] if o["geom"].buffer(0.002).intersects(r["geom"])}
        used = [sum(1 for o in out[:i] if o["color_i"] == c) for c in range(len(TINCTURES))]
        free = [c for c in range(len(TINCTURES)) if c not in taken]
        r["color_i"] = min(free, key=lambda c: (used[c], c))
        r["color"] = TINCTURES[r["color_i"]]
        r["charge"] = CHARGES[i % len(CHARGES)]
    return out
