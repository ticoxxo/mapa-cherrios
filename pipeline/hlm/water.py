"""Agua: who holds the water (CONAGUA REPDA) and how dry it is (SMN Monitor de Sequía).

Sources
- REPDA (Registro Público de Derechos de Agua), CONAGUA open data. datos.conagua.gob.mx answers scripts
  with a bot wall, so we read the unmodified releases preserved on Zenodo (record 24183265,
  Gómez-Arias & Moctezuma; data under Términos de Libre Uso MX, documentation CC BY 4.0). The newest
  release in the record is used; it is a snapshot, not a live feed, and the UI says its date.
  A hand-downloaded `pipeline/manual/repda.zip` (same layout) is used if Zenodo is down.
- Monitor de Sequía de México (SMN / CONAGUA), municipal table, every 15 days since 2003.
  In that table an EMPTY cell means "sin sequía" (see its NOTAS sheet), not missing data.

Rules
- Only points inside the outline of the municipio of Juan José Ríos (INEGI 2025) are kept. Older REPDA
  releases file them under Guasave or Ahome, so the municipio code is not used to filter.
- Privacy: holders that are companies, ejidos, associations or public bodies are named; holders that
  look like private people are shown as "Particular" and their points are rounded to ~100 m.
- Volumes are the yearly volumes the titles AUTHORISE, not metered pumping. The UI says so.
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict

from .common import BBOX, ENT, MUN, OUT, Manifest, Provenance, SourceUnavailable, fetch, write_json

ZENODO = "https://zenodo.org/api/records/24183265/versions/latest"
ZENODO_PAGE = "https://zenodo.org/records/24183265"
SMN_URL = ("https://smn.conagua.gob.mx/tools/RESOURCES/Monitor%20de%20Sequia%20en%20Mexico/"
           "MunicipiosSequia.xlsx")
CVE_MUN = ENT + MUN

USES = ["agricola", "urbano", "industria", "ganado", "otros"]
USE_OF = {"AGRICOLA": "agricola", "AGROINDUSTRIAL": "industria", "PUBLICO URBANO": "urbano",
          "INDUSTRIAL": "industria", "GENERACION DE ENERGIA ELECTRICA": "industria", "PECUARIO": "ganado"}
KINDS = ["pozo", "toma"]  # groundwater well · surface intake (river, dam, stream)
DROUGHT = ["sin", "D0", "D1", "D2", "D3", "D4"]

# Holders named on the map: legal entities, ejidos, associations and public bodies.
_ENTITY = re.compile(
    r"(\bS\.?\s?A\.?(\s|,|$)|\bS\.?\s?DE\s?R\.?\s?L|\bS\.?\s?P\.?\s?R\b|\bSPR\b|\bS\.?\s?C\.?(\s|,|$)|\bA\.?\s?C\.?$|"
    r"\bA\.\s?C\.|\bSAPI\b|\bS\.?\s?A\.?\s?P\.?\s?I\b|\bS\.?\s?A\.?\s?S\b|\bDE\s+C\.?\s?V\b|\bSOCIEDAD\b|\bASOCIACION\b|"
    r"\bCOOPERATIVA\b|\bEJIDO\b|\bEJIDOS\b|\bCOMUNIDAD\b|\bMUNICIPIO\b|\bAYUNTAMIENTO\b|\bGOBIERNO\b|\bCOMISION\b|"
    r"\bORGANISMO\b|\bUNIVERSIDAD\b|\bINSTITUTO\b|\bSECRETARIA\b|\bJUNTA\b|\bDISTRITO\b|"
    r"\bUNION\b|\bGRUPO\b|\bINMOBILIARIA\b|\bFRACCIONADORA\b|\bCORPORATIVO\b|\bCOLEGIO\b|\bPATRONATO\b|"
    r"\bFIDEICOMISO\b|\bIMSS\b|\bISSSTE\b|\bCFE\b|\bPEMEX\b|\bSEDENA\b|\bCOMPANIA\b|\bINDUSTRIAS?\b|\bCLUB\b)")


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip().upper()


def is_entity(holder: str) -> bool:
    return bool(_ENTITY.search(_plain(holder)))


_SUFFIX = re.compile(r"[,.]?\s*\b(S\.?\s?A\.?\s?P\.?\s?I\.?|SAPI|S\.?\s?A\.?|S\.?\s?P\.?\s?R\.?|SPR|S\.?\s?C\.?|A\.?\s?C\.?)"
                     r"(\s*(DE)?\s*(R\.?\s?L\.?|C\.?\s?V\.?|RL|CV))*\.?\s*$|\bS\.?\s?DE\s?R\.?\s?L.*$|\bDE\s+C\.?\s?V?\.?\s*$")


def holder_key(holder: str) -> str:
    """Groups spellings of one holder: 'CASTOR FIELDS SAPI DE CV' == 'CASTOR FIELDS, S.A.P.I. DE C.V.'"""
    k = _plain(holder)
    for _ in range(3):
        k = _SUFFIX.sub("", k).strip(" ,.")
    return re.sub(r"[^A-Z0-9Ñ ]", "", k).strip()


def _dms(d, m, s) -> float | None:
    try:
        return float(d) + float(m) / 60 + float(s) / 3600
    except (TypeError, ValueError):
        return None


def _f(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _latest_repda() -> tuple:
    meta = json.loads(fetch(ZENODO, "repda_zenodo_record.json", max_age_days=6).read_text(encoding="utf-8"))
    snaps = sorted(f["key"] for f in meta.get("files", []) if re.fullmatch(r"REPDA_\d{4}-\d{2}\.zip", f["key"]))
    if not snaps:
        raise SourceUnavailable("no REPDA snapshot in the Zenodo record")
    key = snaps[-1]
    url = next(f["links"]["self"] for f in meta["files"] if f["key"] == key)
    return fetch(url, key, max_age_days=3650, timeout=600), key[6:13], meta


def _read(z: zipfile.ZipFile, name: str):
    n = next(x for x in z.namelist() if x.endswith("/" + name) or x == name)
    return csv.reader(io.TextIOWrapper(z.open(n), encoding="utf-8-sig", newline=""))


def _repda(manifest: Manifest, agebs: list[dict], area) -> dict:
    try:
        path, snap, meta = _latest_repda()
    except (SourceUnavailable, KeyError, StopIteration, json.JSONDecodeError) as e:
        print(f"  ! REPDA unavailable: {e}")
        manifest.add(Provenance(id="conagua_repda", name="REPDA (títulos de agua)", url=ZENODO_PAGE,
                                license="Términos de Libre Uso MX", publisher="CONAGUA", vintage="?",
                                status="unavailable", notes=str(e)))
        return {}

    z = zipfile.ZipFile(path)
    titles = {}  # título -> (use, holder, registration date)
    for name in ("CONCESIONES.csv", "CONCESIONES_DTTOS_DE_RIEGO.csv"):
        rows = _read(z, name)
        h = [_plain(x) for x in next(rows)]
        i_uso, i_tit, i_fecha = h.index("USO QUE AMPARA EL TITULO"), h.index("TITULAR"), h.index("FECHA DE REGISTRO")
        for r in rows:
            titles[r[0]] = (USE_OF.get(_plain(r[i_uso]), "otros"), r[i_tit].strip(), r[i_fecha][:10])

    # annexes with locations: (file, kind). Column positions differ per file, so look them up by name.
    from shapely.geometry import Point
    from shapely.prepared import prep
    inside = prep(area)
    pts = []
    for name, kind in (("ANEXOS_SUBTERRANEOS.csv", 0), ("ANEXOS_SUBTERRANEOS_DTTOS.csv", 0),
                       ("ANEXOS_SUPERFICIALES.csv", 1), ("ANEXOS_SUPERFICIALES_DTTOS.csv", 1)):
        rows = _read(z, name)
        h = [_plain(x) for x in next(rows)]
        col = {k: h.index(k) for k in ("CLAVE DE ESTADO", "CLAVE DE MUNICIPIO", "VOLUMEN ANUAL EN M3", "GRADOS LATITUD",
                                         "MINUTOS LATITUD", "SEGUNDOS LATITUD", "GRADOS LONGITUD", "MINUTOS LONGITUD",
                                         "SEGUNDOS LONGITUD") if k in h}
        if "CLAVE DE MUNICIPIO" not in col:
            continue  # this release's surface-district file has no municipio: cannot be placed safely
        i_aq = h.index("NOMBRE DE ACUIFERO HOMOLOGADO") if "NOMBRE DE ACUIFERO HOMOLOGADO" in h else None
        i_src = h.index("FUENTE DE ABASTECIMIENTO") if "FUENTE DE ABASTECIMIENTO" in h else None
        for r in rows:
            if r[col["CLAVE DE ESTADO"]].strip().zfill(2) != ENT:
                continue
            lat = _dms(r[col["GRADOS LATITUD"]], r[col["MINUTOS LATITUD"]], r[col["SEGUNDOS LATITUD"]])
            lon = _dms(r[col["GRADOS LONGITUD"]], r[col["MINUTOS LONGITUD"]], r[col["SEGUNDOS LONGITUD"]])
            if lat is None or lon is None or not inside.contains(Point(-lon, lat)):
                continue  # no coordinates = cannot tell whether it is in the new municipio
            use, holder, date = titles.get(r[0], ("otros", "", ""))
            pts.append({"lat": lat, "lon": -lon if lon else None, "kind": kind, "use": use, "holder": holder,
                        "date": date, "vol": _f(r[col["VOLUMEN ANUAL EN M3"]]) or 0.0,
                        "aq": _plain(r[i_aq]).title() if i_aq is not None and r[i_aq].strip() not in ("", "SIN DATO") else None,
                        "src": _plain(r[i_src]).lower() if i_src is not None else None, "district": name.endswith("DTTOS.csv")})

    if not pts:
        manifest.add(Provenance(id="conagua_repda", name="REPDA (títulos de agua)", url=ZENODO_PAGE,
                                license="Términos de Libre Uso MX", publisher="CONAGUA", vintage=snap,
                                status="unavailable", notes=f"no rows inside municipio {CVE_MUN}"))
        return {}

    from shapely.strtree import STRtree
    geoms = [a["geom"] for a in agebs]
    tree = STRtree(geoms)
    per = defaultdict(lambda: [0, 0.0])
    aq_names = sorted({p["aq"] for p in pts if p["aq"]})
    rows, unplaced = [], 0
    uses, kinds, aquifers, holders = Counter(), Counter(), defaultdict(lambda: [0, 0.0]), Counter()
    spelling: dict[str, Counter] = defaultdict(Counter)
    for p in pts:
        uses[p["use"]] += p["vol"]
        kinds[p["kind"]] += 1
        if p["aq"]:
            aquifers[p["aq"]][0] += 1
            aquifers[p["aq"]][1] += p["vol"]
        named = is_entity(p["holder"])
        if named:
            k = holder_key(p["holder"])
            holders[k] += p["vol"]
            spelling[k][re.sub(r"\s+", " ", p["holder"]).strip(" ,")] += 1
        if p["lat"] is None or not (BBOX[0] < p["lat"] < BBOX[2] and BBOX[1] < p["lon"] < BBOX[3]):
            unplaced += 1
            continue
        nd = 4 if named else 3  # private people: ~100 m, never the exact spot
        lon, lat = round(p["lon"], nd), round(p["lat"], nd)
        for i in tree.query(Point(lon, lat), predicate="intersects"):
            per[agebs[int(i)]["cvegeo"]][0] += 1
            per[agebs[int(i)]["cvegeo"]][1] += p["vol"]
            break
        # compact rows: [lon, lat, kind, use, m3/year, aquifer index or -1, holder or "", registration year, district]
        rows.append([lon, lat, p["kind"], USES.index(p["use"]), round(p["vol"]), aq_names.index(p["aq"]) if p["aq"] else -1,
                     p["holder"].strip() if named else "", p["date"][:4], 1 if p["district"] else 0])
    rows.sort(key=lambda r: -r[4])  # biggest first: they win symbol collisions on the map
    write_json(OUT / "water.json", {"uses": USES, "kinds": KINDS, "aquifers": aq_names,
                                    "cols": ["lon", "lat", "k", "u", "v", "aq", "h", "y", "d"], "rows": rows})
    for a in agebs:
        n, v = per.get(a["cvegeo"], (0, 0.0))
        a.update(a_n=n, a_vol=round(v))

    last_reg = max((p["date"] for p in pts if p["date"]), default="")
    total = sum(p["vol"] for p in pts)
    manifest.add(Provenance(
        id="conagua_repda", name="REPDA — Registro Público de Derechos de Agua", url=ZENODO_PAGE,
        license="Términos de Libre Uso MX (datos de CONAGUA); documentación del archivo CC BY 4.0",
        publisher="CONAGUA (copia íntegra en Zenodo, Gómez-Arias y Moctezuma)",
        vintage=f"corte {snap} (último registro {last_reg})",
        notes=f"{len(pts)} pozos y tomas dentro del municipio {CVE_MUN}, {unplaced} sin coordenadas válidas. Volúmenes = lo que "
              "autoriza cada título al año, no lo que se bombea. Personas físicas sin nombre y con ubicación redondeada."))
    print(f"  REPDA {snap}: {len(pts)} points ({kinds[0]} wells, {kinds[1]} intakes), {total / 1e6:.1f} hm³/year, "
          f"{unplaced} without coordinates")
    return {
        "snapshot": snap, "last_registration": last_reg, "n": len(pts), "n_wells": kinds[0], "n_intakes": kinds[1],
        "hm3": round(total / 1e6, 1), "uses": {u: round(uses[u] / 1e6, 2) for u in USES},
        "aquifers": sorted(([k, n, round(v / 1e6, 2)] for k, (n, v) in aquifers.items()), key=lambda x: -x[2]),
        "top": [[spelling[h].most_common(1)[0][0], round(v / 1e6, 2)] for h, v in holders.most_common(8)],
        "particular_hm3": round(sum(p["vol"] for p in pts if not is_entity(p["holder"])) / 1e6, 1),
    }


def _drought(manifest: Manifest) -> dict:
    try:
        path = fetch(SMN_URL, "smn_sequia_municipios.xlsx", max_age_days=6)
        import openpyxl
        ws = openpyxl.load_workbook(path, read_only=True)["MUNICIPIOS"]
        it = ws.iter_rows(values_only=True)
        head = next(it)
        row = next(r for r in it if str(r[0]).strip().zfill(5) == CVE_MUN)
    except (SourceUnavailable, StopIteration, KeyError, ValueError, zipfile.BadZipFile) as e:
        print(f"  ! drought monitor unavailable: {e}")
        manifest.add(Provenance(id="smn_sequia", name="Monitor de Sequía de México", url=SMN_URL,
                                license="Términos de Libre Uso MX", publisher="SMN / CONAGUA", vintage="?",
                                status="unavailable", notes=str(e)))
        return {}
    series = []
    for i, d in enumerate(head):
        if not hasattr(d, "date"):
            continue
        v = (str(row[i]).strip().upper() if i < len(row) and row[i] is not None else "") or "sin"
        if v not in DROUGHT:
            continue  # unknown code: leave it out rather than guess
        series.append([d.date().isoformat(), DROUGHT.index(v)])
    if not series:
        return {}
    cur = series[-1]
    since = cur[0]
    for d, lv in reversed(series):
        if lv != cur[1]:
            break
        since = d
    last_year = [lv for d, lv in series if d > f"{int(cur[0][:4]) - 1}{cur[0][4:]}"]
    worst = max(series, key=lambda x: (x[1], x[0]))
    manifest.add(Provenance(
        id="smn_sequia", name="Monitor de Sequía de México — tabla municipal", url=SMN_URL,
        license="Términos de Libre Uso MX", publisher="SMN / CONAGUA", vintage=f"al {cur[0]}",
        notes="Cada 15 días desde 2003. Celda vacía = sin sequía (según la hoja NOTAS del archivo)."))
    print(f"  drought: {DROUGHT[cur[1]]} on {cur[0]} (since {since}), {len(series)} reports")
    return {"date": cur[0], "level": cur[1], "since": since, "worst_year": max(last_year) if last_year else None,
            "worst_ever": worst, "series": series[-72:]}  # last ~3 years for the sparkline


def build_water(manifest: Manifest, agebs: list[dict], area) -> dict:
    rights = _repda(manifest, agebs, area)
    drought = _drought(manifest)
    if not rights and not drought:
        manifest.layer("water", "unavailable", ["conagua_repda", "smn_sequia"])
        return {}
    srcs = [s for s, ok in (("conagua_repda", rights), ("smn_sequia", drought)) if ok]
    manifest.layer("water", "ok" if rights and drought else "partial", srcs)
    return {"rights": rights or None, "drought": drought or None}
