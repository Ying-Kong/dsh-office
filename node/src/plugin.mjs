/**
 * DSH adapter: three model-facing tools over the Python core.
 *
 * Everything document-related lives in the Python package; this file only
 * describes the tools to the model and forwards calls. That keeps the plugin
 * portable across DSH versions (the CLI contract is stable).
 *
 * @module dsh-office
 */
import { absolutePath, extractFacts, fillDocument, verifyDocument } from './core.mjs';

/** Plugin name registered with the DSH loader. */
export const name = 'dsh-office';

/** Host service this plugin consumes. */
export const inject = ['tools'];

const EXTRACT_DESCRIPTION = [
  'Read a .docx template and return its fact table: paragraphs with resolved',
  'font size / fonts, tables with cell ids, and auto-detected fillable slots',
  '(empty cells next to labels, date lines). Use this before writing ops so',
  'every target id is real.',
].join(' ');

const FILL_DESCRIPTION = [
  'Replay a declarative ops file (set_text / replace_in_paragraph / append_content',
  '/ set_format) onto a template and write a new .docx. The ops file is data,',
  'not code: no scripting runs. Refuses to run when the template fingerprint',
  'does not match unless force is true.',
].join(' ');

const VERIFY_DESCRIPTION = [
  'Re-read a rendered .docx and prove the ops landed: slot values, appended text,',
  'figure count and caption numbering, font whitelist, leftover placeholders.',
  'Returns { ok, hard[], soft[] }; hard findings must be fixed before delivery.',
].join(' ');

/**
 * Build the tool definitions. `defineTool` is injected so tests can run without
 * the DSH runtime installed.
 */
export function buildToolDefs({ defineTool, options = {} } = {}) {
  if (typeof defineTool !== 'function') throw new TypeError('buildToolDefs requires { defineTool }');
  const defaults = { python: options.pythonPath, cwd: options.cwd };

  return [
    defineTool({
      name: 'office_extract',
      description: EXTRACT_DESCRIPTION,
      parameters: {
        document: { type: 'string', required: true, description: 'Path to the .docx template.' },
        output: { type: 'string', description: 'Optional path to write the facts JSON.' },
      },
      execute: async ({ document, output }) => {
        const args = { document: absolutePath(document, defaults.cwd), python: defaults.python, cwd: defaults.cwd };
        const facts = extractFacts(args);
        if (output) {
          const { writeFileSync, mkdirSync } = await import('node:fs');
          const { dirname } = await import('node:path');
          const target = absolutePath(output, defaults.cwd);
          mkdirSync(dirname(target), { recursive: true });
          writeFileSync(target, JSON.stringify(facts, null, 2), 'utf8');
        }
        return {
          schema: facts.schema,
          slots: facts.slots.length,
          slot_labels: facts.slots.slice(0, 20).map((slot) => slot.label),
          paragraphs: facts.stats.paragraphs,
          tables: facts.tables.length,
          content_sha256: facts.template.content_sha256,
        };
      },
    }),
    defineTool({
      name: 'office_fill',
      description: FILL_DESCRIPTION,
      parameters: {
        template: { type: 'string', required: true, description: 'Path to the .docx template.' },
        ops: { type: 'string', required: true, description: 'Path to the ops JSON file.' },
        output: { type: 'string', required: true, description: 'Path of the .docx to write.' },
        force: { type: 'boolean', description: 'Ignore the template fingerprint guard.' },
      },
      execute: async ({ template, ops, output, force }) => fillDocument({
        template: absolutePath(template, defaults.cwd),
        ops: absolutePath(ops, defaults.cwd),
        out: absolutePath(output, defaults.cwd),
        force: Boolean(force),
        python: defaults.python,
        cwd: defaults.cwd,
      }),
    }),
    defineTool({
      name: 'office_verify',
      description: VERIFY_DESCRIPTION,
      parameters: {
        document: { type: 'string', required: true, description: 'Rendered .docx to inspect.' },
        ops: { type: 'string', required: true, description: 'The ops file used to render it.' },
        failOnHard: {
          type: 'boolean',
          description: 'When true, a hard finding rejects the tool call instead of returning a report.',
        },
      },
      execute: async ({ document, ops, failOnHard }) => {
        const report = verifyDocument({
          document: absolutePath(document, defaults.cwd),
          ops: absolutePath(ops, defaults.cwd),
          allowFail: !failOnHard,
          python: defaults.python,
          cwd: defaults.cwd,
        });
        return report;
      },
    }),
  ];
}

/**
 * Cordis entry point. Mounting registers the tools in the current scope.
 */
export async function apply(ctx, config = {}) {
  let defineTool;
  try {
    ({ defineTool } = await import('@deepseek-ai/dsh-tools'));
  } catch (error) {
    throw new Error(
      'dsh-office needs @deepseek-ai/dsh-tools in the profile that loads it '
      + `(peer dependency): ${error.message}`,
    );
  }
  for (const def of buildToolDefs({ defineTool, options: config })) ctx.tools.register(def);
}
