# 11 Smart Editing Forms: Dynamic Choices and Photo Attachments

An editing app where the form reacts to what you enter. A dropdown's choices depend on the field before it (an Arcade expression, new in 5.2), one field appears and becomes required only for some answers, another becomes required once the damage is serious, and photos are attached inside the form itself (5.1). All of it is a `FormTemplate` on the layer. The `arcgis-editor` component builds the form from that template, so we write no input controls ourselves. It goes with the ATS Build episode BLD-S02E07, "Smart Editing Forms with Arcade (ArcGIS JS 5.2)".

- SDK: `@arcgis/core` and `@arcgis/map-components` 5.2.7, `@esri/calcite-components` 5.2.1 (the version map-components 5.2.7 asks for). All pinned exactly. No API key.
- Build tool: Vite

```bash
npm ci
npm run dev
```

## Shared sample service: read this first

The data is Esri's public sample service "DamageAssessment", layer 0 (https://sampleserver6.arcgisonline.com/arcgis/rest/services/DamageAssessment/FeatureServer/0). It allows anonymous create, update and delete, with attachments, and needs no sign-in. That also means:

- anyone can add, change or delete features there, so the map will not match the episode;
- what other people typed is not yours to show: frame your own feature;
- delete what you add (select it, then Delete in the Editor) when you are done;
- the layer has contact fields (names, phones, e-mail). The form in this sample lists only damage and occupancy fields, so those never appear in it. The service names features by first name, so `main.js` sets the layer's `displayField` to the extent of damage: lists in the Editor show "Minor", "Major" and so on, not a name. Do not type real personal details into a public service.

To keep your own data, point the sample at your own editable layer (see the end).

## What the form does

`src/form-template.js` builds the form. Three groups of elements:

| Element | Field | Behavior |
|---|---|---|
| Damage group | `typdamage` (Extent of damage) | dropdown from the layer's coded-value domain |
| | `primcause` (Primary cause) | dropdown from the layer's coded-value domain |
| | `descdamage` (Description of damage) | **dynamic choices** from `src/arcade/choices.arcade`, based on the primary cause |
| | `comments` | shown, and required, only for a cause with no preset descriptions (Landslide, Rain, Snow, Other) |
| Occupancy group | `habitable` | required when the extent is Major or Destroyed |
| | `numoccup` | shown only when Habitable is "Yes" |
| Photos | (attachments) | an attachment element: up to 3 images, inside the form |

Rules are Arcade expressions in the template's `expressionInfos`; elements refer to them by name (`visibilityExpression`, `requiredExpression`). They cannot be written inline in the element.

## Dynamic choices (5.2)

A field element whose `input` is a `DynamicChoiceInput` (`type: "dynamic-choice"`). Its `choiceExpression` is the **name** of an entry in `expressionInfos`, and that expression returns a dictionary with a `choices` array of `{ name, code }`: `name` is the text in the list, `code` is the value saved in the field.

```js
expressionInfos: [
  { name: "damage-choices", expression: choicesExpression, returnType: "dictionary" },
],
// ...
{ type: "field", fieldName: "descdamage", input: { type: "dynamic-choice", choiceExpression: "damage-choices" } }
```

`src/arcade/choices.arcade` reads `$feature.primcause` (the value in the form, before it is saved) and returns three descriptions each for Flood, Fire, Wind and Earthquake, and "Describe in comments" for any other cause (Landslide, Rain, Snow, Other) or none. Vite imports the file as text (`?raw`). Esri's own sample builds its list with a query against another table (`FeatureSetById` + `Filter`), which works the same way.

Checked with 5.2.7: pick Flood and the list is "Water above floor level", "Water in basement only", "Foundation scoured"; change to Wind and it becomes "Shingles or siding lost", "Roof lifted", "Tree on structure". A value picked before the change stays in the field until you pick a new one, so re-check it after changing the cause.

## Photo attachments in the form (5.1)

```js
supportsAttachmentElements: true,
elements: [
  // ...
  {
    type: "attachment",
    label: "Photos",
    attachmentKeyword: "photo",
    maxAttachmentCount: 3,
    input: { type: "attachment", attachmentAssociationType: "any", inputTypes: [{ type: "image" }] },
  },
],
```

- `supportsAttachmentElements` is `false` by default. Once it is `true`, attachments show only through attachment elements: with no attachment element, a feature's existing attachments are not shown at all.
- An image, audio, video or document input shows only existing attachments whose keyword matches the element's `attachmentKeyword`. This service does not keep attachment keywords, so the sample uses the general attachment input with `attachmentAssociationType: "any"`, which shows every attachment of the feature.
- Attachment elements work for one feature at a time, not batch edits.

Checked with 5.2.7 on this service: a feature created in the Editor with one photo was saved with its attachment (`applyEdits`, then `addAttachment`), queried back, and deleted.

## Smoke test

`smoke.checks.mjs` checks that `arcgis-editor` is defined and runs the in-page self-test (`window.__atsSample.selfTest()`): the form has a field element with a `dynamic-choice` input whose `choiceExpression` is in `expressionInfos`, an attachment element, `supportsAttachmentElements === true`, and the layer reports add and attachment support. It only reads: CI never writes to the shared service. The add, attach and delete round trip was checked locally, in a scripted browser run with real clicks on the Editor (Create, then Delete and confirm).

## Use your own layer

Change `DAMAGE_URL` in `src/main.js` to your editable feature layer (attachments enabled for the Photos element), then change the field names in `src/form-template.js` and `src/arcade/choices.arcade` to yours.
## Links

- DynamicChoiceInput (5.2): https://developers.arcgis.com/javascript/latest/references/core/form/elements/inputs/DynamicChoiceInput/
- Sample, Edit features with dynamic choices: https://developers.arcgis.com/javascript/latest/sample-code/editor-dynamic-choices/
- AttachmentElement (5.1): https://developers.arcgis.com/javascript/latest/references/core/form/elements/AttachmentElement/
- AttachmentInput (`attachmentAssociationType`): https://developers.arcgis.com/javascript/latest/references/core/form/elements/inputs/attachments/AttachmentInput/
- FormTemplate (`supportsAttachmentElements`, `expressionInfos`): https://developers.arcgis.com/javascript/latest/references/core/form/FormTemplate/
- FieldElement (`requiredExpression`, `visibilityExpression`): https://developers.arcgis.com/javascript/latest/references/core/form/elements/FieldElement/
- Editor component: https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-editor/
- 5.2 release notes: https://developers.arcgis.com/javascript/latest/release-notes/
- 5.1 release notes: https://archive.developers.arcgis.com/javascript/v5-1/release-notes/

## License

MIT, see the repository LICENSE. Sample data: Esri's public sample service, for demonstration only.
