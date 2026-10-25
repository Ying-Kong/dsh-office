/**
 * Plugin-level contract: the three tools exist, advertise parameters, and are
 * thin. `defineTool` is faked so the suite runs without a DSH profile.
 */
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';

import { REPO_ROOT, resolvePython } from '../src/core.mjs';
import { buildToolDefs, inject, name } from '../src/plugin.mjs';

const FIXTURES = join(REPO_ROOT, 'fixtures');
const TEMPLATE = join(FIXTURES, 'templates', 'report.docx');
const OPS = join(FIXTURES, 'reporter', 'ops.json');

const fakeDefineTool = (definition) => ({ definition });

function defs() {
  return buildToolDefs({ defineTool: fakeDefineTool, options: { python: resolvePython() } });
}

test('plugin metadata matches the DSH loader contract', () => {
  assert.equal(name, 'dsh-office');
  assert.deepEqual(inject, ['tools']);
});

test('registers exactly the three document tools', () => {
  const names = defs().map((tool) => tool.definition.name);
  assert.deepEqual(names, ['office_extract', 'office_fill', 'office_verify']);
});

test('every tool declares a canonical output with a renderer', () => {
  // Regression: the real defineTool reads options.output.render and throws
  // without it. A fake defineTool cannot catch that, so assert the shape here.
  for (const { definition } of defs()) {
    assert.ok(definition.output, `${definition.name} needs output`);
    assert.ok(definition.output.schema, `${definition.name} needs output.schema`);
    assert.equal(typeof definition.output.render, 'function');
    const blocks = definition.output.render({}, { ok: true });
    assert.equal(blocks[0].type, 'text');
  }
});

test('definitions are accepted by the real defineTool when it is installed', async (t) => {
  let defineTool;
  try {
    ({ defineTool } = await import('@deepseek-ai/dsh-tools'));
  } catch {
    t.skip('@deepseek-ai/dsh-tools not installed in this environment');
    return;
  }
  const real = buildToolDefs({ defineTool });
  assert.equal(real.length, 3);
  for (const tool of real) assert.equal(typeof tool.execute, 'function');
});

test('every tool declares parameters and a description', () => {
  for (const { definition } of defs()) {
    assert.ok(definition.description.length > 40, `${definition.name} needs a real description`);
    assert.ok(Object.keys(definition.parameters).length > 0);
    assert.equal(typeof definition.execute, 'function');
  }
});

test('office_extract reports slots for the reference template', async () => {
  const tool = defs().find((entry) => entry.definition.name === 'office_extract').definition;
  const summary = await tool.execute({ document: TEMPLATE });
  assert.equal(summary.schema, 'dsh-office/facts@1');
  assert.ok(summary.slots >= 3);
  assert.ok(summary.slot_labels.includes('指导老师'));
});

test('office_fill and office_verify work end to end', async () => {
  const { definition: fill } = defs().find((entry) => entry.definition.name === 'office_fill');
  const { definition: verify } = defs().find((entry) => entry.definition.name === 'office_verify');
  const work = mkdtempSync(join(REPO_ROOT, '.node-work-'));
  try {
    const out = join(work, 'rendered.docx');
    const filled = await fill.execute({ template: TEMPLATE, ops: OPS, output: out });
    assert.equal(filled.ok, true);

    const report = await verify.execute({ document: out, ops: OPS });
    assert.equal(report.ok, true);
    assert.deepEqual(report.captions, [1, 2]);
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
});
