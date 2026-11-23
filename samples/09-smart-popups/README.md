# 09 Smarter Popups with Arcade and Charts

A county map whose popup does real work: it computes values with Arcade ("46% of the homes here were built before 1970"), adds a whole table built by one Arcade expression, and shows a bar chart and a pie chart of homes by decade built. A "Panel mode" switch turns the popup off and lists every feature under a click in a side panel with `fetchPopupFeatures`. It goes with the ATS Build episode BLD-S02E05, "Smarter Popups with Arcade and Charts (ArcGIS JS 5.2)".

- Data: "ACS Housing Units by Year Built (Latest)" from Esri's Living Atlas (item `204f0ea4315640fca8c2e0fbefe11a96`), U.S. Census Bureau American Community Survey 5-year estimates, 2020-2024 release at the time of writing, tables B25034 (year structure built) and B25035 (median year built). County and state layers of https://P3ePLMYs2RVChkJx.svcs.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/ACS_Housing_Units_by_Year_Built_View_Boundaries/FeatureServer. Public, no sign-in. The "Latest" layer moves to each new ACS release, so numbers can change after the episode.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.2.7, `@esri/calcite-components` 5.2.1 (the version map-components 5.2.7 asks for). All pinned exactly. No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

## Arcade expressions as files (`src/arcade/`)

Each expression is its own `.arcade` file, imported as a string with Vite's `?raw` suffix (`import pre1970 from "./arcade/pre-1970.arcade?raw"`), so it can be read, diffed and tested on its own.

`src/popup-template.js` names three of them in `expressionInfos` and uses them in a text element as `{expression/pre-1970}`, `{expression/age-label}` and `{expression/built-since-2010}`:

| File | Returns | Shows |
|---|---|---|
| `pre-1970.arcade` | number | share of homes built before 1970, rounded |
| `built-since-2010.arcade` | string | homes built 2010 or later, with a thousands separator |
| `age-label.arcade` | string | a label from the median year built (`if` / `return`) |

A popup expression must return a string or a number; `returnType` says which.

## ExpressionContent: one expression, one whole element

`top-decades.arcade` is used as `{ type: "expression", expressionInfo: { expression } }`. Instead of a value it returns a dictionary that describes a complete popup element, here `type: "fields"` with its own `fieldInfos` and `attributes`: the three decades in which the most homes were built. Two Arcade details: build the attributes with `Dictionary()`, and give `Sort` a declared function (Arcade has no inline function expressions).

## Chart content

A `media` element holds a `bar-chart` and a `pie-chart`. `value.fields` lists the ten decade fields; on the bar chart `value.normalizeField` is the total-housing-units field, so each bar is a share of all homes. The chart labels come from the template's `fieldInfos`.

## The popup component (beta)

`<arcgis-popup>` sits in the map's `popup` slot. It is labelled beta in 5.2. The sample turns off the default actions (`include-default-actions-disabled`) and puts its own Calcite action in the `actions-end` slot (new in 5.2); clicking it zooms to `selectedFeature`. `dock-enabled` plus `dockOptions` (`position: "top-right"`, `breakpoint: false`, `buttonEnabled: false`) keep it docked at the top right, so the text, the table and the chart fit without scrolling. In 5.2.7 the `dock-enabled` attribute alone did not stay set once the map was ready, so `main.js` also sets `popupElement.dockEnabled = true` after `dockOptions`. In 5.2 the map's `popup` property is deprecated in favor of `popupElement` / `popup-component-enabled` (both beta) or a slotted `arcgis-popup`.

## fetchPopupFeatures in your own panel

With "Panel mode" on, `popupDisabled` stops the popup and a click calls `fetchPopupFeatures` on `<arcgis-map>` (since 5.1). On the component it returns a promise of an async generator:

```js
const generator = await mapElement.fetchPopupFeatures({ x, y }, { pointerType });
for await (const graphic of generator) { /* one feature at a time */ }
```

It returns features from every layer with a popup template and popups enabled, here the county and its state, in layer order. The sample lists them in a `calcite-list` and renders the selected one with `<arcgis-feature>`, which draws the same template (Arcade text, table, charts) outside the map. On a `MapView` the same method returns the generator directly (no `await`). There is no `fetchPopupFeatures` on a layer view.

## Web maps: keep the authored popup

This sample builds its template in code because its layers are added in code. When an app loads a web map, keep the popup that was authored in the map (Arcade, charts and formatting included) and render it with the popup or Feature component instead of rebuilding it.

## 6.0 note

The 5.2 release notes say 6.0 (planned for Q1 2027) removes many deprecated APIs, including widgets and the UI parts of `MapView` such as `view.popup`. The component path used here (`arcgis-popup`, `fetchPopupFeatures`, `arcgis-feature`) is the one that carries forward. In 5.2 `arcgis-feature` logs a deprecation warning for its internal view model; `arcgis-feature-next` (beta) is its preview successor and becomes `arcgis-feature` in 6.0.

## Smoke test

`smoke.checks.mjs` runs the in-page self-test (`window.__atsSample.selfTest()`): at least three `expressionInfos`, a media element and an expression element in the template, `fetchPopupFeatures` at the view center returns at least one feature, and panel mode toggles without a console error. It then opens the popup component on the same spot and checks it has a selected feature.

## Links

- PopupTemplate: https://developers.arcgis.com/javascript/latest/references/core/PopupTemplate/
- ExpressionInfo: https://developers.arcgis.com/javascript/latest/references/core/popup/ExpressionInfo/
- ExpressionContent: https://developers.arcgis.com/javascript/latest/references/core/popup/content/ExpressionContent/
- BarChartMediaInfo: https://developers.arcgis.com/javascript/latest/references/core/popup/content/BarChartMediaInfo/
- Arcade popup profile: https://developers.arcgis.com/arcade/profiles/popup/
- Map component (`fetchPopupFeatures`, `popupElement`): https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-map/
- Popup component: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-popup/
- Feature component: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-feature/
- 5.2 release notes: https://developers.arcgis.com/javascript/latest/release-notes/
- Living Atlas item: https://www.arcgis.com/home/item.html?id=204f0ea4315640fca8c2e0fbefe11a96

## License

MIT, see the repository LICENSE. The ACS data is from the U.S. Census Bureau; the Living Atlas layer is provided by Esri under its terms of use.
