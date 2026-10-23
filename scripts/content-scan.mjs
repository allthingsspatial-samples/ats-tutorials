#!/usr/bin/env node
// Forbidden-content scan for this public repo. CI runs it on every push and pull request, and the
// maintainer's pre-push hook runs it before anything leaves the machine. It fails on:
//   - local file system paths (Windows drive paths, user profile folders)
//   - terms on a private denylist, stored only as salted SHA-256 hashes in content-scan.denylist.json
//     so this public repo never contains the words it guards against. "names" match identifiers
//     joined by - _ . (my-name, my_name); "words" match plain words and phrases in any text.
//   - credentials: API keys, access tokens, private keys, and committed .env / key files
// It checks every tracked file AND the commit metadata (messages, author and committer).
// Findings print the location and category only, never the matched text, so CI logs leak nothing.
//
// Usage:
//   node scripts/content-scan.mjs                        tracked files in the working tree + all commits on HEAD
//   node scripts/content-scan.mjs --ref <sha> --range <a..b>   tree at <sha> + commits in <a..b> (pre-push)
//   node scripts/content-scan.mjs --extra-names <file>   also deny the plain-text names in <file> (local only)
//   node scripts/content-scan.mjs --hash < terms.txt     print the denylist hash of each term on stdin

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const SALT = "ats-content-scan-v1:";
const hash = (s) => createHash("sha256").update(SALT + s).digest("hex");

const args = process.argv.slice(2);
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};

if (args.includes("--hash")) {
  // One term per line. A leading "cs:" makes the match case-sensitive; otherwise case is ignored.
  // Terms made of several words (or joined by - _ .) match those words in sequence.
  const terms = readFileSync(0, "utf8").split(/\r?\n/).map((t) => t.trim()).filter(Boolean);
  for (const t of terms) {
    const cs = t.startsWith("cs:");
    const body = cs ? t.slice(3) : t.toLowerCase();
    console.log(hash((cs ? "cs:" : "") + words(body).join(" ")));
  }
  process.exit(0);
}

const denylist = JSON.parse(readFileSync(join(here, "content-scan.denylist.json"), "utf8"));
const deniedNames = new Set(denylist.names);
const deniedWords = new Set(denylist.words);
const maxWords = denylist.maxWords;

const extra = opt("--extra-names");
if (extra) {
  for (const t of readFileSync(extra, "utf8").split(/\r?\n/).map((s) => s.trim()).filter(Boolean)) {
    deniedNames.add(hash(words(t.toLowerCase()).join(" ")));
  }
}

function words(s) {
  return s.split(/[^A-Za-z0-9]+/).filter(Boolean);
}

// Patterns are assembled from parts so this file does not match itself.
const BS = String.fromCharCode(92);
const PATTERNS = [
  ["local-path", new RegExp("\\b[A-Za-z]:" + BS + BS + "(?:[A-Za-z0-9_.$ -]|" + BS + BS + "|$)", "g")],
  ["local-path", new RegExp("[" + BS + BS + "/]" + "Users" + "[" + BS + BS + "/]" + "[A-Za-z]", "g")],
  ["local-path", new RegExp("/" + "home/[a-z][a-z0-9_-]*/", "g")],
  ["secret", new RegExp("AKIA" + "[0-9A-Z]{16}", "g")],
  ["secret", new RegExp("\\bgh[pousr]" + "_[A-Za-z0-9]{30,}", "g")],
  ["secret", new RegExp("github" + "_pat_[A-Za-z0-9_]{30,}", "g")],
  ["secret", new RegExp("\\bAAP[KT]" + "[A-Za-z0-9_-]{20,}", "g")],
  ["secret", new RegExp("AIza" + "[0-9A-Za-z_-]{30,}", "g")],
  ["secret", new RegExp("\\bxox[abposr]" + "-[A-Za-z0-9-]{10,}", "g")],
  ["secret", new RegExp("\\bsk" + "[-_](?:live|test|proj|ant)[-_][A-Za-z0-9_-]{16,}", "g")],
  ["secret", new RegExp("-----BEGIN [A-Z ]*" + "PRIVATE KEY-----", "g")],
  ["secret", new RegExp("[?&](?:token|access_token|api_key|apikey|key)=" + "[A-Za-z0-9._-]{20,}", "gi")],
  ["secret", new RegExp("\\b(?:api[_-]?key|secret|password|passwd|token)\\s*[:=]\\s*[\"'][^\"'\\s]{12,}[\"']", "gi")],
];

const SECRET_FILES = /(^|\/)(\.env(\.(?!example$)[^/]+)?|[^/]+\.(pem|key|p12|pfx)|id_(rsa|dsa|ecdsa|ed25519))$/;

const git = (...a) => execFileSync("git", a, { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 });
const gitBuf = (...a) => execFileSync("git", a, { maxBuffer: 256 * 1024 * 1024 });

const findings = [];
const report = (where, line, category) => findings.push(`${where}:${line}: ${category}`);

function scanText(where, text) {
  const lines = text.split(/\r?\n/);
  lines.forEach((line, i) => {
    for (const [category, re] of PATTERNS) {
      re.lastIndex = 0;
      if (re.test(line)) report(where, i + 1, category);
    }
    // Denylist: every run of 1..maxWords consecutive parts, case-insensitive and case-sensitive.
    // Names are tested inside each identifier (split on - _ .); words across the whole line.
    const ids = line.split(/[^A-Za-z0-9._-]+/).map((t) => words(t));
    if (ids.some((parts) => hit(parts, deniedNames))) report(where, i + 1, "denylisted-name");
    else if (hit(words(line), deniedWords)) report(where, i + 1, "denylisted-word");
  });
}

function hit(w, set) {
  for (let a = 0; a < w.length; a++) {
    for (let n = 1; n <= maxWords && a + n <= w.length; n++) {
      const seq = w.slice(a, a + n).join(" ");
      if (set.has(hash(seq.toLowerCase())) || set.has(hash("cs:" + seq))) return true;
    }
  }
  return false;
}

const ref = opt("--ref");
const range = opt("--range");

const files = ref
  ? git("ls-tree", "-r", "--name-only", "-z", ref).split("\0").filter(Boolean)
  : git("ls-files", "-z").split("\0").filter(Boolean);

for (const f of files) {
  if (SECRET_FILES.test(f)) report(f, 0, "secret-file");
  scanText(f + " (path)", f);
  const buf = ref ? gitBuf("show", `${ref}:${f}`) : readFileSync(f);
  if (buf.includes(0)) continue; // binary
  scanText(f, buf.toString("utf8"));
}

const logRange = range || "HEAD";
const log = git("log", "--format=%H%x00%an <%ae>%n%cn <%ce>%n%B%x00", logRange);
for (const entry of log.split("\0\n").filter((e) => e.trim())) {
  const [sha, body = ""] = entry.split("\0");
  scanText(`commit ${sha.trim().slice(0, 12)}`, body);
}

const commits = log.split("\0\n").filter((e) => e.trim()).length;
if (findings.length) {
  console.error(`content-scan: FAIL - ${findings.length} finding(s) in ${files.length} files and ${commits} commits`);
  for (const f of findings) console.error("  " + f);
  console.error("Remove the flagged content (and rewrite the flagged commit messages) before pushing.");
  process.exit(1);
}
console.log(`content-scan: PASS - ${files.length} files and ${commits} commits clean`);
