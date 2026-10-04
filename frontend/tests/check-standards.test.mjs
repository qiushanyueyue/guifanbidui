import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/utils/checkStandards.ts', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { checkStandardsConcurrently } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
const flush = () => new Promise(resolve => setImmediate(resolve));
const standards = Array.from({ length: 9 }, (_, index) => ({ code: `GB ${index}`, name: null }));

test('starts four requests, lets fast rows pass a slow row, and waits for all results', async () => {
  const started = [];
  const completed = [];
  const release = new Map();
  let active = 0;
  let peak = 0;
  let finished = false;
  const batch = checkStandardsConcurrently(standards, async standard => {
    started.push(standard.code);
    peak = Math.max(peak, ++active);
    await new Promise(resolve => release.set(standard.code, resolve));
    completed.push(standard.code);
    active--;
  }).then(() => { finished = true; });
  assert.deepEqual(started, ['GB 0', 'GB 1', 'GB 2', 'GB 3']);
  for (const code of ['GB 1', 'GB 2', 'GB 3', 'GB 4', 'GB 5', 'GB 6', 'GB 7', 'GB 8']) {
    release.get(code)();
    await flush();
  }
  assert.equal(finished, false);
  assert.equal(completed.length, 8);
  assert.equal(completed.includes('GB 0'), false);
  release.get('GB 0')();
  await batch;
  assert.equal(peak, 4);
  assert.equal(new Set(started).size, 9);
  assert.equal(completed.length, 9);
});

test('keeps duplicate codes, names, and editions in distinct rows and skips blank rows', async () => {
  const rows = [
    { code: 'GB 50016-2014', name: '防火规范', edition: '2018年版' },
    { code: 'GB 50016-2014', name: '防火规范', edition: '2014年版' },
    { code: '', name: '仅名称规范' },
    { code: '', name: null },
  ];
  const seen = [];
  await checkStandardsConcurrently(rows, async row => { seen.push(row); });
  assert.deepEqual(seen, rows.slice(0, 3));
  await checkStandardsConcurrently([], async () => assert.fail('empty batch must not send requests'));
});

test('a handled row error does not prevent the remaining requests from running', async () => {
  const results = new Map();
  await checkStandardsConcurrently(standards, async row => {
    try {
      if (row.code === 'GB 0') throw new Error('network unavailable');
      await flush();
      results.set(row, 'ok');
    } catch {
      results.set(row, 'error');
    }
  });
  assert.equal(results.size, 9);
  assert.equal(results.get(standards[0]), 'error');
  assert.equal([...results.values()].filter(value => value === 'ok').length, 8);
});
