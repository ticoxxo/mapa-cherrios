"""Wealth: CONAPO Índice de Marginación Urbana 2020 and CONEVAL Grado de Rezago Social 2020, by AGEB.

Both are 2020 products keyed by the 2020 AGEB codes, so they belong to the "Antes de ser Municipio" view
(Juan José Ríos in Guasave, El Estero in Ahome); they cannot be joined to the 2025 zones.

Both files are published on datos.gob.mx (CC-BY 4.0) and served from repodatos.atdt.gob.mx,
which sometimes refuses automated clients. When that happens, download the CSV in a browser
and save it as pipeline/manual/<file name> (see pipeline/README.md); the pipeline picks it up.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata

from .common import ANTES_LOCS, ENT, Manifest, Provenance, SourceUnavailable, fetch, num

IMU_URL = "https://repodatos.atdt.gob.mx/api_update/conapo/indices_marginacion/imu_2020.csv"
GRS_URL = "https://repodatos.atdt.gob.mx/api_update/coneval/rezago_social/grs_ageb_2020.csv"
DATASET_IMU = "https://www.datos.gob.mx/dataset/indices_marginacion"
DATASET_GRS = "https://www.datos.gob.mx/dataset/rezago_social"

GRADES = {"muy bajo": 1, "bajo": 2, "medio": 3, "alto": 4, "muy alto": 5}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)


def _grade(v) -> int | None:
    return GRADES.get(_norm(v)) if v not in (None, "") else None


def _read_csv(path) -> list[dict]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delim))


def _key(row: dict, cols: list[str]) -> str | None:
    """Find a 13-char AGEB CVEGEO either in a single column or from ENT/MUN/LOC/AGEB parts."""
    lc = {_norm(c): c for c in cols}
    for c in cols:
        v = str(row[c]).strip()
        if re.fullmatch(r"\d{9}[0-9A-Z]{4}", v) and v.startswith(ENT):
            return v
    parts = []
    for names, width in ((("ent", "cve_ent", "entidad"), 2), (("mun", "cve_mun", "municipio"), 3),
                         (("loc", "cve_loc", "localidad"), 4), (("ageb", "cve_ageb"), 4)):
        col = next((lc[n] for n in names if n in lc), None)
        if col is None:
            return None
        v = str(row[col]).strip().upper()
        if v.endswith(".0"):
            v = v[:-2]
        parts.append(v.zfill(width)[-width:])
    k = "".join(parts)
    return k if len(k) == 13 else None


def _pick(cols, patterns):
    for p in patterns:
        for c in cols:
            if re.fullmatch(p, _norm(c)):
                return c
    return None


def load_imu(manifest: Manifest) -> dict[str, dict]:
    prefixes = tuple(ENT + m + l for m, l in ANTES_LOCS)
    prov = Provenance(id="conapo_imu2020", name="Índice de Marginación Urbana 2020 (AGEB)", url=DATASET_IMU,
                      license="CC-BY 4.0", publisher="CONAPO", vintage="2020",
                      notes=f"File: {IMU_URL}")
    try:
        rows = _read_csv(fetch(IMU_URL, "imu_2020.csv", max_age_days=3650, retries=2))
    except SourceUnavailable as e:
        prov.status, prov.notes = "unavailable", f"{e}. Save the CSV by hand as pipeline/manual/imu_2020.csv"
        manifest.add(prov)
        print(f"  ! IMU unavailable: {e}")
        return {}
    cols = list(rows[0].keys())
    gcol = _pick(cols, [r"gm_?2020", r"gm", r"grado.*", r"gmu.*"])
    icol = _pick(cols, [r"im_?2020", r"imu_?2020", r"im", r"indice.*"])
    ncol = _pick(cols, [r"imn_?2020", r"imn", r".*normaliz.*"])
    print(f"  IMU columns → grade={gcol} index={icol} normalized={ncol}")
    out = {}
    for r in rows:
        k = _key(r, cols)
        if not k or not k.startswith(prefixes):
            continue
        out[k] = {"imu_grade": _grade(r.get(gcol)) if gcol else None,
                  "imu": num(r.get(icol)) if icol else None,
                  "imu_n": num(r.get(ncol)) if ncol else None}
    prov.status = "ok" if out else "unavailable"
    if not out:
        prov.notes += " — no Juan José Ríos rows: the file may be trimmed to another place; save the national CSV."
    manifest.add(prov)
    print(f"  IMU: {len(out)} AGEBs")
    return out


def load_grs(manifest: Manifest) -> dict[str, dict]:
    prefixes = tuple(ENT + m + l for m, l in ANTES_LOCS)
    prov = Provenance(id="coneval_grs2020", name="Grado de Rezago Social 2020 (AGEB)", url=DATASET_GRS,
                      license="CC-BY 4.0", publisher="CONEVAL", vintage="2020", notes=f"File: {GRS_URL}")
    try:
        rows = _read_csv(fetch(GRS_URL, "grs_ageb_2020.csv", max_age_days=3650, retries=2))
    except SourceUnavailable as e:
        prov.status, prov.notes = "unavailable", f"{e}. Save the CSV by hand as pipeline/manual/grs_ageb_2020.csv"
        manifest.add(prov)
        print(f"  ! GRS unavailable: {e}")
        return {}
    cols = list(rows[0].keys())
    gcol = _pick(cols, [r"grs", r"gdo_?rezsoc.*", r"grado.*rezago.*", r"grado.*", r".*rezago.*"])
    print(f"  GRS columns → grade={gcol}")
    out = {}
    for r in rows:
        k = _key(r, cols)
        if not k or not k.startswith(prefixes):
            continue
        # CONEVAL's AGEB grade has five levels (Muy bajo … Muy alto)
        out[k] = {"grs_grade": _grade(r.get(gcol)) if gcol else None}
    prov.status = "ok" if out else "unavailable"
    manifest.add(prov)
    print(f"  GRS: {len(out)} AGEBs")
    return out
