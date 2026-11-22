// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
export default async function checks(page) {
  const problems = [];
  const state = () =>
    page.evaluate(() => ({
      shell: !!customElements.get("calcite-shell") && !!document.querySelector("calcite-shell"),
      actions: document.querySelectorAll("calcite-action-bar calcite-action").length,
      open: [...document.querySelectorAll("calcite-panel[data-panel]")].filter((p) => !p.hidden && !p.closed).map((p) => p.dataset.panel),
      scheme: getComputedStyle(document.documentElement).colorScheme,
    }));
  let s = await state();
  if (!s.shell) problems.push("calcite-shell is not defined");
  if (s.actions !== 3) problems.push(`expected 3 actions, found ${s.actions}`);
  for (const name of ["layers", "legend", "about"]) {
    await page.evaluate((n) => window.__atsSample.open(n), name);
    s = await state();
    if (s.open.length !== 1 || s.open[0] !== name) problems.push(`open("${name}") showed [${s.open}]`);
  }
  await page.evaluate(() => window.__atsSample.setTheme("light"));
  const before = (await state()).scheme;
  await page.click("#theme");
  await new Promise((r) => setTimeout(r, 500));
  const after = (await state()).scheme;
  if (before !== "light" || after !== "dark") problems.push(`theme switch: color-scheme ${before} -> ${after}`);
  return problems;
}
