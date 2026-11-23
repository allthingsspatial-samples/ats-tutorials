import "@esri/calcite-components/components/calcite-shell";
import "@esri/calcite-components/components/calcite-shell-panel";
import "@esri/calcite-components/components/calcite-navigation";
import "@esri/calcite-components/components/calcite-navigation-logo";
import "@esri/calcite-components/components/calcite-panel";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-zoom";
import "@arcgis/map-components/components/arcgis-editor";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import { createFormTemplate } from "./form-template.js";

// Esri's public sample service "DamageAssessment" (ArcGIS Server, no sign-in). Layer 0 allows
// anonymous create, update and delete, with attachments. Anyone can edit it, and its contents can change at any time,
// so treat what you see there as test data, and delete what you add.
const DAMAGE_URL = "https://sampleserver6.arcgisonline.com/arcgis/rest/services/DamageAssessment/FeatureServer/0";

const mapElement = document.querySelector("arcgis-map");
const editor = document.querySelector("arcgis-editor");

await mapElement.viewOnReady();

const damage = new FeatureLayer({
  url: DAMAGE_URL,
  title: "Damage reports",
  // The service names features by a contact field (first name). Name them by the extent of damage
  // instead, so lists in the Editor never show someone's name.
  displayField: "typdamage",
  outFields: ["*"],
  // The Editor reads the form from the layer.
  formTemplate: createFormTemplate(),
});
mapElement.map.add(damage);

// ---- In-page self-test, used by the smoke run. Reads the form only: it never writes to the service. ----
async function selfTest() {
  const problems = [];
  await mapElement.whenLayerView(damage);
  const form = damage.formTemplate;
  const flat = form.elements.flatMap((e) => (e.type === "group" ? [...e.elements] : [e]));
  const dynamic = flat.find((e) => e.type === "field" && e.input?.type === "dynamic-choice");
  const attachment = flat.find((e) => e.type === "attachment");
  if (!dynamic) problems.push("no field element with a dynamic-choice input");
  else if (!form.expressionInfos.some((x) => x.name === dynamic.input.choiceExpression))
    problems.push(`choiceExpression "${dynamic.input.choiceExpression}" is not in expressionInfos`);
  if (!attachment) problems.push("no attachment element");
  if (form.supportsAttachmentElements !== true) problems.push("supportsAttachmentElements is not true");
  if (!damage.capabilities?.operations?.supportsAdd) problems.push("layer does not report supportsAdd");
  if (!damage.capabilities?.data?.supportsAttachment) problems.push("layer does not report attachments");
  for (const p of problems) console.error(`self-test: ${p}`);
  return { problems, elements: flat.map((e) => e.fieldName ?? e.type) };
}

// For the smoke test and the tutorial's capture rig.
window.view = mapElement.view;
window.__atsSample = { damage, editor, selfTest };
