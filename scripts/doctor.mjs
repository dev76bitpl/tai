#!/usr/bin/env node
/**
 * Cross-platform launcher for `scripts/doctor.py`.
 *
 * Why not `python3 scripts/doctor.py || py scripts/doctor.py` in package.json: doctor exits 1
 * on purpose when a required check fails, and `||` cannot tell "python3 is missing" from
 * "doctor found a problem". Every red report was followed by a second attempt through the
 * Windows launcher `py` — on Linux that ends with a misleading `py: not found`, on Windows
 * with the whole report printed twice.
 *
 * This script picks the first interpreter that answers `--version`, runs doctor exactly once
 * and forwards its exit code untouched.
 */
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const DOCTOR_PY = resolve(dirname(fileURLToPath(import.meta.url)), "doctor.py");

// Windows: the `py` launcher is the one thing guaranteed by the official installer, while
// `python3` may be the Microsoft Store stub that opens a browser instead of running code.
// Elsewhere `python3` is canonical and `python` covers distros/venvs that alias it.
export const CANDIDATES = process.platform === "win32" ? ["py", "python", "python3"] : ["python3", "python"];

export function probeInterpreter(cmd) {
  const result = spawnSync(cmd, ["--version"], { stdio: "ignore", shell: process.platform === "win32" });
  return !result.error && result.status === 0;
}

/** First candidate whose probe succeeds, or null when no Python is reachable. */
export function pickInterpreter(candidates = CANDIDATES, probe = probeInterpreter) {
  for (const cmd of candidates) {
    if (probe(cmd)) return cmd;
  }
  return null;
}

export function main(argv = process.argv.slice(2)) {
  const python = pickInterpreter();
  if (!python) {
    process.stderr.write(
      `[doctor] No Python interpreter found (tried: ${CANDIDATES.join(", ")}). ` +
        "Install Python 3.9+ and make sure it is on PATH.\n",
    );
    return 1;
  }
  const result = spawnSync(python, [DOCTOR_PY, ...argv], { stdio: "inherit", shell: process.platform === "win32" });
  if (result.error) {
    process.stderr.write(`[doctor] Failed to run ${python}: ${result.error.message}\n`);
    return 1;
  }
  return result.status ?? 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  process.exit(main());
}
