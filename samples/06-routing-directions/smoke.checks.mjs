// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
// CI never has a key, so the sample must run in "no-key" mode: notice shown, no Directions component.
export default async function checks(page) {
  const problems = [];
  const s = await page.evaluate(() => ({
    mode: window.__atsSample?.mode,
    directions: document.querySelector("arcgis-directions") !== null,
    // open, and actually drawn (a notice that is not open has no height)
    notice: document.querySelector("#no-key")?.open === true && document.querySelector("#no-key").getBoundingClientRect().height > 40,
  }));
  if (s.mode !== "no-key") problems.push(`expected mode "no-key", got "${s.mode}"`);
  if (s.directions) problems.push("arcgis-directions is in the page without a key");
  if (!s.notice) problems.push("the Add your key notice is not shown");
  return problems;
}
