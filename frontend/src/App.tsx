import { useState, useEffect, useCallback } from 'react';
import { api, type StandardInfo, type SearchResult, type Stats } from './api';
import { InputSection } from './components/InputSection';
import { ComparisonTable } from './components/ComparisonTable';
import { ExportModal } from './components/ExportModal';
import './App.css';

function App() {
  const [standards, setStandards] = useState<StandardInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // Results Map for comparison
  const [resultsMap, setResultsMap] = useState<Record<string, SearchResult | null | 'loading' | 'error' | 'not_found'>>({});
  const [stats, setStats] = useState<Stats>({ count: 0, last_updated: null, current: 0, upcoming: 0, abolished: 0, replaced: 0, partially_amended: 0, unknown: 0, conflict: 0 });

  // Trigger for checking all standards
  const [checkTrigger, setCheckTrigger] = useState(0);

  const checkStandard = useCallback(async (code: string, name?: string, edition?: string | null) => {
    // Should check if either code OR name exists
    if (!code && !name) return;

    // Use code as key if available, otherwise use name
    const key = code || name || 'unknown';

    setResultsMap(prev => ({ ...prev, [key]: 'loading' }));
    try {
      let results: SearchResult[] = [];

      // Priority 1: Search by Code (if exists)
      if (code) {
        const lookupCode = edition ? `${code}（${edition}）` : code;
        results = await api.searchStandard(lookupCode);
      }

      // Priority 2: If Code search fails (or no code), try Name
      if ((!results || results.length === 0) && name) {
        // console.log(`Code search failed/skipped for ${code}, trying name: ${name}`);
        results = await api.searchStandard(name);
      }

      if (results && results.length > 0) {
        setResultsMap(prev => ({ ...prev, [key]: results[0] }));
      } else {
        setResultsMap(prev => ({ ...prev, [key]: 'not_found' }));
      }
    } catch {
      setResultsMap(prev => ({ ...prev, [key]: 'error' }));
    }
  }, []);

  // Listen for global check trigger
  useEffect(() => {
    const runCheckAll = async () => {
      for (const std of standards) {
        // Always run check to update status in-place (no flicker)
        if (std.code || std.name) {
          await checkStandard(std.code, std.name || undefined, std.edition || std.revision_year);
        }
      }
      setIsLoading(false);
    };
    runCheckAll();
  }, [checkTrigger, standards, checkStandard]);

  useEffect(() => {
    api.getDatabaseStats().then(data => setStats(data)).catch(console.error);
  }, []);

  const handleExtract = async (text: string) => {
    setIsLoading(true);
    try {
      const extracted = await api.extractStandards(text);
      setResultsMap({}); // Clear previous results to avoid flickering or stale data
      setStandards(extracted);
      if (extracted.length === 0) {
        alert('未提取到规范信息，请检查输入格式');
      }
    } catch (error: unknown) {
      console.error('Error extracting standards:', error);
      const errorMsg = error instanceof Error ? error.message : '未知错误';
      alert(`提取失败: ${errorMsg}\n\n请确认：\n1. 后端服务已启动 (http://localhost:8012)\n2. 网络连接正常`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setStandards([]);
    setResultsMap({});
  };

  const handleAddStandard = () => {
    setStandards([...standards, { code: '', name: '', year: '' }]);
  };

  const handleRemoveStandard = (index: number) => {
    const newStandards = [...standards];
    newStandards.splice(index, 1);
    setStandards(newStandards);
  };

  const handleUpdateStandard = (index: number, field: keyof StandardInfo, value: string) => {
    const newStandards = [...standards];
    newStandards[index] = { ...newStandards[index], [field]: value };
    setStandards(newStandards);
  };

  const handleCheckAll = () => {
    if (standards.length === 0) return;
    // Clear existing results to force a fresh check (prevents stale state/flickering)
    setResultsMap({});
    setCheckTrigger(prev => prev + 1);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <span style={{ fontSize: '20px' }}>📄</span>
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
          onClear={handleClear}
          onAdd={handleAddStandard}
          onRemove={handleRemoveStandard}
          onUpdate={handleUpdateStandard}
          stats={stats}
        />

        {/* Footer & Export Row */}
        {standards.length > 0 && (
          <div style={{ marginTop: '20px', padding: '10px 0', borderTop: '1px solid #eee' }}>
            <div style={{ marginBottom: '15px' }}>
              <button
                className="btn-primary"
                style={{ backgroundColor: '#4f46e5', width: 'auto', padding: '10px 20px', borderRadius: '6px' }}
                onClick={() => setIsExportOpen(true)}
              >
                📑 导出规范引用
              </button>
            </div>
            <div style={{ color: '#888', fontSize: '12px', textAlign: 'left', lineHeight: '1.6' }}>
              <div>说明：</div>
              <div>1. 匹配状态：现行（绿色）、待核验（灰色）、废止/替代（红色）。</div>
              <div>2. 输入结果与最新规范不一致时标记黄色背景。</div>
              <div>3. 结果仅供参考，必要时请以官方发布为准。</div>

            </div>
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
      />
    </div>
  );
}

export default App;
