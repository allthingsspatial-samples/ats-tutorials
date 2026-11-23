// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
export default async function checks(page) {
  const problems = [];
  await page.waitForFunction(() => window.__atsSample?.chartsReady === true, { timeout: 90_000 }).catch(() => problems.push("charts did not finish drawing"));
  const n = await page.evaluate(() => document.querySelectorAll("arcgis-chart").length);
  if (n !== 2) problems.push(`expected 2 charts, found ${n}`);
  // Dark mode on and off: one class on the body.
  await page.evaluate(() => window.__atsSample.setDark(true));
  await new Promise((r) => setTimeout(r, 1500));
  const dark = await page.evaluate(() => getComputedStyle(document.querySelector("calcite-panel")).backgroundColor);
  if (dark === "rgb(255, 255, 255)") problems.push(`dark mode: panel still white`);
  await page.evaluate(() => window.__atsSample.setDark(false));
  console.log(`map-charts: ${n} charts drawn, dark mode ${dark}`);
  await page.waitForFunction(() => window.view?.updating === false, { timeout: 60_000 });
  return problems;
}
