import PopupTemplate from "@arcgis/core/PopupTemplate.js";
// Each Arcade expression lives in its own file; Vite's ?raw suffix imports it as a string.
import pre1970 from "./arcade/pre-1970.arcade?raw";
import builtSince2010 from "./arcade/built-since-2010.arcade?raw";
import ageLabel from "./arcade/age-label.arcade?raw";
import topDecades from "./arcade/top-decades.arcade?raw";

// ACS table B25034 "Year structure built": one field per decade, plus the total.
const DECADES = [
  ["B25034_011E", "1939 or earlier"],
  ["B25034_010E", "1940s"],
  ["B25034_009E", "1950s"],
  ["B25034_008E", "1960s"],
  ["B25034_007E", "1970s"],
  ["B25034_006E", "1980s"],
  ["B25034_005E", "1990s"],
  ["B25034_004E", "2000s"],
  ["B25034_003E", "2010s"],
  ["B25034_002E", "2020 or later"],
];
const TOTAL = "B25034_001E";
const MEDIAN = "B25035_001E";

// The county and state layers share the same ACS fields, so they share this template;
// only the title differs.
export function createPopupTemplate(title, titleFields) {
  return new PopupTemplate({
    title,
    // The Arcade in top-decades.arcade reads the decade fields too: request them all.
    outFields: [...titleFields, TOTAL, MEDIAN, ...DECADES.map(([field]) => field)],

    // 1. expressionInfos: named Arcade expressions, used as {expression/<name>}.
    expressionInfos: [
      { name: "pre-1970", title: "Share built before 1970 (%)", expression: pre1970, returnType: "number" },
      { name: "built-since-2010", title: "Homes built since 2010", expression: builtSince2010, returnType: "string" },
      { name: "age-label", title: "Housing stock", expression: ageLabel, returnType: "string" },
    ],

    // Field labels (the chart uses them for its bars) and number formats.
    fieldInfos: [
      { fieldName: TOTAL, label: "Housing units", format: { digitSeparator: true, places: 0 } },
      { fieldName: MEDIAN, label: "Median year built", format: { digitSeparator: false, places: 0 } },
      ...DECADES.map(([fieldName, label]) => ({ fieldName, label, format: { digitSeparator: true, places: 0 } })),
      { fieldName: "expression/pre-1970", format: { places: 0 } },
    ],

    content: [
      // Text content that mixes fields and expressions.
      {
        type: "text",
        text:
          "<b>{expression/pre-1970}%</b> of the {" + TOTAL + "} homes here were built before 1970. " +
          "The median home was built in {" + MEDIAN + "}: {expression/age-label}. " +
          "{expression/built-since-2010} homes are from 2010 or later.",
      },
      // 2. ExpressionContent: one Arcade expression returns a whole content element.
      {
        type: "expression",
        expressionInfo: { title: "Busiest building decades", expression: topDecades },
      },
      // 3. MediaContent: a bar chart of the decade fields, each divided by the total.
      {
        type: "media",
        mediaInfos: [
          {
            type: "bar-chart",
            title: "Homes by decade built (share of all homes)",
            value: { fields: DECADES.map(([field]) => field), normalizeField: TOTAL },
          },
          {
            type: "pie-chart",
            title: "Homes by decade built (count)",
            value: { fields: DECADES.map(([field]) => field) },
          },
        ],
      },
    ],
  });
}
