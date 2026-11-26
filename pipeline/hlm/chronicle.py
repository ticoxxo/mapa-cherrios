"""La Gaceta: weekly snapshots (public/data/history.json) and the entries the app prints
(public/data/chronicle.json). Every sentence is built from numbers in the snapshots."""
from __future__ import annotations

import datetime as dt
import json
import re
from collections import Counter

from .common import OUT, PLACE, TODAY, write_json

GROUP_ES = {"ave": ("ave", "aves"), "rep": ("reptil", "reptiles"), "mam": ("mamífero", "mamíferos"),
            "ins": ("insecto o araña", "insectos y arañas"), "otr": ("otro animal", "otros animales")}
MAX_ENTRIES = 40


def _fmt(n: int) -> str:
    return f"{n:,}"


def _plural(g: str, n: int) -> str:
    return f"{_fmt(n)} {GROUP_ES[g][0] if n == 1 else GROUP_ES[g][1]}"


DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]


def _day(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"el {DAYS[d.weekday()]} {d.day} de {MONTHS[d.month - 1]}"


def _realm_ndvi(agebs, key):
    acc = {}
    for a in agebs:
        v = a.get(key)
        if v is None:
            continue
        s, w = acc.get(a["realm"], (0.0, 0.0))
        acc[a["realm"]] = (s + v * a["area_km2"], w + a["area_km2"])
    return {k: s / w for k, (s, w) in acc.items() if w > 0}


def _green_entries(green, agebs, realms, prev, week_key):
    by_id = {r["id"]: r for r in realms}
    name = lambda rid: by_id[rid].get("name") or by_id[rid].get("title")  # noqa: E731
    now = _realm_ndvi(agebs, "ndvi")
    out = []
    if green.get("city_ndvi_ago"):
        d = 100 * (green["city_ndvi"] / green["city_ndvi_ago"] - 1)
        ago = _realm_ndvi(agebs, "ndvi_ago")
        ch = {k: 100 * (now[k] / ago[k] - 1) for k in now if ago.get(k)}
        text = ("La ciudad está " + (f"{abs(d):.0f}% más verde" if d >= 0.5 else f"{abs(d):.0f}% menos verde" if d <= -0.5
                else "igual de verde") + " que en estas mismas fechas del año pasado.")
        if ch:
            lo, hi = min(ch, key=ch.get), max(ch, key=ch.get)
            if ch[lo] < -1:
                text += f" Donde más bajó: {name(lo)} ({ch[lo]:.0f}%)."
            if ch[hi] > 1:
                text += f" Donde más subió: {name(hi)} (+{ch[hi]:.0f}%)."
        out.append({"week": week_key, "date": TODAY, "kind": "green_year", "title": "¿Qué tan verde está la ciudad?",
                    "es": text, "source": "Satélites Sentinel-2 (Copernicus)"})
    if prev and prev.get("realm_ndvi"):
        ch = {k: 100 * (now[k] / prev["realm_ndvi"][k] - 1) for k in now if prev["realm_ndvi"].get(k)}
        if ch:
            k = max(ch, key=lambda x: abs(ch[x]))
            if abs(ch[k]) >= 2:
                out.append({"week": week_key, "date": TODAY, "kind": "green_week", "title": "El verde esta semana",
                            "es": f"Esta semana el verde {'subió' if ch[k] > 0 else 'bajó'} {abs(ch[k]):.0f}% en {name(k)}.",
                            "source": "Satélites Sentinel-2 (Copernicus)"})
    return out, now


WORK_ES = {"tienda": "tiendas y comercios", "comida": "lugares de comida y hoteles", "taller": "talleres y oficios",
           "oficina": "oficinas y gobierno", "fabrica": "fábricas, obras y bodegas",
           "escuela": "escuelas, clínicas y lugares de diversión"}


def _work_entries(work, agebs, realms, prev_weeks, week_key):
    src = f"INEGI, directorio de negocios (DENUE {work['edition']})"
    last = next((w for w in reversed(prev_weeks) if w.get("work_total")), None)
    text = (f"INEGI actualizó su directorio de negocios: en el municipio hay {_fmt(work['total'])} lugares de chamba"
            if last else f"Según el directorio de negocios de INEGI, en el municipio hay {_fmt(work['total'])} lugares de chamba")
    if last:
        d = work["total"] - last["work_total"]
        text += f" ({_fmt(abs(d))} {'más' if d >= 0 else 'menos'} que en la versión anterior)."
    else:
        g, n = max(work["groups"].items(), key=lambda kv: kv[1])
        text += f". Lo que más hay: {WORK_ES[g]} ({_fmt(n)})."
    out = [{"week": week_key, "date": TODAY, "kind": "work", "title": f"La chamba en {PLACE}", "es": text, "source": src}]
    ny = work.get("new_year") or {}
    if ny.get("total"):
        g, n = max(ny["groups"].items(), key=lambda kv: kv[1])
        out.append({"week": week_key, "date": TODAY, "kind": "work_new", "title": "Negocios nuevos en la lista",
                    "es": f"En {ny['year']} se agregaron {_fmt(ny['total'])} negocios al directorio. "
                          f"Los más: {WORK_ES[g]} ({_fmt(n)}).", "source": src})
    by_id = {r["id"]: r for r in realms}
    per = Counter()
    for a in agebs:
        per[a["realm"]] += a.get("j_emp") or 0
    if per:
        rid, jobs = per.most_common(1)[0]
        r = by_id.get(rid, {})
        out.append({"week": week_key, "date": TODAY, "kind": "work_top", "title": "Donde más se chambea",
                    "es": f"{r.get('name') or r.get('title')} es la zona con más trabajo: cerca de {_fmt(round(jobs, -3))} "
                          "empleos (calculado con el tamaño de cada negocio).", "source": src})
    return out


DROUGHT_ES = ["sin sequía", "anormalmente seco (todavía no es sequía)", "en sequía moderada", "en sequía severa",
              "en sequía extrema", "en sequía excepcional"]
USE_ES = {"agricola": "el campo", "urbano": "la ciudad (agua potable)", "industria": "la industria",
          "ganado": "el ganado", "otros": "otros usos"}


def _name(holder: str) -> str:
    from .work import _title
    t = _title(holder).replace("N° ", "n.º ")
    return re.sub(r"\b(?:[A-Za-z]\.){2,}[A-Za-z]?\.?|\b[A-Za-z]\.\s?[A-Za-z]\.?$", lambda m: m.group(0).upper(), t)


def _mx_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.day} de {MONTHS[d.month - 1]} de {d.year}"


