"""Chamba: INEGI DENUE (Directorio Estadístico Nacional de Unidades Económicas), state file (ENT),
filtered to the municipio (CVE_ENT + CVE_MUN in common.py).

Rules:
- DENUE gives each business's size only as a range of people employed (PER_OCU). The number
  of jobs per AGEB is therefore an ESTIMATE (range midpoints, `JOBS_MID`) and is labelled so.
- Businesses are assigned to an AGEB by DENUE's own CVE_LOC + CVE_AGEB keys, not by geometry.
- Groups follow the first two digits of the SCIAN activity code (`GROUP_OF`).
- No phone numbers, e-mails or web sites are copied into the app.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from collections import Counter, defaultdict

from .common import ENT, MUN, OUT, Manifest, Provenance, SourceUnavailable, fetch, write_json

URL = f"https://www.inegi.org.mx/contenidos/masiva/denue/denue_{ENT}_csv.zip"
ZIP_NAME = f"denue_{ENT}_csv.zip"

SIZES = ["0 a 5", "6 a 10", "11 a 30", "31 a 50", "51 a 100", "101 a 250", "251 y m"]
JOBS_MID = [3, 8, 20, 40, 75, 175, 300]  # 251+ is open-ended: a deliberately low guess
GROUPS = ["tienda", "comida", "taller", "oficina", "fabrica", "escuela"]
GROUP_OF = {"43": "tienda", "46": "tienda", "72": "comida", "81": "taller",
            **{k: "oficina" for k in ("51", "52", "53", "54", "55", "56", "93")},
            **{k: "fabrica" for k in ("11", "21", "22", "23", "31", "32", "33", "48", "49")},
            **{k: "escuela" for k in ("61", "62", "71")}}

_SMALL = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "a", "para", "con", "sa", "cv"}


def _title(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    words = []
    for i, w in enumerate(s.lower().split(" ")):
        words.append(w if (i and w in _SMALL) else w[:1].upper() + w[1:])
    return " ".join(words)


def _size(per_ocu: str) -> int | None:
    for i, p in enumerate(SIZES):
        if per_ocu.startswith(p):
            return i
    return None


def _edition(z: zipfile.ZipFile) -> tuple[str, str]:
    meta = z.read("metadatos/metadatos_denue.txt").decode("utf-8", "replace")
    title = re.search(r"DENUE\)\s*(\d{2})_(\d{4})", meta)
    mod = re.search(r"Modified:\s*(\S+)", meta)
    ed = f"{title.group(2)}-{title.group(1)}" if title else "?"
    return ed, (mod.group(1) if mod else "?")


def build_work(manifest: Manifest, agebs: list[dict]) -> dict:
    try:
        path = fetch(URL, ZIP_NAME, max_age_days=6, timeout=600)
    except SourceUnavailable as e:
        print(f"  ! DENUE unavailable: {e}")
        manifest.add(Provenance(id="inegi_denue", name="DENUE (directorio de negocios)", url=URL,
                                license="Términos de Libre Uso de la Información del INEGI", publisher="INEGI",
                                vintage="?", status="unavailable", notes=str(e)))
        manifest.layer("work", "unavailable", ["inegi_denue"])
        return {}

    z = zipfile.ZipFile(path)
    edition, modified = _edition(z)
    csv_name = next(n for n in z.namelist() if n.startswith("conjunto_de_datos/") and n.endswith(".csv"))
    rows = csv.DictReader(io.TextIOWrapper(z.open(csv_name), encoding="latin-1", newline=""))

    by_key = {a["cvegeo"]: a for a in agebs}
    acc: dict[str, dict] = defaultdict(lambda: {"n": 0, "emp": 0, "big": 0, "g": Counter(), "top": None})
    feats, acts = [], {}
    total, groups, sizes, unplaced, new_year = 0, Counter(), Counter(), 0, Counter()
    year = modified[:4]
    biggest = []
    for r in rows:
        if r["CVE_ENT"] != ENT or r["CVE_MUN"] != MUN:
            continue
        s = _size(r["PER_OCU"])
        g = GROUP_OF.get(r["CODIGO_ACT"][:2], "taller")
        try:
            lat, lon = float(r["LATITUD"]), float(r["LONGITUD"])
        except ValueError:
            lat = lon = None
        total += 1
        groups[g] += 1
        if s is not None:
            sizes[s] += 1
        alta = (r["FECHA_ALTA"] or "").strip()
        if alta.startswith(year):
            new_year[g] += 1
        name = _title(r["NOM_ESTAB"]) or "Sin nombre"
        code = r["CODIGO_ACT"].strip()
        acts.setdefault(code, r["NOMBRE_ACT"].strip())
        if s is not None and s >= 6:
            biggest.append(name)

        key = ENT + MUN + r["CVE_LOC"].strip().zfill(4) + r["CVE_AGEB"].strip().upper().zfill(4)
        if key in by_key:
            a = acc[key]
            a["n"] += 1
            a["g"][g] += 1
            if s is not None:
                a["emp"] += JOBS_MID[s]
                if s >= 5:
                    a["big"] += 1
                if a["top"] is None or s > a["top"][0]:
                    a["top"] = (s, name)
        else:
            unplaced += 1
        if lat is not None:  # compact rows: [lon, lat, group index, size index or -1, name, SCIAN code, alta]
            feats.append([round(lon, 5), round(lat, 5), GROUPS.index(g), -1 if s is None else s, name, code, alta])

    if not total:
        manifest.layer("work", "unavailable", ["inegi_denue"])
        return {}

    # big employers first so they win symbol collisions on the map
    feats.sort(key=lambda f: -f[3])
    write_json(OUT / "work.json", {"groups": GROUPS, "cols": ["lon", "lat", "g", "s", "n", "c", "a"], "rows": feats,
                                   "acts": acts})

    for a in agebs:
        v = acc.get(a["cvegeo"])
        if not v:
            a.update(j_n=0, j_emp=0, j_dens=0, j_big=0, j_top=None, **{f"j_{g}": 0 for g in GROUPS})
            continue
        a.update(j_n=v["n"], j_emp=v["emp"], j_dens=round(v["emp"] / a["area_km2"]) if a["area_km2"] else None,
                 j_big=v["big"], j_top=v["top"][1] if v["top"] and v["top"][0] >= 3 else None,
                 **{f"j_{g}": v["g"][g] for g in GROUPS})

    manifest.add(Provenance(
        id="inegi_denue", name="DENUE (directorio de negocios)", url=URL,
        license="Términos de Libre Uso de la Información del INEGI", publisher="INEGI",
        vintage=f"edición {edition} (publicada {modified})",
        notes=f"{total} establecimientos en el municipio 030; {unplaced} sin AGEB urbana. "
              "Empleos por AGEB estimados con el punto medio del rango PER_OCU (251+ = 300)."))
    manifest.layer("work", "ok", ["inegi_denue", "inegi_mg_ageb"], modeled_fields=["j_emp", "j_dens"])
    est_jobs = sum(JOBS_MID[s] * n for s, n in sizes.items())
    print(f"  {total} businesses, ~{est_jobs} jobs (estimate), {unplaced} outside urban AGEBs, edition {edition}")
    return {"edition": edition, "published": modified, "total": total, "jobs_est": est_jobs,
            "groups": dict(groups), "sizes": [sizes[i] for i in range(len(SIZES))],
            "new_year": {"year": year, "total": sum(new_year.values()), "groups": dict(new_year)},
            "n_big": len(biggest), "jobs_mid": JOBS_MID}
