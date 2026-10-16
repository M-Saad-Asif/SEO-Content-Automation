// Reads a site's rate modules (TypeScript or JavaScript, e.g. Calcsite's src/data/rates) and prints their exported
// data as JSON: {"uk/income-tax.ts": {"incomeTax": {...}, "incomeTaxSource": {...}}, ...}. Node 22.6+ loads .ts
// files by stripping their types. Functions are skipped; Infinity becomes "Infinity". Read-only.
import { readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { pathToFileURL } from "node:url";

const root = process.argv[2];
const files = [];
const walk = (d) => {
  for (const f of readdirSync(d)) {
    const p = join(d, f);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(ts|mts|js|mjs)$/.test(f) && !/\.(test|spec|d)\.[mc]?[tj]s$/.test(f)) files.push(p);
  }
};
walk(root);
const out = {};
for (const f of files) {
  const key = relative(root, f).split("\\").join("/");
  try {
    const m = await import(pathToFileURL(f).href);
    out[key] = Object.fromEntries(Object.entries(m).filter(([, v]) => typeof v !== "function"));
  } catch (e) {
    out[key] = { __error: String((e && e.message) || e).slice(0, 300) };
  }
}
process.stdout.write(JSON.stringify(out, (k, v) => (v === Infinity ? "Infinity" : v)));
