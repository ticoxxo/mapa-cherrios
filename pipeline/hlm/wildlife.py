"""Fauna: iNaturalist research-grade animal observations in the municipio bbox.

Rules:
- Only observations with an open licence (CC0 / CC-BY*) are kept; each keeps its observer
  login and licence so the app can attribute it.
- Observations with obscured coordinates (threatened species, private geoprivacy) are never
  placed on the map or assigned to an AGEB. They are counted city-wide only.
- Positions less precise than MAX_ACCURACY_M are drawn but not assigned to an AGEB.
- Counts reflect where people observe, not how much wildlife there is (observer effort).
"""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

from shapely import STRtree
from shapely.geometry import Point

from .common import BBOX, CACHE, OUT, TODAY, UA, Manifest, Provenance, write_json

API = "https://api.inaturalist.org/v1/observations"
ANIMALS = ["Aves", "Reptilia", "Mammalia", "Amphibia", "Insecta", "Arachnida", "Mollusca", "Actinopterygii", "Animalia"]
GROUP = {"Aves": "ave", "Reptilia": "rep", "Mammalia": "mam", "Insecta": "ins", "Arachnida": "ins"}  # else "otr"
GROUPS = ["ave", "rep", "mam", "ins", "otr"]
MAX_ACCURACY_M = 500
CACHE_FILE = "inat_observations.json"
MAX_AGE_DAYS = 6


def _get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    wait = 4
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"  ! iNaturalist attempt {attempt + 1}: {e}; retrying in {wait}s")
            time.sleep(wait)
            wait *= 2
    raise RuntimeError("iNaturalist API unreachable")


