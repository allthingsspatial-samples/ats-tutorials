// Extra smoke checks for this sample (run by scripts/smoke.mjs after the view is ready).
// CI never has a key, so the sample must run in "no-key" mode: notice shown, no search box,
// no geocoding requests, and the address list still loads from public/data/capitols.csv.
export default async function checks(page) {
  const problems = [];
  const s = await page.evaluate(() => ({
    mode: window.__atsSample?.mode,
    rows: window.__atsSample?.rows,
    search: document.querySelector("arcgis-search") !== null,
    batchDisabled: document.querySelector("#run-batch")?.disabled === true,
    tableRows: document.querySelectorAll("#results calcite-table-row:not([slot])").length,
    // open, and actually drawn (a notice that is not open has no height)
    notice: document.querySelector("#no-key")?.open === true && document.querySelector("#no-key").getBoundingClientRect().height > 40,
  }));
  if (s.mode !== "no-key") problems.push(`expected mode "no-key", got "${s.mode}"`);
  if (s.rows !== 10) problems.push(`expected 10 rows from capitols.csv, got ${s.rows}`);
  if (s.tableRows !== 10) problems.push(`expected 10 table rows, got ${s.tableRows}`);
  if (s.search) problems.push("arcgis-search is in the page without a key");
  if (!s.batchDisabled) problems.push("the list button is enabled without a key");
  if (!s.notice) problems.push("the Add your key notice is not shown");
  return problems;
}
