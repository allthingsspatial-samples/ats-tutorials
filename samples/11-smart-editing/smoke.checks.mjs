// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
// No edits: CI must never write to the shared sample service.
export default async function checks(page) {
  const problems = [];
  const missing = await page.evaluate(() => ["arcgis-map", "arcgis-editor"].filter((t) => !customElements.get(t)));
  for (const tag of missing) problems.push(`${tag} is not defined`);
  const result = await page.evaluate(() => window.__atsSample.selfTest());
  problems.push(...result.problems);
  await page.waitForFunction(() => window.view?.updating === false, { timeout: 60_000 });
  return problems;
}
