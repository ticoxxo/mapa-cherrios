"""People: INEGI Censo de Población y Vivienda 2020, AGEB and block (manzana) tables."""
from __future__ import annotations

import csv
import io
import zipfile

from .common import ENT, MUN, Manifest, Provenance, fetch, num

URL = ("https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/"
       f"ageb_manzana/ageb_mza_urbana_{ENT}_cpv2020_csv.zip")

# census mnemonic -> short property name used in the app
FIELDS = {
    "POBTOT": "pop", "POBFEM": "fem", "POBMAS": "mas",
    "POB0_14": "a0_14", "POB15_64": "a15_64", "POB65_MAS": "a65",
    "GRAPROES": "school", "PEA": "pea", "POCUPADA": "employed",
    "PSINDER": "nohealth", "PDER_SS": "health",
    # Dwelling denominators (see the census data dictionary, fields 170–175):
    # - VPH_* counts INCLUDE dwellings without occupant information, so their base is VIVPARH_CV
    #   ("viviendas particulares habitadas con características"), never VIVPAR_HAB (which excludes them).
    # - "Casas con gente" shows TVIVPARHAB, the full count of inhabited private dwellings.
    # - Empty homes are a share of private dwellings (TVIVPAR), not of VIVTOT (which adds collective housing).
    "VIVTOT": "dwell", "TVIVPAR": "priv", "TVIVPARHAB": "homes", "VIVPARH_CV": "homes_cv",
    "VIVPAR_DES": "empty", "PROM_OCUP": "occ",
    "VPH_INTER": "h_inet", "VPH_AUTOM": "h_car", "VPH_PC": "h_pc",
    "VPH_AGUADV": "h_water", "VPH_DRENAJ": "h_drain", "VPH_TINACO": "h_tinaco", "VPH_CISTER": "h_cister",
}


def load_census(manifest: Manifest, locs: tuple[tuple[str, str], ...] | None = None):
    """Returns (ageb_stats, block_pop, totals) keyed by CVEGEO.

    `locs` = (municipio, localidad) pairs to keep (the "Antes de ser Municipio" view); otherwise the whole
    current municipio. Juan José Ríos became municipio 020 after 2020, so the 2020 census has no rows for it:
    the current view then gets empty results and shows "sin datos" for census modes.
    """
    path = fetch(URL, f"cpv2020_ageb_mza_{ENT}.zip", max_age_days=3650)
    manifest.add(Provenance(
        id="inegi_censo2020", name="Censo de Población y Vivienda 2020 — AGEB y manzana urbana",
        url=URL, license="INEGI Términos de libre uso de la información", publisher="INEGI",
        vintage="2020", notes="'*' cells (confidentiality, < 3 dwellings) are treated as missing, never as zero."))
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv") and "conjunto_de_datos" in n)
        text = z.read(name).decode("utf-8-sig")
    ageb, blocks, totals = {}, {}, {}
    for row in csv.DictReader(io.StringIO(text)):
        if locs:
            if (row["MUN"], row["LOC"]) not in locs:
                continue
        elif row["MUN"] != MUN:
            continue
        key = row["ENTIDAD"] + row["MUN"] + row["LOC"]
        if row["LOC"] == "0000":
            totals["municipio"] = {v: num(row[k]) for k, v in FIELDS.items()}
            continue
        if row["AGEB"] == "0000":
            totals[row["LOC"]] = {"name": row["NOM_LOC"], **{v: num(row[k]) for k, v in FIELDS.items()}}
            continue
        if row["MZA"] == "000":
            ageb[key + row["AGEB"]] = {v: num(row[k]) for k, v in FIELDS.items()}
        else:
            blocks[key + row["AGEB"] + row["MZA"]] = num(row["POBTOT"])
            # only block rows carry the real locality name (total rows say "Total ...")
            if row["LOC"] in totals and not row["NOM_LOC"].startswith("Total"):
                totals[row["LOC"]]["name"] = row["NOM_LOC"]
    if locs:  # the "area" is the sum of the kept localities
        locs_t = [v for k, v in totals.items() if k != "municipio"]
        # only counts add up; averages (schooling, occupants) are not summed
        totals["municipio"] = {f: (sum(v[f] for v in locs_t) if locs_t and all(v.get(f) is not None for v in locs_t)
                                   else None) for f in ("pop", "homes")}
    mpop = totals.get("municipio", {}).get("pop")
    print(f"  census: {len(ageb)} AGEBs, {len(blocks)} blocks, area pop {mpop if mpop is not None else 'sin datos'}")
    return ageb, blocks, totals


PCT_FIELDS = ("p_young", "p_old", "p_inet", "p_car", "p_pc", "p_water", "p_drain", "p_tinaco", "p_cister", "p_nohealth", "p_empty",
              "p_employed")


def check_ratios(agebs: list[dict]) -> None:
    """Stop the run if any share is impossible (outside 0–100 %): it means a wrong denominator."""
    bad = [(a["cvegeo"], k, a[k]) for a in agebs for k in PCT_FIELDS if a.get(k) is not None and not 0 <= a[k] <= 100]
    if bad:
        raise ValueError(f"{len(bad)} impossible percentages, e.g. {bad[:5]}")


def derive(stats: dict, area_km2: float) -> dict:
    """Ratios computed from census counts. Returns None where inputs are missing."""
    def pct(a, b):
        x, y = stats.get(a), stats.get(b)
        return round(100 * x / y, 1) if x is not None and y else None
    pop = stats.get("pop")
    return {
        "dens": round(pop / area_km2) if pop is not None and area_km2 > 0 else None,
        "p_young": pct("a0_14", "pop"), "p_old": pct("a65", "pop"),
        "p_inet": pct("h_inet", "homes_cv"), "p_car": pct("h_car", "homes_cv"), "p_pc": pct("h_pc", "homes_cv"),
        "p_water": pct("h_water", "homes_cv"), "p_drain": pct("h_drain", "homes_cv"),
        "p_tinaco": pct("h_tinaco", "homes_cv"), "p_cister": pct("h_cister", "homes_cv"),
        "p_nohealth": pct("nohealth", "pop"), "p_empty": pct("empty", "priv"),
        "p_employed": pct("employed", "pea"),
    }
