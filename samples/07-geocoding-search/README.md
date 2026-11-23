# 07 - Address search, reverse geocoding and geocoding a list

A map of downtown Denver with three geocoding jobs:

- **Search:** the `<arcgis-search>` component in the map's top-right corner. Type an address, pick a suggestion, and the map zooms to it.
- **Reverse geocode:** click anywhere on the map. `locationToAddress` returns the nearest street address and the side panel shows it.
- **Geocode a list:** the **Geocode the list** button geocodes the ten addresses in `public/data/capitols.csv` one at a time:
  one `addressToLocations` request per address (REST `findAddressCandidates`) with `forStorage: false`. Each result goes on the map
  with its match score, and the table lists them lowest score first, so the weakest matches are at the top.

Episode: *Address Search and Reverse Geocoding in JS (ArcGIS JS 5.2)* on the All Things Spatial YouTube channel.

Built with ArcGIS Maps SDK for JavaScript 5.2.7 (`@arcgis/core` + `@arcgis/map-components`), Calcite 5.2.1 and Vite.

## You need an API key

Geocoding is an ArcGIS location service, and it needs an access token.

1. Create a free ArcGIS Location Platform account.
2. Create an API key with these privileges: **geocoding (not stored)** for search, reverse geocoding and the list button, and
   **basemaps**.
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

## Not stored, one address at a time

Search, reverse geocoding and the list button are all **geocodes (not stored)**: they have a monthly free tier on Location
Platform, and the results may be shown on the map but not saved (`forStorage` is `false`, the default).

True batch geocoding is a different job. One `geocodeAddresses` request (`addressesToLocations` in the SDK) sends many addresses
at once and returns results you are allowed to store, in a database for example. Batch geocoding with stored results needs the
separate **geocoding (stored)** privilege for production apps, and it is billed as stored geocoding with no free tier (the
pricing page listed $4 per 1,000 geocodes on 2026-11-22). This sample's key has only geocoding (not stored), so it loops over
the list instead. Without the stored privilege, `geocodeAddresses` answers HTTP 403 ("User does not have permissions to store
geocoding results").

Every click on **Geocode the list** geocodes every row again, one request each. The sample reads at most 25 rows (`MAX_ROWS` in
`src/main.js`) so a long file cannot use up your free tier by accident.

## Without a key

With no `VITE_ARCGIS_TOKEN`, the app still loads: it shows a basemap, an "Add your key" notice, the address list with
no scores, a disabled list button and no search box, so no geocoding request is sent. This is also how CI runs the sample.

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
- locator (`addressToLocations`, `locationToAddress`): https://developers.arcgis.com/javascript/latest/references/core/rest/locator/
- `forStorage` (AddressToLocationsParameters): https://developers.arcgis.com/javascript/latest/references/core/rest/support/AddressToLocationsParameters/
- Find address candidates (REST, `forStorage`): https://developers.arcgis.com/rest/geocode/find-address-candidates/
- Reverse geocode (REST, `featureTypes`): https://developers.arcgis.com/rest/geocode/reverse-geocode/
- Geocode addresses (REST batch operation, stored privilege): https://developers.arcgis.com/rest/geocode/geocode-addresses/
- Batch geocoding guide: https://developers.arcgis.com/documentation/mapping-and-location-services/geocoding/batch-geocoding/
- Create an API key: https://developers.arcgis.com/documentation/security-and-authentication/api-key-authentication/tutorials/create-an-api-key/location-platform/
- Location Platform pricing: https://location.arcgis.com/pricing/
- Vite env variables: https://vite.dev/guide/env-and-mode

## License

MIT (see the repository LICENSE).
