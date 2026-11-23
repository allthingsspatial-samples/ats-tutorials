import FormTemplate from "@arcgis/core/form/FormTemplate.js";
import choicesExpression from "./arcade/choices.arcade?raw";

// The form the Editor shows for the damage layer. Only the fields listed here appear,
// so the layer's contact fields (names, phones, e-mail) never show in this app.
export function createFormTemplate() {
  return new FormTemplate({
    title: "Damage report",
    description: "Esri public sample service: shared and reset from time to time.",
    // 5.1: attachments become part of the form. With this on, attachments that no
    // attachment element matches are not shown at all.
    supportsAttachmentElements: true,
    expressionInfos: [
      // 5.2: a dictionary expression that returns { choices: [{ name, code }] }.
      { name: "damage-choices", title: "Damage choices", expression: choicesExpression, returnType: "dictionary" },
      // Rules: Arcade expressions that return true or false.
      { name: "cause-is-other", title: "Cause is Other", expression: '$feature.primcause == "Other"', returnType: "boolean" },
      { name: "major-or-worse", title: "Major or destroyed", expression: 'Includes(["Major", "Destroyed"], $feature.typdamage)', returnType: "boolean" },
      { name: "is-habitable", title: "Habitable", expression: '$feature.habitable == "Yes"', returnType: "boolean" },
    ],
    elements: [
      {
        type: "group",
        label: "Damage",
        elements: [
          { type: "field", fieldName: "typdamage", label: "Extent of damage" },
          { type: "field", fieldName: "primcause", label: "Primary cause" },
          {
            type: "field",
            fieldName: "descdamage",
            label: "Description of damage",
            hint: "Choices depend on the primary cause",
            // 5.2: DynamicChoiceInput. choiceExpression names an entry in expressionInfos.
            input: { type: "dynamic-choice", choiceExpression: "damage-choices" },
          },
          {
            type: "field",
            fieldName: "comments",
            label: "Comments",
            // Shown only when the cause is "Other", and then it must be filled in.
            visibilityExpression: "cause-is-other",
            requiredExpression: "cause-is-other",
            input: { type: "text-area" },
          },
        ],
      },
      {
        type: "group",
        label: "Occupancy",
        elements: [
          // Required once the damage is Major or Destroyed.
          { type: "field", fieldName: "habitable", label: "Habitable", requiredExpression: "major-or-worse" },
          { type: "field", fieldName: "numoccup", label: "Number of occupants", visibilityExpression: "is-habitable" },
        ],
      },
      {
        // 5.1: AttachmentElement. "any" = this element shows every attachment of the feature.
        type: "attachment",
        label: "Photos",
        attachmentKeyword: "photo",
        displayFilename: true,
        maxAttachmentCount: 3,
        input: {
          type: "attachment",
          attachmentAssociationType: "any",
          inputTypes: [{ type: "image" }],
        },
      },
    ],
  });
}
