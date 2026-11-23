# 12 The Time Bar: Animate a Map Through Time

A map of a month of earthquakes that you play like a video. The new Time Bar component (5.2) steps the map one day at a time, a Time Bar Slider shows where you are, a switch changes the time mode, and a Feature Table below the map lists only the earthquakes in the current time. It goes with the ATS Build episode BLD-S02E08, "The New Time Bar for Time-Aware Maps (ArcGIS JS 5.2)".

- Data: Esri's public sample item "USGS earthquakes 2019 June 18th" (item 0433d83530334b46b87c940dfc810589, GeoJSON, owner jsapi_team, the data Esri's Time Bar API reference uses). It holds 10,875 USGS earthquakes from 20 May to 19 June 2019. It is a fixed file, so you see the same earthquakes the episode shows. Public, no sign-in.
- SDK: `@arcgis/core` and `@arcgis/map-components` 5.2.7, `@esri/calcite-components` 5.2.1 (the version map-components 5.2.7 asks for). All pinned exactly. No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

## The Time Slider is deprecated in 5.2

The 5.2 release notes: "The new Time Bar component replaces the TimeSlider widget and component". The `arcgis-time-slider` reference page: "Deprecated since 5.2. Use the Time Bar component instead." This sample uses no Time Slider.

## Time Slider to Time Bar

The Time Bar keeps the time properties of the Time Slider and moves the look into `show-*` flags and a separate slider. This table is our reading of the two 5.2 API references (they do not publish a mapping):

| `arcgis-time-slider` (deprecated) | `arcgis-time-bar` (5.2) |
|---|---|
| `fullTimeExtent`, `timeExtent`, `mode`, `stops`, `playRate`, `loop`, `timeZone` | same names |
| `play()`, `stop()`, `next()`, `previous()`, `effectiveStops`, `state` | same names |
| `applyTimeSliderSettings()` | `applyTimeSettings()` |
| `layout` ("auto", "compact", "wide": the orientation of the parts) | no `layout` property: the look comes from the parts you show (`show-play`, `show-previous`, `show-next`, `show-settings`, `show-time-extent`) and an optional Time Bar Slider |
| the slider track (always there) | optional: an `arcgis-time-bar-slider` in the `time-extent` slot (shown with `show-time-extent`) |
| `timeVisible`, `labelFormatFunction` | `format` ("date" or "date-time"), or your own content in the slider's `min`, `max` and `popover` slots |
| `tickConfigs` | `show-ticks` on the Time Bar Slider, or an `arcgis-ticks` in its `content-end` slot |
| `actions` | the `actions-end` slot (`calcite-action` elements) |

## How it works

1. **A time-aware layer.** The layer's `timeInfo` names the date field (`startField: "time"`). The map's time filters only time-aware layers.
2. **The Time Bar.** It sits in the map's `bottom-left` slot, so it drives the map's `timeExtent` by itself, with no filter code. `main.js` sets `fullTimeExtent` from the layer (`layer.timeInfo.fullTimeExtent.expandTo("days", "Etc/UTC")`), one stop per day (`stops = { interval: 1 day }`, 32 stops), and a one-day window to start. `loop` restarts playback at the end; `play-rate="1000"` asks for one step a second (the docs note playback waits for the view to finish updating, so it can be slower).
3. **Time zone.** The map has `time-zone="Etc/UTC"`. The Time Bar and the table take the map's time zone, so every date reads the same on any computer. `expandTo` is given the same zone; without it, it rounds to days in the computer's time zone.

## Modes

The switch at the top sets the Time Bar's `mode`. Each mode expects its own time extent shape, so `setMode()` in `main.js` sets the mode and the extent together:

| Mode | Time extent | Checked in this sample (UTC) |
|---|---|---|
| `time-window` (default) | start and end | 20 May 00:00 to 21 May 00:00: 91 earthquakes |
| `instant` | start equals end | one earthquake per stop (see below) |
| `cumulative-from-start` | start `null`, end | everything before the end: 91 up to 21 May 00:00, growing as you step forward |

An instant matches only features at that exact moment. With the daily stops (midnight) no earthquake in this file matches, so instant mode would show an empty map. The Time Bar's stops can also be a list of dates, so in instant mode the sample sets the stops to the times of the 12 earthquakes of magnitude 6 or more (`stops = { dates }`): each instant shows that one earthquake, and Next steps to the next one. The other modes switch back to the daily stops.

The Time Bar also has `cumulative-from-end` (end `null`).

## The table follows the map's time

`<arcgis-feature-table view-time-enabled>`: `viewTimeEnabled` (new in 5.2) makes the table use the intersection of the view's and the layer's time extent. The table is bound to the layer with `mapLayerId`. On the first day the table header reads "Total: 91", the same count as the map.

## Smoke test

`smoke.checks.mjs` runs the in-page self-test (`window.__atsSample.selfTest()`): `arcgis-time-bar`, `arcgis-time-bar-slider` and `arcgis-feature-table` are defined, the layer has `timeInfo`, the view's `timeExtent` is set once the Time Bar is ready, one `next()` changes `view.timeExtent.start` (the run logs the counts, 91 then 312 earthquakes), the table has `viewTimeEnabled`, there are 32 daily stops and 12 strong-earthquake stops. The self-test logs `console.error` only on failure, so the standard smoke run fails with it.

## Data note

The data is a fixed sample file, so nothing here refreshes. For a live feed, swap in any time-enabled layer, for example Esri Living Atlas "Recent Earthquakes" (`USGS_Seismic_Data_v1`, field `eventTime`); its counts change through the day.

## Links

- Time Bar: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-time-bar/
- Time Bar Slider: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-time-bar-slider/
- Time Slider (deprecated): https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-time-slider/
- Feature Table (`viewTimeEnabled`): https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-feature-table/
- TimeInfo: https://developers.arcgis.com/javascript/latest/references/core/layers/support/TimeInfo/
- Esri sample "Time Bar component": https://developers.arcgis.com/javascript/latest/sample-code/time-bar/
- 5.2 release notes: https://developers.arcgis.com/javascript/latest/release-notes/
- Data item: https://www.arcgis.com/home/item.html?id=0433d83530334b46b87c940dfc810589

## License

MIT, see the repository LICENSE. Earthquake data from the U.S. Geological Survey (public domain), in a sample file published by Esri.
