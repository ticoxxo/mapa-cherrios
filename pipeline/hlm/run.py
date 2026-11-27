"""Entry point: `uv run --directory pipeline python -m hlm.run [--skip blocks,streets,osm]`.

Builds two views of Juan José Ríos into public/data/:
- public/data/        "Municipio": the 2025 zones of municipio 25-020 plus every live layer.
- public/data/antes/  "Antes de ser Municipio": the 2020 zones (Guasave / Ahome) with the 2020 census and
                      the 2020 marginalization indices. Only 2020 data; live layers are not repeated there.
"""
from __future__ import annotations

import argparse
import json
import statistics

from shapely.geometry import mapping

from . import base, campo, chronicle, coast, green, heat, osm, people, realms, wealth, water, wildlife, work
from .common import ANTES_CITY, ANTES_LOCS, OUT, OUT_ANTES, PLACE, Manifest, Provenance, round_coords, write_json


def quantile_breaks(values, n):
    v = sorted(x for x in values if x is not None)
    if len(v) < 2:
        return []
    qs = statistics.quantiles(v, n=n, method="inclusive")
    nice = []
    for q in qs:
        mag = 10 ** max(len(str(int(q))) - 2, 0)
        b = round(q / mag) * mag
        if not nice or b > nice[-1]:
            nice.append(b)
    return nice


def quantiles(values, n, nd):
    v = [x for x in values if x is not None]
    return [round(x, nd) for x in statistics.quantiles(v, n=n)] if len(v) >= 2 else []


def _features(agebs, rs, out_dir):
    """Write agebs.geojson and realms.geojson for one view."""
    realm_by_id = {r["id"]: r for r in rs}
    feats = []
    for a in agebs:
        props = {k: v for k, v in a.items() if k != "geom"}
        props["area_km2"] = round(a["area_km2"], 4)
        props["color"] = realm_by_id[a["realm"]]["color"]
        feats.append({"type": "Feature", "id": int(a["cvegeo"][5:9] + "".join(
            str(ord(ch) - 55) if ch.isalpha() else ch for ch in a["cvegeo"][9:])),
            "geometry": round_coords(mapping(a["geom"].simplify(0.00001, preserve_topology=True)), 6),
            "properties": props})
    write_json(out_dir / "agebs.geojson", {"type": "FeatureCollection", "features": feats})
    rfeats = []
    for r in rs:
        props = {k: v for k, v in r.items() if k != "geom"}
        props["area_km2"] = round(r["area_km2"], 2)
        props["dens"] = round(r["pop"] / r["area_km2"]) if r["area_km2"] and r["pop"] else None
        members = [a for a in agebs if a["realm"] == r["id"]]
        graded = [(a["imu_grade"], a.get("pop") or 0) for a in members if a.get("imu_grade")]
        wsum = sum(p for _, p in graded)
        props["imu_grade_avg"] = round(sum(g * p for g, p in graded) / wsum, 2) if wsum else None
        rfeats.append({"type": "Feature", "geometry": round_coords(mapping(r["geom"]), 5), "properties": props})
    write_json(out_dir / "realms.geojson", {"type": "FeatureCollection", "features": rfeats})


RANGE_KEYS = ("dens", "school", "p_inet", "p_car", "p_young", "p_old", "occ", "p_water", "p_tinaco", "p_cister")


def _census_stats(agebs, totals, city_loc):
    city = totals.get(city_loc, {})
    mun = totals.get("municipio", {})
    return {
        "municipio": {"pop": mun.get("pop"), "homes": mun.get("homes")},
        "city": {"name": city.get("name") or PLACE, "pop": city.get("pop"),
                 "area_km2": round(sum(a["area_km2"] for a in agebs if a["loc"] == city_loc), 1)},
        "localities": {k: {"name": v.get("name"), "pop": v.get("pop")} for k, v in totals.items() if k != "municipio"},
        "n_ageb": len(agebs), "n_ageb_without_census": sum(not a["in_census"] for a in agebs),
        "ranges": {k: [min(vals), max(vals), round(statistics.median(vals), 1)] for k in RANGE_KEYS
                   if (vals := [a[k] for a in agebs if a.get(k) is not None])},
    }


def _join_census(agebs, census, imu, grs):
    for a in agebs:
        c = census.get(a["cvegeo"])
        a["in_census"] = c is not None
        a.update({k: v for k, v in (c or {}).items() if k != "loc_name"})
        a.update(people.derive(c or {}, a["area_km2"]))
        a.update(imu.get(a["cvegeo"], {"imu_grade": None, "imu": None, "imu_n": None}))
        a.update(grs.get(a["cvegeo"], {"grs_grade": None}))
    people.check_ratios(agebs)


