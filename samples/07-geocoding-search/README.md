# 07 - Address search, reverse geocoding and batch geocoding

A map of downtown Denver with three geocoding jobs:

- **Search:** the `<arcgis-search>` component in the map's top-right corner. Type an address, pick a suggestion, and the map zooms to it.
- **Reverse geocode:** click anywhere on the map. `locationToAddress` returns the nearest street address and the side panel shows it.
- **Batch geocode:** the **Geocode the list** button sends the ten addresses in `public/data/capitols.csv` to the geocoding service in one
  `addressesToLocations` request (REST `geocodeAddresses`). Each result goes on the map with its match score, and the table lists them
  lowest score first, so the weakest matches are at the top.

Episode: *Address Search and Reverse Geocoding in JS (ArcGIS JS 5.2)* on the All Things Spatial YouTube channel.

Built with ArcGIS Maps SDK for JavaScript 5.2.7 (`@arcgis/core` + `@arcgis/map-components`), Calcite 5.2.1 and Vite.

## You need an API key

Geocoding is an ArcGIS location service, and it needs an access token.

1. Create a free ArcGIS Location Platform account.
2. Create an API key with these privileges: **geocoding (not stored)** for search and reverse geocoding, **geocoding (stored)** for the
   batch button, and **basemaps**.
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

## Cost: why the batch button is capped

Search and reverse geocoding are **geocodes (not stored)**: they have a monthly free tier on Location Platform, and the
results may be shown on the map but not saved. Batch geocoding is billed as **batch geocodes (stored)**, with no free tier
(the pricing page lists $4 per 1,000 geocodes when this sample was written), so your account must allow paid usage.
It also needs the geocoding (stored) privilege on your key; without it the service answers HTTP 403 ("User does not
have permissions to store geocoding results") and the panel shows the error.

Every click on **Geocode the list** geocodes every row again. The sample reads at most 25 rows (`MAX_ROWS` in
`src/main.js`) so a long file cannot run up a bill by accident. Check the current prices before you raise it.

## Without a key

With no `VITE_ARCGIS_TOKEN`, the app still loads: it shows a basemap, an "Add your key" notice, the address list with
no scores, a disabled batch button and no search box, so no geocoding request is sent. This is also how CI runs the sample.

## Keep the key out of git

- `.env.local` is git-ignored. Only `.env.example` (with an empty value) is committed.
- Vite inlines every `VITE_*` variable into the built JavaScript. Anyone who loads a build made with your key can read
  it, so never deploy such a build unless the key is referrer-restricted.

## Data: `public/data/capitols.csv`

Ten state capitol buildings. Each street address was copied from an official state website on 2026-11-22:

| Row | Source |
|---|---|
| Colorado | https://content.leg.colorado.gov/visit-learn |
| Texas | https://tspb.texas.gov/plan/hours/hours.html |
| California | https://capitolmuseum.ca.gov/visit/ |
| Washington | https://capitol.wa.gov/visit/getting-here-directions-parking |
| Utah | https://utahstatecapitol.utah.gov/contact/ |
| Minnesota | https://www.mnhs.org/capitol/visit/directions |
| Wisconsin | https://legis.wisconsin.gov/about/visit |
| Georgia | https://georgia.gov/locations/state-capitol-location |
| Arizona | https://azcapitolmuseum.gov/contact-us/ |
| Oregon | https://www.oregonlegislature.gov/CapitolOffices |

## Docs

- Search component: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-search/
- locator (`locationToAddress`, `addressesToLocations`): https://developers.arcgis.com/javascript/latest/references/core/rest/locator/
- Reverse geocode (REST, `featureTypes`): https://developers.arcgis.com/rest/geocode/reverse-geocode/
- Geocode addresses (REST batch operation): https://developers.arcgis.com/rest/geocode/geocode-addresses/
- Batch geocoding guide: https://developers.arcgis.com/documentation/mapping-and-location-services/geocoding/batch-geocoding/
- Create an API key: https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/tutorials/create-an-api-key/location-platform/
- Location Platform pricing: https://location.arcgis.com/pricing/
- Vite env variables: https://vite.dev/guide/env-and-mode

## License

MIT (see the repository LICENSE).
