"""Shared helpers: paths, cached downloads, provenance records, geometry utils."""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline"
CACHE = Path(os.environ.get("HLM_CACHE", PIPELINE / ".cache"))
MANUAL = PIPELINE / "manual"  # hand-downloaded files when a portal blocks scripts
OUT = Path(os.environ.get("HLM_OUT", ROOT / "public" / "data"))

# Juan José Ríos, Sinaloa: municipio 25-020 since the 2021 decree (INEGI Marco Geoestadístico 2025).
ENT, MUN = "25", "020"
PLACE = "Juan José Ríos"
# Municipio bbox (S, W, N, E) used for OSM, iNaturalist and satellite queries
BBOX = (25.44, -109.13, 25.96, -108.64)
CITY_CENTER = (25.757, -108.822)

# "Antes de ser Municipio": in the 2020 census the town belonged to Guasave (011) and El Estero to Ahome (001).
# (municipio, localidad) pairs of the 2020 census / Marco Geoestadístico 2020.
ANTES_LOCS = (("011", "0138"), ("001", "0136"))
ANTES_CITY = "0138"
OUT_ANTES = OUT / "antes"

UA = "mapa-cherrios-pipeline/0.1 (+open data pipeline)"

TODAY = dt.date.today().isoformat()


class SourceUnavailable(Exception):
    """Raised when a source cannot be fetched and no manual copy exists."""


@dataclass
class Provenance:
    id: str
    name: str
    url: str
    license: str
    publisher: str
    vintage: str  # year / edition of the data itself
    retrieved: str = TODAY
    status: str = "ok"  # ok | unavailable | partial
    notes: str = ""
    modeled: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class Manifest:
    generated: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    sources: dict = field(default_factory=dict)
    layers: dict = field(default_factory=dict)

    def add(self, p: Provenance):
        self.sources[p.id] = p.to_dict()

    def layer(self, name: str, status: str, sources: list[str], **extra):
        self.layers[name] = {"status": status, "sources": sources, **extra}


def fetch(url: str, name: str, *, max_age_days: float = 30, retries: int = 4,
          data: dict | None = None, timeout: int = 180) -> Path:
    """Download `url` into the cache (reusing a fresh copy) and return its path.

    Falls back to pipeline/manual/<name> when the network fetch fails, so that
    portals that block automated clients can be supplied by hand.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / name
    if dest.exists() and (time.time() - dest.stat().st_mtime) < max_age_days * 86400:
        return dest
    manual = MANUAL / name
    body = urllib.parse.urlencode(data).encode() if data else None
    wait = 5
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                content = r.read()
            ctype = r.headers.get("Content-Type", "")
            if b"Access Denied" in content[:600] and "html" in ctype.lower():
                raise SourceUnavailable(f"{url} answered 'Access Denied'")
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(content)
            tmp.replace(dest)
            return dest
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (401, 403, 404):
                break  # retrying will not help
        except Exception as e:  # noqa: BLE001 - network errors of every kind
            last_err = e
        print(f"  ! {name}: attempt {attempt + 1} failed ({last_err}); retrying in {wait}s")
        time.sleep(wait)
        wait *= 2
    if manual.exists():
        print(f"  → using manual copy {manual.relative_to(ROOT)}")
        return manual
    if dest.exists():
        print(f"  → using stale cached copy of {name}")
        return dest
    raise SourceUnavailable(f"{name}: {last_err}")


def write_json(path: Path, obj, *, compact=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.2f} MB)")


# ---------- geometry ----------

def round_coords(geom: dict, nd: int = 5) -> dict:
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], nd), round(c[1], nd)]
        return [r(x) for x in c]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def local_area_km2(geom) -> float:
    """Area of a lon/lat shapely geometry in km², via a local equirectangular
    projection centred on the town (error < 0.5 % at city scale)."""
    from shapely.ops import transform
    lat0 = math.radians(CITY_CENTER[0])
    kx = 111.320 * math.cos(lat0)
    ky = 110.574
    return transform(lambda x, y, z=None: (x * kx, y * ky), geom).area


def num(v):
    """Parse an INEGI cell: '*' (confidential) and 'N/D' become None."""
    if v is None:
        return None
    v = str(v).strip()
    if v in ("", "*", "N/D", "NA", "nan"):
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    return int(f) if f.is_integer() else f