def build_antes(m: Manifest, places, skip, farm=None):
    """'Antes de ser Municipio': 2020 zones + 2020 census + 2020 marginalization, nothing live."""
    print("• antes de ser municipio (2020)")
    agebs = base.load_agebs_2020(m)
    census, block_pop, totals = people.load_census(m, ANTES_LOCS)
    imu = wealth.load_imu(m)
    grs = wealth.load_grs(m)
    _join_census(agebs, census, imu, grs)
    loc_names = {k: v["name"] for k, v in totals.items() if k != "municipio" and "name" in v}
    rs = realms.build_realms(agebs, loc_names, places, city_loc=ANTES_CITY)
    _features(agebs, rs, OUT_ANTES)
    have_imu = any(a["imu_grade"] for a in agebs)
    have_grs = any(a["grs_grade"] for a in agebs)
    m.layer("antes_realm", "ok", ["inegi_mg2020", "hlm_realms"])
    m.layer("antes_people", "ok" if census else "unavailable", ["inegi_censo2020", "inegi_mg2020"])
    m.layer("antes_wealth", "ok" if (have_imu or have_grs) else "unavailable",
            [s for s, ok in (("conapo_imu2020", have_imu), ("coneval_grs2020", have_grs)) if ok]
            or ["conapo_imu2020", "coneval_grs2020"],
            primary="imu" if have_imu else "grs" if have_grs else None)
    stats = {"era": "antes", **_census_stats(agebs, totals, ANTES_CITY),
             "parent": {"011": "Guasave", "001": "Ahome"},
             "breaks": {"dens": quantile_breaks([a["dens"] for a in agebs if a.get("pop")], 7),
                        "p_tinaco": quantiles([a.get("p_tinaco") for a in agebs], 6, 1)},
             # SIAP still files the town inside Guasave / Ahome: their whole-municipio tables belong here
             "campo": {"siap": siap} if (siap := campo.antes_siap(m, farm)) else None}
    write_json(OUT_ANTES / "stats.json", stats, compact=False)
    if "blocks" not in skip:
        base.build_blocks_2020(m, block_pop)


CARRY = {"wildlife": (("wildlife",), lambda k: k.startswith("w_")),
         "heat": (("heat", "weather"), lambda k: k == "lst"),
         "green": (("green",), lambda k: k in ("ndvi", "p_green", "ndvi_ago", "p_tree")),
         "work": (("work",), lambda k: k.startswith("j_")),
         "water": (("water",), lambda k: k in ("a_n", "a_vol")),
         "campo": (("campo",), lambda k: k == "c_crop")}


