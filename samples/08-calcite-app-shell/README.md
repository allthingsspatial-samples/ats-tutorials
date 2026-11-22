# 08 A Full Map App Layout with Calcite

A complete app frame around a map, built only from Calcite Design System components and ArcGIS map components: a header, an action bar that opens side panels (Layers, Legend, About), an end panel with the details of the clicked feature, a dark-mode switch and a narrow-screen layout. No CSS framework. It goes with the ATS Build episode BLD-S02E04, "Build a Full Map App Layout with Calcite (ArcGIS JS 5.2)".

- Data: the USGS Earthquake Hazards Program GeoJSON summary feed, every earthquake of magnitude 2.5 or more in the past 7 days (https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson). The feed changes every few minutes, so the count you see will differ from the episode.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.2.7, `@esri/calcite-components` 5.2.1 (the version map-components 5.2.7 asks for). All pinned exactly. No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

## Layout (Shell slots)

```
calcite-shell
|-- slot="header"       calcite-navigation (title + theme action)
|-- slot="panel-start"  calcite-shell-panel
|     |-- slot="action-bar"  calcite-action-bar (Layers, Legend, About)
|     `-- calcite-panel x 3 (one per action)
|-- (default slot)      arcgis-map
`-- slot="panel-end"    calcite-shell-panel -> calcite-panel "Details" -> arcgis-feature
```

The shell slot decides where a shell panel goes. The shell panel's `position` and `layout` attributes are deprecated since Calcite 5.0 and are not used here. Shell also has `panel-top`, `panel-bottom`, `footer`, `dialogs`, `alerts` and `sheets` slots.

## Action bar wiring (`src/main.js`)

Each `calcite-action` has a `data-panel` name that matches one `calcite-panel`. `open(name)` marks that action `active`, shows its panel and hides the others (with the `hidden` attribute, so a hidden panel takes no space), and collapses the shell panel when nothing is open. Clicking the open action again closes it; so does the panel's own close button (`closable`, event `calcitePanelClose`).

`arcgis-layer-list`, `arcgis-legend` and `arcgis-feature` sit inside the panels, outside the map, and find the map through `reference-element="map"` (the map's id). A click on the map runs `hitTest` and puts the strongest earthquake under the cursor into `arcgis-feature`; the map's own popup is turned off (`popupDisabled`).

## Dark mode

Calcite 5.2 deprecated the `calcite-mode-light` / `calcite-mode-dark` / `calcite-mode-auto` classes in favor of the CSS `color-scheme` property. `src/style.css` sets `color-scheme: light` on `:root`, and the theme action sets `document.documentElement.style.colorScheme` to `dark` or `light`. Calcite components and the map components follow it. The basemap is map content, not UI, so the sample also swaps `gray-vector` for `dark-gray-vector`. The choice is kept in `localStorage` (the preference only).

Build note: Calcite's colors use the CSS `light-dark()` function. `vite.config.js` sets `build.cssTarget` to browsers that support `light-dark()`; with Vite's default CSS target the production build rewrites `light-dark()` into a fallback that ignores `color-scheme` set from JavaScript, and the switch does nothing after `npm run build`.

## Responsive

Calcite's Shell does not hide panels on small screens by itself. Under 700 px wide the sample sets both shell panels to `displayMode = "overlay"` (they float over the map instead of pushing it aside), sets their `width` to `"l"` so the 300 px legend is not cut off, and collapses them until an action is clicked.

## Links

- Shell: https://developers.arcgis.com/calcite-design-system/components/shell/
- Shell Panel: https://developers.arcgis.com/calcite-design-system/components/shell-panel/
- Action Bar: https://developers.arcgis.com/calcite-design-system/components/action-bar/
- Panel: https://developers.arcgis.com/calcite-design-system/components/panel/
- Navigation: https://developers.arcgis.com/calcite-design-system/components/navigation/
- Calcite 5.2 release notes (mode classes deprecated): https://developers.arcgis.com/calcite-design-system/releases/v5-2/
- Modes (`color-scheme`): https://developers.arcgis.com/calcite-design-system/core-concepts/
- Building your UI (map components + Calcite): https://developers.arcgis.com/javascript/latest/building-your-ui/
- Layer List, Legend, Feature components: https://developers.arcgis.com/javascript/latest/references/map-components/

## License

MIT, see the repository LICENSE.
