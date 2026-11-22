# 06 - Turn-by-turn directions with the Directions component

A map of Denver with the `<arcgis-directions>` component in a Calcite side panel. Type two addresses, and the
component geocodes them, solves a driving route on the ArcGIS routing service, draws it, and lists every turn.

Episode: *Turn-by-Turn Directions in JavaScript (ArcGIS JS 5.2)* on the All Things Spatial YouTube channel.

Built with ArcGIS Maps SDK for JavaScript 5.2.7 (`@arcgis/core` + `@arcgis/map-components`), Calcite 5.2.1 and Vite.

## You need an API key

Routing and geocoding are ArcGIS location services, and they need an access token.

1. Create a free ArcGIS Location Platform account.
2. Create an API key with these privileges: **routing** (basic routes), **geocoding (not stored)** and **basemaps**.
3. Restrict the key to the referrers you run on: `http://localhost:5173/*` (dev) and `http://localhost:4173/*` (preview).
4. In this folder:

```sh
cp .env.example .env.local
# open .env.local and paste your key after VITE_ARCGIS_TOKEN=
npm ci
npm run dev
```

Vite serves the app on port 5173 and stops with an error if that port is busy (`strictPort`), so the app never
runs on a port your key does not allow.

## Cost

Basic routes have a monthly free tier on Location Platform (see the pricing page). Leave **Optimize order** off:
stop-optimized routes are billed per route with no free tier.

## Without a key

With no `VITE_ARCGIS_TOKEN`, the app still loads: it shows a basemap, an "Add your key" notice, and no Directions
component, so no routing or geocoding request is sent. This is also how CI runs the sample.

## Keep the key out of git

- `.env.local` is git-ignored. Only `.env.example` (with an empty value) is committed.
- Vite inlines every `VITE_*` variable into the built JavaScript. Anyone who loads a build made with your key can read
  it, so never deploy such a build unless the key is referrer-restricted.

## Docs

- Directions component: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-directions/
- RouteLayer: https://developers.arcgis.com/javascript/latest/references/core/layers/RouteLayer/
- Routing service (direct): https://developers.arcgis.com/rest/routing/route-service-direct/
- Create an API key: https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/tutorials/create-an-api-key/location-platform/
- Location Platform pricing: https://location.arcgis.com/pricing/
- Vite env variables: https://vite.dev/guide/env-and-mode

## License

MIT (see the repository LICENSE).
