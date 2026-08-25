import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const inputSection = await readFile(new URL('../src/components/InputSection.tsx', import.meta.url), 'utf8');
const comparisonTable = await readFile(new URL('../src/components/ComparisonTable.tsx', import.meta.url), 'utf8');
const exportModal = await readFile(new URL('../src/components/ExportModal.tsx', import.meta.url), 'utf8');
const modalCss = await readFile(new URL('../src/components/StandardDetailModal.css', import.meta.url), 'utf8');
const app = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
const appCss = await readFile(new URL('../src/App.css', import.meta.url), 'utf8');

test('primary flow is named as one-click extraction and verification', () => {
  assert.match(inputSection, /提取并查新/);
  assert.match(inputSection, /重新查新/);
});

test('results expose the dataset update time and responsive table affordances', () => {
  assert.match(comparisonTable, /数据更新时间/);
  assert.match(comparisonTable, /Asia\/Shanghai/);
  assert.match(comparisonTable, /className="results-toolbar"/);
  assert.match(comparisonTable, /className="table-scroll"/);
});

test('primary interface does not use emoji as controls or section icons', () => {
  for (const source of [app, inputSection]) {
    assert.doesNotMatch(source, /[📄📝⚡🔍📑]/u);
  }
});

test('interactive controls keep a 44px minimum touch target', () => {
  assert.doesNotMatch(appCss, /min-height:\s*(?:[0-3]?\d|4[0-3])px/);
});

test('results use a stable row identity instead of code-only keys', () => {
  assert.match(app, /WeakMap/);
  assert.match(app, /getResultKey\(std\)/);
  assert.match(comparisonTable, /getResultKey\(standard\)/);
  assert.match(comparisonTable, /getResultKey\(std\)/);
});

test('export preview uses the same stable row identity as the results table', () => {
  assert.match(exportModal, /getResultKey\(std\)/);
  assert.doesNotMatch(app, /legacyKey/);
});

test('source search links remain available when the local lookup is missing', () => {
  assert.match(comparisonTable, /result\?\.soujianzhu_url\s*\|\|/);
  assert.match(comparisonTable, /standard\.name\s*\|\|\s*standard\.code/);
  assert.match(comparisonTable, /搜建筑搜索/);
  assert.match(comparisonTable, /工标网搜索/);
});

test('soujianzhu and csres actions share one fixed button size', () => {
  assert.match(comparisonTable, /const sourceActionStyle/);
  assert.match(comparisonTable, /width:\s*'96px'/);
  assert.match(comparisonTable, /minHeight:\s*'44px'/);
  assert.equal((comparisonTable.match(/\.\.\.sourceActionStyle/g) || []).length, 3);
});

test('revision-missing results explicitly drive the code highlight', () => {
  assert.match(comparisonTable, /matchType\s*===\s*['"]revision_missing['"]/);
  assert.match(comparisonTable, /revisionMismatch/);
});

test('empty results keep an actionable row and do not auto-check', () => {
  assert.doesNotMatch(comparisonTable, /if\s*\(standards\.length\s*===\s*0\)\s*return\s+null/);
  assert.match(comparisonTable, /className="empty-state-row"/);
  assert.match(comparisonTable, /aria-label="新增规范名称"/);
  assert.match(comparisonTable, /aria-label="新增规范编号"/);
  assert.match(comparisonTable, /暂无待查规范/);
  assert.match(comparisonTable, /加入查新列表/);
  assert.match(comparisonTable, /event\.key === 'Enter'/);
  assert.doesNotMatch(comparisonTable, /onChange=\{\(event\)[\s\S]{0,220}onUpdate\?\.\(0/);
});

test('table and export modal keep overflow inside their own containers', () => {
  assert.match(appCss, /\.table-scroll\s*\{[\s\S]*?overflow-x:\s*auto/);
  assert.match(appCss, /\.table-scroll\s*\{[\s\S]*?max-width:\s*100%/);
  assert.match(exportModal, /className="modal-overlay export-modal-overlay"/);
  assert.match(exportModal, /className="modal-content export-modal-content"/);
  assert.match(exportModal, /className="modal-body export-modal-body"/);
  assert.match(exportModal, /className="standard-list export-standard-list"/);
  assert.match(exportModal, /className="export-preview-text"/);
  assert.match(modalCss, /\.export-modal-content\s*\{/);
  assert.match(modalCss, /\.export-standard-list\s*\{[\s\S]*?overflow:\s*auto/);
  assert.match(modalCss, /@media\s*\(max-width:\s*720px\)/);
  assert.match(modalCss, /\.export-modal-body\s*\{[\s\S]*?flex-direction:\s*column/);
});
