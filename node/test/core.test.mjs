/**
 * The Node layer must stay a pass-through: if these break, the adapter is
 * doing document work it should not own.
 */
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';

import {
  REPO_ROOT, OfficeCliError, EXIT, absolutePath, extractFacts, fillDocument, resolvePython, verifyDocument,
} from '../src/core.mjs';

const FIXTURES = join(REPO_ROOT, 'fixtures');
const TEMPLATE = join(FIXTURES, 'templates', 'report.docx');
const OPS = join(FIXTURES, 'reporter', 'ops.json');

function interpreterAvailable() {
  try {
    extractFacts({ document: TEMPLATE, python: resolvePython() });
    return true;
  } catch {
    return false;
  }
}

const available = interpreterAvailable();

test('resolvePython prefers the repository virtualenv', () => {
  const python = resolvePython();
  assert.ok(python.includes('.venv') || python === 'python3', `unexpected interpreter: ${python}`);
});

test('absolutePath resolves relative to the given cwd', () => {
  assert.equal(absolutePath('a.docx', '/tmp'), '/tmp/a.docx');
  assert.equal(absolutePath('/abs/a.docx', '/tmp'), '/abs/a.docx');
});

test('extractFacts returns the fact table', { skip: !available && 'python core not installed' }, () => {
  const facts = extractFacts({ document: TEMPLATE });
  assert.equal(facts.schema, 'dsh-office/facts@1');
  assert.ok(facts.slots.length >= 3);
  assert.ok(facts.slots.some((slot) => slot.label === '指导老师'));
  assert.equal(facts.template.page.width_twip, 11906);
});

test('fill then verify roundtrip', { skip: !available && 'python core not installed' }, () => {
  const work = mkdtempSync(join(REPO_ROOT, '.node-work-'));
  try {
    const out = join(work, 'filled.docx');
    const filled = fillDocument({ template: TEMPLATE, ops: OPS, out });
    assert.equal(filled.ok, true);

    const report = verifyDocument({ document: out, ops: OPS });
    assert.equal(report.ok, true, JSON.stringify(report.hard, null, 2));
    assert.deepEqual(report.captions, [1, 2]);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});

test('hard failures surface as a distinct exit code', { skip: !available && 'python core not installed' }, () => {
  const work = mkdtempSync(join(REPO_ROOT, '.node-work-'));
  try {
    const out = join(work, 'x.docx');
    // verifying the *template* against ops meant for a filled document must fail
    assert.throws(
      () => verifyDocument({ document: TEMPLATE, ops: OPS, allowFail: false }),
      (error) => error instanceof OfficeCliError && error.exitCode === EXIT.verificationFailed,
    );
    assert.ok(out);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
