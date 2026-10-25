/**
 * Thin, dependency-free wrapper around the Python core.
 *
 * The Node side owns no document logic: it shells out to `office_core.cli` and
 * parses one JSON object per call. Keeping it this thin is deliberate - the
 * DSH plugin API can change, the CLI contract cannot.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = resolve(HERE, '..', '..');

/** Exit codes mirrored from python/office_core/cli.py */
export const EXIT = {
  opsRejected: 2,
  verificationFailed: 3,
  templateMismatch: 4,
  targetNotFound: 5,
};

export class OfficeCliError extends Error {
  constructor(message, { exitCode = 1, payload = null, stderr = '' } = {}) {
    super(message);
    this.name = 'OfficeCliError';
    this.exitCode = exitCode;
    this.payload = payload;
    this.stderr = stderr;
  }
}

export function resolvePython(explicit) {
  if (explicit) return explicit;
  if (process.env.DSH_OFFICE_PYTHON) return process.env.DSH_OFFICE_PYTHON;
  const candidates = [
    join(REPO_ROOT, '.venv', 'bin', 'python'),
    join(REPO_ROOT, '.venv', 'Scripts', 'python.exe'),
  ];
  for (const candidate of candidates) if (existsSync(candidate)) return candidate;
  return 'python3';
}

export function runCli(args, { python, cwd = REPO_ROOT, timeoutMs = 180_000 } = {}) {
  const interpreter = resolvePython(python);
  const result = spawnSync(interpreter, ['-m', 'office_core.cli', ...args], {
    cwd,
    encoding: 'utf8',
    timeout: timeoutMs,
  });
  if (result.error) {
    throw new OfficeCliError(`failed to spawn ${interpreter}: ${result.error.message}`, { stderr: String(result.stderr ?? '') });
  }
  const stdout = (result.stdout ?? '').trim();
  const stderr = (result.stderr ?? '').trim();
  let payload = null;
  if (stdout) {
    try {
      payload = JSON.parse(stdout);
    } catch {
      throw new OfficeCliError(`non-JSON output from dsh-office: ${stdout.slice(0, 200)}`, {
        exitCode: result.status ?? 1, stderr,
      });
    }
  }
  if ((result.status ?? 1) !== 0) {
    let parsed = null;
    try {
      parsed = stderr ? JSON.parse(stderr) : null;
    } catch {
      /* stderr is not JSON (traceback); keep the text */
    }
    throw new OfficeCliError(parsed?.message ?? stderr.slice(0, 400) ?? `dsh-office exited ${result.status}`,
      { exitCode: result.status ?? 1, payload: parsed, stderr });
  }
  return payload;
}

/** Read a template into its fact table. */
export function extractFacts({ document, python, cwd } = {}) {
  if (!document) throw new TypeError('extractFacts requires { document }');
  return runCli(['extract', document], { python, cwd });
}

/** Replay an ops file onto a template. */
export function fillDocument({ template, ops, out, force = false, python, cwd } = {}) {
  for (const [key, value] of Object.entries({ template, ops, out })) {
    if (!value) throw new TypeError(`fillDocument requires { ${key} }`);
  }
  const args = ['fill', template, ops, '-o', out];
  if (force) args.push('--force');
  return runCli(args, { python, cwd });
}

/** Re-read a rendered document and report hard/soft findings. */
export function verifyDocument({ document, ops, allowFail = true, python, cwd } = {}) {
  for (const [key, value] of Object.entries({ document, ops })) {
    if (!value) throw new TypeError(`verifyDocument requires { ${key} }`);
  }
  const args = ['verify', document, ops];
  if (allowFail) args.push('--allow-fail');
  return runCli(args, { python, cwd });
}

/** Resolve an absolute path or one relative to the session working directory. */
export function absolutePath(path, cwd = process.cwd()) {
  return isAbsolute(path) ? path : resolve(cwd, path);
}
