import { useState, useEffect, useCallback, useRef } from 'react';
import { api, type StandardInfo, type SearchResult, type Stats } from './api';
import { InputSection } from './components/InputSection';
import { ComparisonTable } from './components/ComparisonTable';
import { ExportModal } from './components/ExportModal';
import { checkStandardsConcurrently } from './utils/checkStandards';
import './App.css';

function App() {
  const [standards, setStandards] = useState<StandardInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Results Map for comparison
  const [resultsMap, setResultsMap] = useState<Record<string, SearchResult | null | 'loading' | 'error' | 'not_found'>>({});
  const [stats, setStats] = useState<Stats>({ count: 0, last_updated: null, current: 0, upcoming: 0, abolished: 0, replaced: 0, partially_amended: 0, unknown: 0, conflict: 0 });
  const resultKeys = useRef(new WeakMap<StandardInfo, string>());
  const nextResultKey = useRef(0);
  // Each extract/check-all/clear starts a new run; older responses are aborted and ignored.
  const lookupRun = useRef({ id: 0, controller: new AbortController() });

  const startLookupRun = useCallback(() => {
    lookupRun.current.controller.abort();
    lookupRun.current = { id: lookupRun.current.id + 1, controller: new AbortController() };
    return lookupRun.current;
  }, []);

  const getResultKey = useCallback((standard: StandardInfo): string => {
    const existing = resultKeys.current.get(standard);
    if (existing) return existing;
    const key = `row-${nextResultKey.current++}`;
    resultKeys.current.set(standard, key);
    return key;
  }, []);

  const checkStandard = useCallback(async (code: string, name?: string, edition?: string | null, resultKey?: string) => {
    // Should check if either code OR name exists
    if (!code && !name) return;

    // Keep a row-specific key so duplicate codes and editions cannot overwrite each other.
    const key = resultKey || code || name || 'unknown';
    const run = lookupRun.current;
    const { signal } = run.controller;
    const updateResult = (value: SearchResult | 'loading' | 'error' | 'not_found') => {
      if (lookupRun.current !== run) return;
      setResultsMap(prev => ({
        ...prev,
        [key]: value,
      }));
    };

    updateResult('loading');
    try {
      // verify already falls back to a name lookup server-side and attaches a match
      // decision; a second client-side fuzzy search would show a result without one.
      const inputCode = edition ? `${code}（${edition}）` : code;
      const verified = await api.verifyStandard(inputCode, name, signal);
      updateResult(verified.result ?? 'not_found');
    } catch {
      updateResult('error');
    }
  }, []);

  const checkStandards = useCallback(async (items: StandardInfo[]) => {
    const run = lookupRun.current;
    await checkStandardsConcurrently(
      items,
      std => checkStandard(std.code, std.name || undefined, std.edition || std.revision_year, getResultKey(std)),
      () => lookupRun.current === run,
    );
  }, [checkStandard, getResultKey]);

  useEffect(() => {
    api.getDatabaseStats().then(data => setStats(data)).catch(console.error);
  }, []);

  const handleExtract = async (text: string) => {
    const run = startLookupRun();
    setIsLoading(true);
    try {
      const extracted = await api.extractStandards(text);
      if (lookupRun.current !== run) return;
      const nonEmptyStandards = extracted.filter((standard) => (
        Boolean(standard.code?.trim()) || Boolean(standard.name?.trim())
      ));
      setResultsMap({}); // Clear previous results to avoid flickering or stale data
      setStandards(nonEmptyStandards);
      if (nonEmptyStandards.length === 0) {
        alert('未提取到规范信息，请检查输入格式');
        return;
      }
      await checkStandards(nonEmptyStandards);
    } catch (error: unknown) {
      console.error('Error extracting standards:', error);
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      alert(`提取失败: ${errorMsg}\n\n请检查网络连接后重试；如持续失败，可能是查新服务暂时不可用。`);
    } finally {
      if (lookupRun.current === run) setIsLoading(false);
    }
  };

  const handleClear = () => {
    startLookupRun();
    setIsLoading(false);
    setStandards([]);
    setResultsMap({});
  };

  const handleAddStandard = () => {
    setStandards((previous) => [...previous, { code: '', name: '', year: '' }]);
  };

  const handleRemoveStandard = (index: number) => {
    const newStandards = [...standards];
    newStandards.splice(index, 1);
    setStandards(newStandards);
  };

  const handleUpdateStandard = (index: number, field: keyof StandardInfo, value: string) => {
    setStandards((previous) => {
      const newStandards = [...previous];
      while (newStandards.length <= index) {
        newStandards.push({ code: '', name: '', year: '' });
      }
      newStandards[index] = { ...newStandards[index], [field]: value };
      return newStandards;
    });
  };

  const handleCheckAll = async () => {
    if (standards.length === 0) return;
    const run = startLookupRun();
    setIsLoading(true);
    setResultsMap({});
    try {
      await checkStandards(standards);
    } finally {
      if (lookupRun.current === run) setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <span className="app-mark" aria-hidden="true">规</span>
        <h1>规范名称校验工具</h1>
      </header>

      <main className="app-content">
        <InputSection
          onExtract={handleExtract}
          onCheckAll={handleCheckAll}
          isLoading={isLoading}
          hasStandards={standards.length > 0}
        />
        <ComparisonTable
          standards={standards}
          resultsMap={resultsMap}
          onCheckSingle={checkStandard}
          getResultKey={getResultKey}
          onClear={handleClear}
          onAdd={handleAddStandard}
          onRemove={handleRemoveStandard}
          onUpdate={handleUpdateStandard}
          stats={stats}
        />

        {/* Footer & Export Row */}
        {standards.length > 0 && (
          <div className="export-actions-bar">
              <button
                className="btn-primary export-open-button"
                onClick={() => setIsExportOpen(true)}
              >
                导出规范引用
              </button>
          </div>
        )}
      </main>

      {/* Replaced footer with inline one above */}
      {/* <footer className="app-footer">
        <p>说明：1. 匹配状态：现行（绿色）、废止（红色）。 2. 输入结果与最新规范不一致时标记黄色背景。</p>
        <p style={{ textAlign: 'center', color: '#888', fontSize: '12px', padding: '0', margin: '5px 0 0 0' }}>
          3. 结果仅供参考，必要时请以官方发布为准。
        </p>
      </footer> */}

      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        standards={standards}
        resultsMap={resultsMap}
        getResultKey={getResultKey}
      />
    </div>
  );
}

export default App;