def _water_entries(water, prev_weeks, chron, week_key):
    out = []
    dr, rt = water.get("drought"), water.get("rights")
    if dr:
        last = next((w.get("drought_level") for w in reversed(prev_weeks) if w.get("drought_level") is not None), None)
        if last != dr["level"] or not any(e.get("kind") == "water_drought" for e in chron["entries"]):
            text = f"El Monitor de Sequía dice que {PLACE} está {DROUGHT_ES[dr['level']]} (reporte del {_mx_date(dr['date'])})."
            if last is not None and last != dr["level"]:
                text += " Antes estaba " + DROUGHT_ES[last].split(" (")[0] + "."
            elif dr["since"] != dr["date"]:
                text += f" Así sigue desde el {_mx_date(dr['since'])}."
            out.append({"week": week_key, "date": TODAY, "kind": "water_drought", "title": "¿Hay sequía?",
                        "es": text, "source": "Monitor de Sequía de México (SMN / CONAGUA)"})
    if rt:
        last = next((w.get("water_snapshot") for w in reversed(prev_weeks) if w.get("water_snapshot")), None)
        if last != rt["snapshot"] or not any(e.get("kind") == "water" for e in chron["entries"]):
            y, m = rt["snapshot"].split("-")
            src = f"CONAGUA, Registro Público de Derechos de Agua (corte {MONTHS[int(m) - 1]} {y})"
            tot = sum(rt["uses"].values()) or 1
            u1, u2 = sorted(rt["uses"], key=lambda k: -rt["uses"][k])[:2]
            out.append({"week": week_key, "date": TODAY, "kind": "water", "title": "¿Quién tiene el agua?",
                        "es": f"En el municipio hay permiso para sacar {rt['hm3']:,.0f} millones de m³ de agua al año, de "
                              f"{_fmt(rt['n'])} pozos y tomas. El {100 * rt['uses'][u1] / tot:.0f}% es para {USE_ES[u1]} y el "
                              f"{100 * rt['uses'][u2] / tot:.0f}% para {USE_ES[u2]}.", "source": src})
            if rt.get("top"):
                (h1, v1), *rest = rt["top"]
                text = f"Quien tiene permiso para más agua: {_name(h1)} ({v1:,.0f} millones de m³ al año)."
                if rest:
                    text += f" Le sigue {_name(rest[0][0])} ({rest[0][1]:,.1f} millones)."
                out.append({"week": week_key, "date": TODAY, "kind": "water_top", "title": "Los que más agua pueden sacar",
                            "es": text, "source": src})
    return out



def _keep(entries, new_entries, week_key):
    """Entries to keep when re-running a week: only the families just rewritten (wildlife, heat, green,
    weather, work, water) are replaced, so a partial run never deletes the rest of this week's Gaceta."""
    fam = lambda e: e.get("kind", "").split("_")[0]  # noqa: E731
    redone = {fam(e) for e in new_entries}
    return [e for e in entries if not (e.get("week") == week_key and fam(e) in redone)]


