# TODO — hosting and analytics setup

Steps to finish when the site goes live at `cherrios.jalmeida.dev`.

## Google Tag Manager (container `GTM-P3XKB934`, already in `index.html`)

- [ ] Create a GA4 property at analytics.google.com and a **Web** data stream for `cherrios.jalmeida.dev`;
      copy its Measurement ID (`G-…`).
- [ ] In GTM, add a **Google tag** with that `G-…` ID, trigger **All Pages**.
- [ ] Add the app's custom events (pushed to `dataLayer` by `src/analytics.ts`):
  - [ ] One **Custom Event** trigger per name: `cambio_modo`, `abrir_barrio`, `ver_ficha_punto`,
        `cambio_estilo`, `cambio_epoca` (or one trigger with regex
        `^(cambio_modo|abrir_barrio|ver_ficha_punto|cambio_estilo|cambio_epoca)$`).
  - [ ] **Data Layer Variables** for the event parameters you want (check `src/analytics.ts` for the
        names, e.g. `tipo` on `ver_ficha_punto`).
  - [ ] A **GA4 Event** tag with event name `{{Event}}`, sending those parameters, fired by the trigger(s).
  - [ ] Register the parameters as **custom dimensions** in GA4 (Admin → Custom definitions) so they
        show up in reports.
- [ ] Optional: add a trigger condition `Page Hostname equals cherrios.jalmeida.dev` so copies of the
      site on other domains aren't counted.
- [ ] **Submit / Publish** the GTM container (nothing is collected until it is published).

## Cloudflare (Workers static assets, free plan)

- [ ] `npx wrangler login` (or create an API token with "Edit Cloudflare Workers" permissions).
- [ ] `npm run build`, then `CLOUDFLARE_ACCOUNT_ID=<your account id> npx wrangler deploy`
      (worker name `mapa-cherrios`, see `wrangler.toml`).
- [ ] Attach the custom domain `cherrios.jalmeida.dev` to the worker (Workers → mapa-cherrios →
      Settings → Domains & Routes), with `jalmeida.dev` on Cloudflare DNS.
- [ ] Update the account name/comment in `wrangler.toml` and `AGENTS.md` (still say "vinc").

## GitHub Action (weekly refresh)

- [ ] Add repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`
      (optional `PC_SDK_SUBSCRIPTION_KEY` for Planetary Computer).
- [ ] Keep the repo **public** so Actions minutes stay free.
- [ ] Run the workflow once by hand (Actions → weekly refresh → Run workflow) to check it deploys.

## Verify

- [ ] Open the live site with GTM **Preview** (tagassistant.google.com) and click through modes,
      a barrio, a point and the style/era switches; each event should fire.
- [ ] Check GA4 **Realtime** shows the visit and events (GTM is skipped on `localhost`).
