// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
const headerBackground = (page) =>
  page.evaluate(() => {
    const inner = document.querySelector("calcite-navigation")?.shadowRoot?.querySelector("div,nav,header");
    return inner ? getComputedStyle(inner).backgroundColor : "missing";
  });

export default async function checks(page) {
  const problems = [];
  await page.waitForFunction(() => window.__atsSample?.chartsReady === true, { timeout: 90_000 }).catch(() => problems.push("charts did not finish drawing"));
  const n = await page.evaluate(() => document.querySelectorAll("arcgis-chart").length);
  if (n !== 2) problems.push(`expected 2 charts, found ${n}`);
  // Dark mode on and off: one class on the html element must change the header background, and back.
  const light = await headerBackground(page);
  await page.evaluate(() => window.__atsSample.setDark(true));
  await new Promise((r) => setTimeout(r, 1500));
  const dark = await headerBackground(page);
  await page.evaluate(() => window.__atsSample.setDark(false));
  await new Promise((r) => setTimeout(r, 500));
  const back = await headerBackground(page);
  if (light === "missing" || dark === light) problems.push(`dark mode did not change the header (${light} -> ${dark})`);
  if (back !== light) problems.push(`light mode did not come back (${back})`);
  console.log(`map-charts: ${n} charts drawn, header ${light} -> dark ${dark} -> ${back}`);
  await page.waitForFunction(() => window.view?.updating === false, { timeout: 60_000 });
  return problems;
}