def update(wild: dict, heat: dict | None = None, weather: dict | None = None, agebs: list | None = None,
           realms: list | None = None, green: dict | None = None, work: dict | None = None, water: dict | None = None):
    hist_path, chron_path = OUT / "history.json", OUT / "chronicle.json"
    history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {"weeks": []}
    chron = json.loads(chron_path.read_text(encoding="utf-8")) if chron_path.exists() else {"entries": []}
    if not (wild or weather or green or work or water):
        return
    week_key = "%d-W%02d" % dt.date.fromisoformat(TODAY).isocalendar()[:2]
    same = next((w for w in history["weeks"] if w["week"] == week_key), {})
    snap = {**same, "week": week_key, "date": TODAY}  # a partial re-run keeps this week's other numbers
    if wild:
        snap.update(wildlife_total=wild["total"], wildlife_new=wild["week"]["new"], wildlife_groups=wild["week"]["groups"])
    if weather:
        snap.update(tmax_week=weather["week_max"]["tmax"], tmax_week_date=weather["week_max"]["date"])
    prev_weeks = [w for w in history["weeks"] if w["week"] != week_key]
    prev = prev_weeks[-1] if prev_weeks else None
    new_entries = []
    if green and agebs and realms:
        ge, realm_ndvi = _green_entries(green, agebs, realms, prev, week_key)
        new_entries += ge
        snap.update(city_ndvi=green["city_ndvi"], realm_ndvi={k: round(v, 4) for k, v in realm_ndvi.items()})
    if work:
        snap.update(work_edition=work["edition"], work_total=work["total"])
        last_ed = next((w.get("work_edition") for w in reversed(prev_weeks) if w.get("work_edition")), None)
        if last_ed != work["edition"] or not any(e.get("kind") == "work" for e in chron["entries"]):
            new_entries += _work_entries(work, agebs or [], realms or [], prev_weeks, week_key)
    if water:
        new_entries += _water_entries(water, prev_weeks, chron, week_key)
        if water.get("drought"):
            snap.update(drought_level=water["drought"]["level"], drought_date=water["drought"]["date"])
        if water.get("rights"):
            snap.update(water_snapshot=water["rights"]["snapshot"], water_hm3=water["rights"]["hm3"])
    weeks = sorted(prev_weeks + [snap], key=lambda w: w["week"])
    history["weeks"] = weeks[-104:]
    write_json(hist_path, history, compact=False)

    if weather:
        wm = weather["week_max"]
        text = f"El día más caliente de la semana fue {_day(wm['date'])}, con {wm['tmax']:.0f} °C de máxima."
        if prev and prev.get("tmax_week") is not None:
            d = wm["tmax"] - prev["tmax_week"]
            text += (f" {abs(d):.0f} °C más que la semana pasada." if d >= 1 else
                     f" {abs(d):.0f} °C menos que la semana pasada." if d <= -1 else " Casi igual que la semana pasada.")
        new_entries.append({"week": week_key, "date": TODAY, "kind": "weather", "title": "El calor de la semana",
                            "es": text, "source": "NASA POWER (temperatura del aire, toda la ciudad)"})
    if heat and agebs and realms:
        by_id = {r["id"]: r for r in realms}
        top = heat["hottest"][0]
        a = next(x for x in agebs if x["cvegeo"] == top["cvegeo"])
        r = by_id[a["realm"]]
        where = r.get("name") or r.get("title")
        new_entries.append({"week": week_key, "date": TODAY, "kind": "heat", "title": "El barrio más caliente",
                            "es": f"En verano, el suelo de un barrio de {where} llega a {top['lst']:.0f} °C en promedio. "
                                  f"El más fresco de la ciudad se queda en {heat['ageb_min']:.0f} °C.",
                            "source": "Satélites Landsat, veranos " + f"{heat['summers'][0]}–{heat['summers'][-1]}"})
    if not wild:
        kept = _keep(chron["entries"], new_entries, week_key)
        chron["entries"] = (new_entries + kept)[:MAX_ENTRIES]
        write_json(chron_path, chron, compact=False)
        return
    w = wild["week"]
    parts = [_plural(g, n) for g, n in sorted(w["groups"].items(), key=lambda kv: -kv[1])]
    text = f"Esta semana la gente reportó {_fmt(w['new'])} {'animal' if w['new'] == 1 else 'animales'} en {PLACE}"
    text += f": {', '.join(parts[:-1]) + ' y ' + parts[-1] if len(parts) > 1 else parts[0]}." if parts else "."
    if prev:
        d = w["new"] - prev.get("wildlife_new", w["new"])
        text += (f" {_fmt(abs(d))} más que la semana pasada." if d > 0 else
                 f" {_fmt(abs(d))} menos que la semana pasada." if d < 0 else " Igual que la semana pasada.")
    new_entries.insert(0, {"week": week_key, "date": TODAY, "kind": "wildlife", "title": "Animales de la semana",
                           "es": text, "source": "iNaturalist"})
    if w["top"]:
        new_entries.append({"week": week_key, "date": TODAY, "kind": "wildlife_top", "title": "Los más vistos",
                            "es": "Lo más fotografiado esta semana: " + ", ".join(w["top"]) + ".",
                            "source": "iNaturalist"})
    for common, sci in w["firsts"]:
        new_entries.append({"week": week_key, "date": TODAY, "kind": "wildlife_first", "title": "¡Primera vez en el mapa!",
                            "es": f"Por primera vez aparece en el mapa: {common}" + (f" ({sci})" if sci and sci != common else "") + ".",
                            "source": "iNaturalist"})
    kept = _keep(chron["entries"], new_entries, week_key)
    chron["entries"] = (new_entries + kept)[:MAX_ENTRIES]
    write_json(chron_path, chron, compact=False)
