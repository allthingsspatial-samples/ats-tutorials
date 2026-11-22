// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
export default async function checks(page) {
  const problems = [];
  const defined = await page.evaluate(() =>
    ["arcgis-selection-toolbar", "arcgis-selection-list", "arcgis-feature-table"].filter((t) => !customElements.get(t)),
  );
  for (const tag of defined) problems.push(`${tag} is not defined`);
  // In-page self-test: select 3 known ids in code -> table highlights 3 rows -> clear.
  const result = await page.evaluate(() => window.__atsSample.selfTest());
  problems.push(...result.problems);
  await page.waitForFunction(() => window.view?.updating === false, { timeout: 60_000 });
  return problems;
}
