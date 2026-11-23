// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
export default async function checks(page) {
  const problems = [];
  // In-page self-test: template shape, fetchPopupFeatures at the view center, panel mode on and off.
  const result = await page.evaluate(() => window.__atsSample.selfTest());
  problems.push(...result.problems);
  // The popup component opens on the same spot with the Arcade text and the chart.
  const popup = await page.evaluate(async () => {
    const map = document.querySelector("arcgis-map");
    const popupEl = document.querySelector("arcgis-popup");
    await map.openPopup({ location: map.view.center, fetchFeatures: true });
    for (let i = 0; i < 60 && !popupEl.selectedFeature; i++) await new Promise((r) => setTimeout(r, 250));
    await new Promise((r) => setTimeout(r, 1500));
    const title = popupEl.selectedFeature?.attributes?.NAME ?? null;
    const docked = popupEl.dockEnabled;
    await map.closePopup();
    while (map.view.updating) await new Promise((r) => setTimeout(r, 250));
    return { title, docked };
  });
  if (!popup.title) problems.push("popup component opened with no selected feature");
  if (!popup.docked) problems.push("popup component is not docked");
  return problems;
}
