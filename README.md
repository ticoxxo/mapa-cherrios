# Hermosillo: El Mapa Vivo

A Norteño-style strategy-game map of Hermosillo, Sonora, built from real open data. Territories carry
ranch brands (*fierros*), map modes are silver *conchos*, and *La Gaceta* reports what changed. Every
figure has a cited source, and missing data is shown as "Datos no disponibles", never invented.
The interface is in Mexican Spanish only.

**Built so far:** pipeline + Territorio (base), Gente (Censo 2020) and Bienestar (CONAPO marginación urbana
2020, CONEVAL rezago social 2020), Fauna (iNaturalist, weekly), Calor (Landsat summer ground temperature + NASA POWER), Verde (Sentinel-2 + ESA WorldCover) and Chamba (INEGI DENUE), the HUD, the *ficha del barrio*, *La Gaceta*, legends and credits.
All seven modes are built.

**Live:** https://hermosillo-mapa-vivo.vinc-fdb.workers.dev (Cloudflare Workers static assets, account *vinc*).
Deploy by hand with `npm run build && npx wrangler deploy` (set `CLOUDFLARE_ACCOUNT_ID` to the vinc account).
The weekly GitHub Action refreshes the data and redeploys; it needs the repo secrets `CLOUDFLARE_API_TOKEN`
and `CLOUDFLARE_ACCOUNT_ID` (and optionally `PC_SDK_SUBSCRIPTION_KEY`).

```bash
npm install
npm run data      # runs the pipeline (needs uv) → public/data/
npm run dev       # http://localhost:5173
npm run build     # static site in dist/ (Cloudflare Pages: build `npm run build`, output `dist`)
```

- `pipeline/`: data pipeline (see `pipeline/README.md`)
- `DATA.md`: every dataset, update frequency, license and known gaps
- `src/`: Vite + React + TypeScript + MapLibre GL, fully custom style (no basemap tiles)

Keys: 1–7 switch modes, Esc closes the ficha. Zoom tiers: territorios (z < 12) → barrios/AGEB
(12–14.2) → manzanas (≥ 14.2, loaded lazily).

The interface is written for people who don't use maps or data tools: plain Mexican Spanish, a first-visit
"¿Cómo se usa?" card (the **?** button reopens it), and no technical terms on screen.

---

Based on the original [Hermosillo: El Mapa Vivo](https://github.com/jmsalcido/mapa-hermosillo) by jmsalcido.
