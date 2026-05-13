#!/usr/bin/env node
/**
 * Bootstrap pre-commit framework + install git hooks.
 *
 * Invoked automatically by `npm install` via the "prepare" script.
 * Idempotent — re-running is safe.
 *
 * Skipped in:
 *   - CI (CI=true) — CI runs `pre-commit run --all-files` directly
 *   - Production installs (NODE_ENV=production)
 *   - Non-git checkouts (no .git directory)
 */
import { execSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const REPO_ROOT = resolve(process.cwd());
const GIT_DIR = resolve(REPO_ROOT, ".git");

function log(msg) {
  process.stdout.write(`[setup-hooks] ${msg}\n`);
}

function warn(msg) {
  process.stderr.write(`[setup-hooks] ⚠️  ${msg}\n`);
}

function fail(msg) {
  process.stderr.write(`[setup-hooks] ❌ ${msg}\n`);
  process.exit(1);
}

if (process.env.CI === "true") {
  log("CI environment detected — skipping hook install.");
  process.exit(0);
}

if (process.env.NODE_ENV === "production") {
  log("NODE_ENV=production — skipping hook install.");
  process.exit(0);
}

if (!existsSync(GIT_DIR)) {
  log("Not a git checkout — skipping hook install.");
  process.exit(0);
}

// Align local git config with .gitattributes (eol=lf). On Windows the default
// core.autocrlf=true would convert LF→CRLF on checkout, fighting the LF-only
// repo and triggering `mixed-line-ending` on every commit. `input` keeps the
// working tree as-is but normalizes line endings to LF on commit.
{
  const current = spawnSync("git", ["config", "--local", "core.autocrlf"], {
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  const value = (current.stdout || "").trim();
  if (value !== "input" && value !== "false") {
    log("Setting core.autocrlf=input (matches .gitattributes eol=lf)…");
    spawnSync("git", ["config", "--local", "core.autocrlf", "input"], {
      stdio: "inherit",
      shell: process.platform === "win32",
    });
  }
}

function commandAvailable(cmd, args = ["--version"]) {
  const result = spawnSync(cmd, args, { stdio: "ignore", shell: process.platform === "win32" });
  return result.status === 0;
}

function tryInstallPreCommit() {
  // Order matters: pipx (isolated, premium) > python -m pip (Windows-friendly) > pip standalone.
  // On Windows `pip` is rarely in PATH but `python -m pip` always works if Python is installed.
  const candidates = [
    { cmd: "pipx", args: ["install", "pre-commit"], probe: ["--version"], label: "pipx" },
    { cmd: "python", args: ["-m", "pip", "install", "--user", "pre-commit"], probe: ["-m", "pip", "--version"], label: "python -m pip --user" },
    { cmd: "python3", args: ["-m", "pip", "install", "--user", "pre-commit"], probe: ["-m", "pip", "--version"], label: "python3 -m pip --user" },
    { cmd: "py", args: ["-m", "pip", "install", "--user", "pre-commit"], probe: ["-m", "pip", "--version"], label: "py -m pip --user" },
    { cmd: "pip", args: ["install", "--user", "pre-commit"], probe: ["--version"], label: "pip --user" },
    { cmd: "pip3", args: ["install", "--user", "pre-commit"], probe: ["--version"], label: "pip3 --user" },
  ];
  for (const { cmd, args, probe, label } of candidates) {
    if (!commandAvailable(cmd, probe)) continue;
    log(`Installing pre-commit via ${label}…`);
    const result = spawnSync(cmd, args, { stdio: "inherit", shell: process.platform === "win32" });
    if (result.status === 0) return true;
    warn(`${label} failed (exit ${result.status}) — trying next option.`);
  }
  return false;
}

function preCommitInstalled() {
  return commandAvailable("pre-commit");
}

let _cachedInvocation;

// Returns { cmd, prefix } for invoking pre-commit, or null. Memoized.
// Falls back to `python -m pre_commit` when the standalone binary isn't on PATH —
// common on Windows after `pip install --user`.
function resolvePreCommitInvocation() {
  if (_cachedInvocation !== undefined) return _cachedInvocation;
  if (commandAvailable("pre-commit")) {
    _cachedInvocation = { cmd: "pre-commit", prefix: [] };
    return _cachedInvocation;
  }
  for (const py of ["python", "python3", "py"]) {
    if (commandAvailable(py, ["-m", "pre_commit", "--version"])) {
      log(`Using '${py} -m pre_commit' (standalone binary not in PATH).`);
      _cachedInvocation = { cmd: py, prefix: ["-m", "pre_commit"] };
      return _cachedInvocation;
    }
  }
  _cachedInvocation = null;
  return _cachedInvocation;
}

function installHooks() {
  const invocation = resolvePreCommitInvocation();
  if (!invocation) {
    fail("pre-commit installed but not callable. Check Python user Scripts directory in PATH.");
  }
  log("Installing git hooks (pre-commit + commit-msg)…");
  const result = spawnSync(
    invocation.cmd,
    [...invocation.prefix, "install", "--hook-type", "pre-commit", "--hook-type", "commit-msg"],
    { stdio: "inherit", shell: process.platform === "win32" },
  );
  if (result.status !== 0) {
    fail(`pre-commit install failed (exit ${result.status}).`);
  }
}

if (!resolvePreCommitInvocation()) {
  warn("pre-commit not found in PATH. Attempting auto-install…");
  const installed = tryInstallPreCommit();
  if (!installed || !resolvePreCommitInvocation()) {
    warn("Could not auto-install pre-commit.");
    warn("Install manually (see docs/SETUP.md step 12):");
    warn("    python -m pip install --user pre-commit");
    warn("    python -m pre_commit install --hook-type pre-commit --hook-type commit-msg");
    warn("Skipping hook install — commits will not be guarded locally.");
    warn("CI will still enforce all guards server-side.");
    process.exit(0);
  }
}

installHooks();
log("✅ Git hooks installed. Local commits are now guarded.");
log("   Run `npm run doctor` for a full health check.");