def _carry_over(agebs, skip):
    """Copy per-AGEB fields and stats sections of skipped steps from the previous output."""
    steps = [s for s in CARRY if s in skip]
    if not steps or not (OUT / "stats.json").exists() or not (OUT / "agebs.geojson").exists():
        return {}
    old_stats = json.loads((OUT / "stats.json").read_text(encoding="utf-8"))
    old = {f["properties"]["cvegeo"]: f["properties"]
           for f in json.loads((OUT / "agebs.geojson").read_text(encoding="utf-8"))["features"]}
    out = {}
    for step in steps:
        sections, want = CARRY[step]
        for sec in sections:
            if old_stats.get(sec):
                out[sec] = old_stats[sec]
        for a in agebs:
            a.update({k: v for k, v in old.get(a["cvegeo"], {}).items() if want(k)})
        print(f"  (kept previous {step} numbers)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", default="", help="comma list: blocks,streets,osm,wildlife,heat,green,work,water,campo")
    args = ap.parse_args(argv)
    skip = set(filter(None, args.skip.split(",")))

    m = Manifest()
    prev = OUT / "manifest.json"
    if prev.exists():  # keep provenance of layers this run does not rebuild
        old = json.loads(prev.read_text(encoding="utf-8"))
        m.sources.update(old.get("sources", {}))
        m.layers.update(old.get("layers", {}))

    print("• base geometry")
    agebs = base.load_agebs(m)
    area = base.load_municipio(m)
    print("• people (census 2020; none for the new municipio's zones)")
    census, block_pop, totals = people.load_census(m)
    print("• sea (Natural Earth)")
    coast.build_sea(m, area)
    if "osm" not in skip:
        print("• OpenStreetMap")
        places = osm.build_osm(m)
    else:
        places = osm.cached_places()

    _join_census(agebs, census, {}, {})

    wild = {}
    if "wildlife" not in skip:
        print("• wildlife (iNaturalist)")
        wild = wildlife.build_wildlife(m, agebs)

    lst, weather = {}, {}
    if "heat" not in skip:
        print("• heat (Landsat + NASA POWER)")
        lst = heat.build_heat(m, agebs)
        weather = heat.build_weather(m)

    veg = {}
    if "green" not in skip:
        print("• green (Sentinel-2 + WorldCover)")
        veg = green.build_green(m, agebs)

    jobs = {}
    if "work" not in skip:
        print("• work (INEGI DENUE)")
        jobs = work.build_work(m, agebs)

    wat = {}
    if "water" not in skip:
        print("• water (CONAGUA REPDA + Monitor de Sequía)")
        wat = water.build_water(m, agebs, area)

    farm = {}
    if "campo" not in skip:
        print("• campo (INEGI USV VII + WorldCover + SIAP)")
        farm = campo.build_campo(m, agebs, area)

    # A skipped data step keeps last run's numbers instead of blanking its map mode.
    carried = _carry_over(agebs, skip)
    fresh = (wild, lst, weather, veg, jobs, wat, farm)  # La Gaceta only reports what this run actually measured
    wild = wild or carried.get("wildlife", {})
    lst = lst or carried.get("heat", {})
    weather = weather or carried.get("weather", {})
    veg = veg or carried.get("green", {})
    jobs = jobs or carried.get("work", {})
    wat = wat or carried.get("water", {})
    farm = farm or carried.get("campo", {})

    print("• realms")
    loc_names = base.locality_names(m)
    rs = realms.build_realms(agebs, loc_names, places)
    m.add(Provenance(id="hlm_realms", name="Territorios (agrupación visual)", url="pipeline/hlm/realms.py",
                     license="CC-BY 4.0 (derived)", publisher="Mapa Cherrios", vintage="derived",
                     modeled=True, notes="k-means of AGEB centroids (population-weighted when the census covers "
                                         "them, area-weighted otherwise); not an official district."))
    _features(agebs, rs, OUT)

    m.layer("realm", "ok", ["inegi_mg_ageb", "hlm_realms", "osm"])
    # The 2020 census and indices use the old Guasave / Ahome codes: they live in the "antes" view.
    m.layer("people", "ok" if census else "unavailable", ["inegi_censo2020", "inegi_mg_ageb"],
            **({} if census else {"reason": "antes"}))
    m.layer("wealth", "unavailable", ["conapo_imu2020", "coneval_grs2020"], reason="antes", primary=None)
    for mode in ("heat", "green", "wildlife", "work", "water", "campo"):
        m.layers.setdefault(mode, {"status": "not_built", "sources": []})

    stats = {
        "era": "municipio",
        **_census_stats(agebs, totals, "0001"),
        "breaks": {
            "dens": quantile_breaks([a["dens"] for a in agebs if a.get("pop")], 7),
            "w_n": quantile_breaks([a["w_n"] for a in agebs if a.get("w_n")], 6),
            "lst": quantiles([a.get("lst") for a in agebs], 7, 1),
            "ndvi": quantiles([a.get("ndvi") for a in agebs], 6, 3),
            "j_dens": quantile_breaks([a["j_dens"] for a in agebs if a.get("j_dens")], 6),
            "p_tinaco": quantiles([a.get("p_tinaco") for a in agebs], 6, 1),
        },
        "work": jobs or None,
        "water": wat or None,
        "heat": lst or None,
        "green": veg or None,
        "weather": weather or None,
        "wildlife": wild or None,
        "campo": farm or None,
    }
    write_json(OUT / "stats.json", stats, compact=False)

    if "streets" not in skip:
        print("• streets")
        base.build_streets(m)
    if "blocks" not in skip:
        print("• blocks")
        base.build_blocks(m, block_pop)

    build_antes(m, places, skip, farm)

    f_wild, f_lst, f_weather, f_veg, f_jobs, f_wat, f_farm = fresh
    chronicle.update(f_wild, f_lst, f_weather, agebs, rs, f_veg, f_jobs, f_wat, f_farm)
    write_json(OUT / "manifest.json", {"generated": m.generated, "sources": m.sources, "layers": m.layers},
               compact=False)
    print("done.")


if __name__ == "__main__":
    main()