def _download() -> list[dict]:
    """All research-grade animal observations in the bbox, paged by id (API asks ≤ 1 req/s)."""
    cache = CACHE / CACHE_FILE
    if cache.exists() and (time.time() - cache.stat().st_mtime) < MAX_AGE_DAYS * 86400:
        return json.loads(cache.read_text(encoding="utf-8"))
    s, w, n, e = BBOX
    base = {"swlat": s, "swlng": w, "nelat": n, "nelng": e, "quality_grade": "research",
            "iconic_taxa": ",".join(ANIMALS), "per_page": 200, "order_by": "id", "order": "asc",
            "locale": "es-MX"}
    out, last = [], 0
    while True:
        d = _get({**base, "id_above": last})
        res = d.get("results", [])
        if not res:
            break
        for o in res:
            t = o.get("taxon") or {}
            loc = (o.get("location") or "").split(",")
            out.append({
                "id": o["id"],
                "lat": float(loc[0]) if len(loc) == 2 else None,
                "lon": float(loc[1]) if len(loc) == 2 else None,
                "obscured": bool(o.get("obscured")),
                "acc": o.get("public_positional_accuracy"),
                "observed": o.get("observed_on"),
                "created": (o.get("created_at") or "")[:10],
                "taxon_id": t.get("id"),
                "sci": t.get("name"),
                "common": t.get("preferred_common_name"),
                "iconic": t.get("iconic_taxon_name"),
                "rank": t.get("rank"),
                "license": o.get("license_code"),
                "user": (o.get("user") or {}).get("login"),
            })
        last = res[-1]["id"]
        print(f"  iNaturalist: {len(out):,} / {d.get('total_results', '?'):,}", end="\r")
        time.sleep(1.1)
    print()
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def build_wildlife(manifest: Manifest, agebs: list[dict]) -> dict:
    """Writes wildlife.geojson and adds w_* fields to each AGEB dict. Returns city stats."""
    prov = Provenance(id="inaturalist", name="Observaciones de fauna, grado de investigación",
                      url="https://www.inaturalist.org/observations?" + urllib.parse.urlencode(
                          {"swlat": BBOX[0], "swlng": BBOX[1], "nelat": BBOX[2], "nelng": BBOX[3],
                           "quality_grade": "research", "iconic_taxa": ",".join(ANIMALS)}),
                      license="Por observación: CC0 / CC BY / CC BY-NC (se excluyen las de todos los derechos reservados)",
                      publisher="iNaturalist", vintage="en vivo")
    try:
        obs = _download()
    except RuntimeError as e:
        prov.status, prov.notes = "unavailable", str(e)
        manifest.add(prov)
        manifest.layer("wildlife", "unavailable", ["inaturalist"], reason=str(e))
        for a in agebs:
            a.update({"w_n": None, "w_sp": None, **{f"w_{g}": None for g in GROUPS}, "w_top": None})
        return {}

    licensed = [o for o in obs if o["license"]]
    placed = [o for o in licensed if not o["obscured"] and o["lat"] is not None]
    precise = [o for o in placed if o["acc"] is None or o["acc"] <= MAX_ACCURACY_M]
    grp = lambda o: GROUP.get(o["iconic"], "otr")  # noqa: E731
    name = lambda o: o["common"] or o["sci"]  # noqa: E731

    # --- assign to AGEBs ---
    tree = STRtree([a["geom"] for a in agebs])
    per = defaultdict(list)
    for o in precise:
        hits = tree.query(Point(o["lon"], o["lat"]), predicate="intersects")
        if len(hits):
            per[int(hits[0])].append(o)
    for i, a in enumerate(agebs):
        lst = per.get(i, [])
        gc = Counter(grp(o) for o in lst)
        sp = Counter(name(o) for o in lst if o["rank"] in ("species", "subspecies", "variety"))
        a.update({"w_n": len(lst), "w_sp": len(sp), **{f"w_{g}": gc.get(g, 0) for g in GROUPS},
                  "w_top": "|".join(f"{k}:{v}" for k, v in sp.most_common(3)) or None})

    # --- points for the map ---
    week_ago = (dt.date.fromisoformat(TODAY) - dt.timedelta(days=7)).isoformat()
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(o["lon"], 5), round(o["lat"], 5)]},
              "properties": {"i": o["id"], "g": grp(o), "n": name(o), "s": o["sci"], "d": o["observed"],
                             "u": o["user"], "l": o["license"], "w": 1 if o["created"] >= week_ago else 0}}
             for o in placed]
    write_json(OUT / "wildlife.geojson", {"type": "FeatureCollection", "features": feats})

    # --- city stats & this week ---
    new = [o for o in licensed if o["created"] >= week_ago]
    species_total = Counter(o["taxon_id"] for o in licensed)
    firsts = sorted({name(o) + "|" + (o["sci"] or "") for o in new
                     if species_total[o["taxon_id"]] == 1 and o["rank"] in ("species", "subspecies")})
    stats = {
        "total": len(licensed), "excluded_unlicensed": len(obs) - len(licensed),
        "obscured": sum(o["obscured"] for o in licensed), "placed": len(placed), "in_ageb": sum(len(v) for v in per.values()),
        "species": len({o["taxon_id"] for o in licensed if o["rank"] in ("species", "subspecies")}),
        "groups": dict(Counter(grp(o) for o in licensed)),
        "week": {"from": week_ago, "to": TODAY, "new": len(new), "groups": dict(Counter(grp(o) for o in new)),
                 "top": [k for k, _ in Counter(name(o) for o in new).most_common(3)],
                 "firsts": [f.split("|") for f in firsts[:5]]},
    }
    prov.notes = (f"{len(obs):,} observaciones; {stats['excluded_unlicensed']:,} sin licencia abierta excluidas; "
                  f"{stats['obscured']:,} con ubicación oculta (no se dibujan).")
    manifest.add(prov)
    manifest.layer("wildlife", "ok", ["inaturalist", "inegi_mg_ageb"], count=len(feats))
    print(f"  wildlife: {len(licensed):,} licensed, {len(placed):,} placed, {stats['in_ageb']:,} in AGEBs, "
          f"{stats['week']['new']} new this week")
    return stats
