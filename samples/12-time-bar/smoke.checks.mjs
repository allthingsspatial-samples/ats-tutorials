// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
export default async function checks(page) {
  const problems = [];
  const result = await page.evaluate(() => window.__atsSample.selfTest());
  problems.push(...result.problems);
  console.log(`time-bar self-test: ${JSON.stringify({ ...result, problems: undefined })}`);
  await page.waitForFunction(() => window.view?.updating === false, { timeout: 60_000 });
  return problems;
}
