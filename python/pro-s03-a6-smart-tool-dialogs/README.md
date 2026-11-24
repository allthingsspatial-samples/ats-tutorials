# How to Make Smart Tool Dialogs in ArcGIS Pro (PRO-S03 A6)

The finished `SymbolTools.pyt` from the **Automate GIS** episode A6. It has one tool, **Export Pro Symbols to SVG/PNG**, and its dialog is the lesson:

- the Categories and Symbols value lists are filled from the chosen style in `updateParameters`;
- the Symbols list follows the categories you pick;
- parameters switch on and off with the Export choice;
- an optional parameter becomes required for one choice, with `setIDMessage("ERROR", 735)` in `updateMessages`;
- a File filter (`stylx`) on the style and a Range filter on the PNG size;
- a warning when the output folder is not empty.

- Video: TBD (not uploaded yet; goes live 2026-11-30)
- Watch page and the other ArcGIS Pro episodes: https://www.allthingsspatial.io/learn/

## Files

- [`SymbolTools.pyt`](SymbolTools.pyt): the toolbox as it stands at the end of the episode

ArcGIS Pro writes the help files (`SymbolTools.pyt.xml` and the tool's `.pyt.xml`) itself, so they are not included.

## Versions

ArcGIS Pro 3.8 or later (recorded on 3.8.1), Basic license, no extension.

## Run it

1. In the Catalog pane, right-click Toolboxes > Add Toolbox and browse to `SymbolTools.pyt`. Trust the code when ArcGIS Pro asks.
2. Open **Symbol Tools > Export Pro Symbols to SVG/PNG**.
3. Pick an Input Style (`.stylx`), then Export: all point symbols, selected categories or selected symbols.
4. Pick an Output Folder, an Output Format (SVG, PNG, or SVG and PNG) and, for PNG, a size in pixels.

The tool writes one file per point symbol, in one subfolder per category. It draws vector markers (rings, paths, Bezier curves, arcs, solid fill and stroke) and embedded picture markers; font-glyph markers and effects are skipped with a warning. The core logic is in `export_style_symbols()`.

The same tool is also in the [ATS Starter Toolbox](../ats-starter-toolbox/).

## Data

Data pack: downloads.allthingsspatial.io pack for A6 is coming soon. Any point-symbol style you made yourself (`.stylx`) works with the tool. Check the terms before you share symbols copied from the ArcGIS Pro system styles.

License: MIT, see [LICENSE](../../LICENSE) at the repo root.
