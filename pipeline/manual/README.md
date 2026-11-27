Hand-downloaded source files, used when a portal blocks scripted downloads (CONAPO / CONEVAL answer 403).

Committed here (national files trimmed to the two localities below, original header and columns kept):

- `imu_2020.csv`: CONAPO Índice de Marginación Urbana 2020 by AGEB (CC-BY 4.0), from
  <https://www.datos.gob.mx/dataset/indices_marginacion>.
- `grs_ageb_2020.csv`: CONEVAL Grado de Rezago Social 2020 by AGEB (CC-BY 4.0), from
  <https://www.datos.gob.mx/dataset/rezago_social>.

Both are 2020 products keyed by the 2020 AGEB codes, so they fill the Bienestar mode of the
**"Antes de ser Municipio"** view only (Juan José Ríos = Guasave `25011` localidad `0138`, El Estero = Ahome
`25001` localidad `0136`). A national download works as is; to keep the repo small, trim it to those rows
(keep the original header and columns) before committing it, so the weekly GitHub Action can use it.
Fallbacks for the Campo mode (used only when the live download fails):

- `siap_cierre_mun_<year>.csv`: SIAP Cierre de la producción agrícola por municipio (Términos de Libre Uso MX), from
  <https://nube.agricultura.gob.mx/datosAbiertos/Agricola.php>, trimmed to Sinaloa rows (`Idestado = 25`), original
  header, columns and ISO-8859-1 encoding kept. Refresh them when a new year is published.
- `usv7_25020.geojson`: the agricultural polygons of INEGI Uso del Suelo y Vegetación Serie VII, already clipped to
  municipio 25-020 by `hlm/campo.py` (the national zip is 317 MB). Written from `public/data/campo.geojson`.

Anything else in this folder is git-ignored. See ../README.md.
