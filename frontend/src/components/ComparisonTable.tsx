import React, { useState } from 'react';
import { api, isInactiveStatus, statusLabel, type StandardInfo, type SearchResult, type Stats } from '../api';
import { StandardDetailModal } from './StandardDetailModal';
import { FeedbackModal } from './FeedbackModal';
import { openCsresSearch } from '../utils/csres';

const formatDataUpdatedAt = (value: string | null): string => {
    if (!value) return '暂无';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '暂无';
    return new Intl.DateTimeFormat('zh-CN', {
        timeZone: 'Asia/Shanghai',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    }).format(parsed).replaceAll('/', '.');
};

interface ComparisonTableProps {
    standards: StandardInfo[];
    resultsMap: Record<string, SearchResult | null | 'loading' | 'error' | 'not_found'>; // New Prop
    onCheckSingle: (code: string, name?: string, edition?: string | null, resultKey?: string) => Promise<void>; // New Prop
    getResultKey: (standard: StandardInfo) => string;
    onClear?: () => void;
    onAdd?: () => void;
    onRemove?: (index: number) => void;
    onUpdate?: (index: number, field: keyof StandardInfo, value: string) => void;
    checkTrigger?: number; // Kept for backward compat if needed, but logic moved up
    stats?: Stats;
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({
    standards,
    resultsMap,
    onCheckSingle,
    getResultKey,
    onClear,
    onAdd,
    onRemove,
    onUpdate,
    stats
}) => {
    // Internal resultsMap state REMOVED

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedStandard, setSelectedStandard] = useState<{
        detail: SearchResult;
        identifiedName: string | null;
        identifiedCode: string | null;
    } | null>(null);

    // Feedback Modal State
    const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
    const [feedbackStandard, setFeedbackStandard] = useState<{ name: string, code: string } | null>(null);
    const [filter, setFilter] = useState<'all' | 'issues' | 'obsolete' | 'update' | 'not_found'>('all');
    const [emptyDraft, setEmptyDraft] = useState({ name: '', code: '' });

    // checkStandard logic REMOVED (moved to App.tsx)

    // global checkTrigger effect REMOVED (handled in App.tsx)

    const handleViewDetail = (detail: SearchResult, std: StandardInfo) => {
        setSelectedStandard({
            detail,
            identifiedName: std.name,
            identifiedCode: std.code
        });
        setIsModalOpen(true);
    };

    const handleFeedback = (std: StandardInfo) => {
        setFeedbackStandard({
            name: std.name || '',
            code: std.code
        });
        setIsFeedbackOpen(true);
    };

    const commitEmptyDraft = () => {
        const name = emptyDraft.name.trim();
        const code = emptyDraft.code.trim();
        if (!name && !code) return;
        if (onUpdate) {
            onUpdate(0, 'name', name);
            onUpdate(0, 'code', code);
        } else {
            onAdd?.();
        }
        setEmptyDraft({ name: '', code: '' });
    };

    const handleEmptyDraftKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            commitEmptyDraft();
        }
    };

    const visibleStandards = standards
        .map((standard, index) => ({ standard, index, result: resultsMap[getResultKey(standard)] }))
        .filter(({ result }) => {
            if (filter === 'all') return true;
            if (filter === 'not_found') return result === 'not_found';
            if (!result || typeof result !== 'object') return filter === 'issues';
            if (filter === 'obsolete') return ['obsolete', 'replaced'].includes(result.match_type || '') || isInactiveStatus(result.status);
            if (filter === 'update') return ['revision_missing', 'code_type_mismatch', 'code_mismatch', 'name_mismatch'].includes(result.match_type || '');
            return result.match_type !== 'exact';
        });
    const batchCounts = standards.reduce(
        (counts, standard) => {
            const result = resultsMap[getResultKey(standard)];
            if (result === 'not_found') counts.notFound += 1;
            else if (result && typeof result === 'object') {
                if (result.match_type === 'exact') counts.exact += 1;
                else if (['obsolete', 'replaced'].includes(result.match_type || '') || isInactiveStatus(result.status)) counts.obsolete += 1;
                else counts.issues += 1;
            }
            return counts;
        },
        { exact: 0, issues: 0, obsolete: 0, notFound: 0 },
    );

    return (
        <div className="comparison-table" style={{ marginTop: '20px' }}>
            <div className="results-header">
                <div>
                    <h2>2. 查新结果</h2>
                    <div className="dataset-status" aria-live="polite">
                        {stats ? (
                            <>数据库 {stats.count} 条 · 数据更新时间 {formatDataUpdatedAt(stats.last_updated)}</>
                        ) : (
                            '加载统计中...'
                        )}
                    </div>
                </div>
                <div className="results-actions">
                    <button className="btn-secondary" onClick={onAdd}>新增一行</button>
                    <button className="btn-danger" onClick={onClear}>清空表格</button>
                </div>
            </div>

            <div className="results-toolbar">
                {standards.length > 0 ? ([
                    ['all', '全部'], ['issues', '仅问题'], ['obsolete', '已废止'], ['update', '需更新'], ['not_found', '未找到'],
                ] as const).map(([value, label]) => (
                    <button
                        className={`filter-button${filter === value ? ' is-active' : ''}`}
                        key={value}
                        onClick={() => setFilter(value)}
                    >{label}</button>
                )) : (
                    <span className="empty-toolbar-hint">还没有待查规范，先在下方填写名称和编号</span>
                )}
                <span className="results-summary">
                    {standards.length > 0
                        ? `本次识别 ${standards.length} 条 · 完全一致 ${batchCounts.exact} · 需修改 ${batchCounts.issues} · 已废止 ${batchCounts.obsolete} · 未找到 ${batchCounts.notFound}`
                        : '尚未开始查新'}
                </span>
            </div>

            <div className="table-scroll" tabIndex={0} aria-label="规范查新结果表格，可横向滚动">
            <table>
                <thead>
                    <tr style={{ background: '#fafafa', color: '#666', height: '45px', textAlign: 'left' }}>
                        <th style={{ padding: '0 10px', width: '50px' }}>序号</th>
                        <th style={{ padding: '0 10px', minWidth: '190px' }}>规范名称(识别)</th>
                        <th style={{ padding: '0 10px', minWidth: '170px' }}>规范编号(识别)</th>
                        <th style={{ padding: '0 10px', minWidth: '300px', textAlign: 'center' }}>匹配规范</th>
                        <th style={{ minWidth: '150px', padding: '12px 10px', textAlign: 'center', fontWeight: '600', color: '#666' }}>业务判定</th>
                        <th style={{ minWidth: '220px', textAlign: 'center' }}>规范状态</th>
                        <th style={{ minWidth: '180px', textAlign: 'center' }}>匹配结果</th>
                        <th style={{ minWidth: '120px', textAlign: 'center' }}>搜建筑</th>
                        <th style={{ minWidth: '220px', textAlign: 'center' }}>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {standards.length === 0 ? (
                        <tr className="empty-state-row">
                            <td className="empty-state-index">—</td>
                            <td>
                                <input
                                    className="empty-state-input"
                                    aria-label="新增规范名称"
                                    value={emptyDraft.name}
                                    onChange={(event) => {
                                        const value = event.target.value;
                                        setEmptyDraft((previous) => ({ ...previous, name: value }));
                                    }}
                                    onKeyDown={handleEmptyDraftKeyDown}
                                    placeholder="输入规范名称"
                                />
                            </td>
                            <td>
                                <input
                                    className="empty-state-input"
                                    aria-label="新增规范编号"
                                    value={emptyDraft.code}
                                    onChange={(event) => {
                                        const value = event.target.value;
                                        setEmptyDraft((previous) => ({ ...previous, code: value }));
                                    }}
                                    onKeyDown={handleEmptyDraftKeyDown}
                                    placeholder="输入规范编号，如 GB 50016-2014"
                                />
                            </td>
                            <td colSpan={6}>
                                <div className="empty-state-content">
                                    <strong>暂无待查规范</strong>
                                    <span>填写名称或编号后即可进入查新列表；也可以先粘贴文本，再点击“提取并查新”。</span>
                                    <button
                                        className="btn-secondary empty-state-add"
                                        type="button"
                                        onClick={commitEmptyDraft}
                                        disabled={!emptyDraft.name.trim() && !emptyDraft.code.trim()}
                                    >加入查新列表</button>
                                </div>
                            </td>
                        </tr>
                    ) : visibleStandards.map(({ standard: std, index }) => (
                            <StandardRowControlled
                                key={getResultKey(std)}
                                index={index + 1}
                                standard={std}
                                resultStatus={resultsMap[getResultKey(std)]}
                                onCheck={() => onCheckSingle(std.code, std.name || undefined, std.edition || std.revision_year, getResultKey(std))}
                                onViewDetail={(result) => handleViewDetail(result, std)}
                                onRemove={() => onRemove && onRemove(index)}
                                onUpdate={(field, value) => onUpdate && onUpdate(index, field, value)}
                                onFeedback={() => handleFeedback(std)}
                            />
                        ))}
                </tbody>
            </table>
            </div>

            <div className="results-note" aria-label="查新说明">
                <strong>说明</strong>
                <div className="results-note-grid">
                    <span><b className="legend-chip legend-current">现行</b> 可作为当前版本继续核对。</span>
                    <span><b className="legend-chip legend-update">需更新</b> 输入版本或编号与来源不一致。</span>
                    <span><b className="legend-chip legend-obsolete">已废止</b> 优先查看替代规范。</span>
                    <span><b className="legend-chip legend-unknown">暂无法确认</b> 仅用于来源不可用、未检索到或信息冲突。</span>
                </div>
                <p>系统已按来源证据给出查新结论；正式出图或审查前仍应以发布机构原始文件作为引用依据。</p>
            </div>

            {/* Modal Restored */}
            <StandardDetailModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                detail={selectedStandard?.detail || null}
                identifiedName={selectedStandard?.identifiedName || null}
                identifiedCode={selectedStandard?.identifiedCode || null}
            />

            <FeedbackModal
                isOpen={isFeedbackOpen}
                onClose={() => setIsFeedbackOpen(false)}
                identifiedName={feedbackStandard?.name}
                identifiedCode={feedbackStandard?.code}
            />
        </div>
    );
};

interface StandardRowControlledProps {
    index: number;
    standard: StandardInfo;
    resultStatus: SearchResult | null | 'loading' | 'error' | 'not_found' | undefined;
    onCheck: () => void;
    onViewDetail: (result: SearchResult) => void;
    onRemove: () => void;
    onUpdate: (field: keyof StandardInfo, value: string) => void;
    onFeedback: () => void;
}

const StandardRowControlled: React.FC<StandardRowControlledProps> = ({ index, standard, resultStatus, onCheck, onViewDetail, onRemove, onUpdate, onFeedback }) => {
    const result = (typeof resultStatus === 'object') ? resultStatus : null;
    const isLoading = resultStatus === 'loading';
    const isError = resultStatus === 'error';

    const matchLabels: Record<string, string> = {
        exact: '完全一致',
        revision_missing: '修订版需更新',
        code_type_mismatch: '标准属性错误',
        code_mismatch: '规范编号错误',
        name_mismatch: '规范名称错误',
        obsolete: '已废止',
        replaced: '被替代',
        unknown: '暂无法确认',
        source_conflict: '来源冲突',
    };
    const matchType = result?.match_type || 'unknown';
    const isExact = matchType === 'exact';
    const matchLabel = result ? (matchLabels[matchType] || '暂无法确认') : '-';
    const isIssue = !isExact;
    const isConsistent = isExact ? matchLabel : (result?.message || matchLabel);
    const revisionMismatch = matchType === 'revision_missing'
        || isConsistent.includes('版本')
        || isConsistent.includes('修订版')
        || isConsistent.includes('年份');
    const csresUrl = result?.sources?.find((source) => source.name === 'csres' && source.url)?.url;
    const soujianzhuKeyword = result?.name || standard.name || standard.code;
    const soujianzhuSearchUrl = `https://www.soujianzhu.cn/Search/SouGuifan.aspx?skey=${encodeURIComponent(soujianzhuKeyword)}`;
    const statusTone = result?.status === 'current'
        ? { background: '#f0fdf4', color: '#15803d' }
        : ['upcoming', 'partially_amended'].includes(result?.status || '')
            ? { background: '#fffbeb', color: '#b45309' }
            : result?.status === 'unknown'
                ? { background: '#f3f4f6', color: '#6b7280' }
                : { background: '#fef2f2', color: '#b91c1c' };

    // Replacement Info Logic
    const [replacementInfo, setReplacementInfo] = React.useState<string | null>(null);
    const [isFetchingReplacement, setIsFetchingReplacement] = React.useState(false);

    React.useEffect(() => {
        if (result && isInactiveStatus(result.status) && !replacementInfo && !isFetchingReplacement) {
            setIsFetchingReplacement(true);
            api.getStandardDetail(result.url || undefined, result.code)
                .then(detail => {
                    // Prioritize structured "replaced by" info
                    if (detail.replaced_by_code) {
                        const namePart = detail.replaced_by_name ? ` ${detail.replaced_by_name}` : "";
                        setReplacementInfo(`${detail.replaced_by_code}${namePart}`);
                    } else {
                        // Fallback to raw strings
                        setReplacementInfo(detail.replaces || detail.replaced_by || "暂无替代信息");
                    }
                })
                .catch(err => {
                    console.error("Failed to fetch replacement info", err);
                    setReplacementInfo("查询失败");
                })
                .finally(() => {
                    setIsFetchingReplacement(false);
                });
        }
    }, [result, replacementInfo, isFetchingReplacement]);

    return (
        <tr style={{ borderBottom: '1px solid #f0f0f0', height: '55px' }}>
            <td style={{ padding: '0 10px', color: '#666' }}>{index}</td>

            {/* 规范名称(识别) - Editable */}
            <td style={{ padding: '0 10px' }}>
                <input
                    type="text"
                    value={standard.name || ''}
                    onChange={(e) => onUpdate('name', e.target.value)}
                    style={{
                        border: isConsistent.includes('名称') ? '1px solid #f59e0b' : '1px solid #ddd',
                        background: isConsistent.includes('名称') ? '#fffbeb' : '#fff',
                        borderRadius: '4px',
                        padding: '6px',
                        width: '100%',
                        boxSizing: 'border-box'
                    }}
                />
            </td>

            {/* 规范编号(识别) - Editable */}
            <td style={{ padding: '0 10px' }}>
                <input
                    type="text"
                    value={standard.code}
                    onChange={(e) => onUpdate('code', e.target.value)}
                        style={{
                            border: (isConsistent.includes('编号') || revisionMismatch) ? '1px solid #f59e0b' : '1px solid #ddd',
                            background: (isConsistent.includes('编号') || revisionMismatch) ? '#fffbeb' : '#fff',
                        borderRadius: '4px',
                        padding: '6px',
                        width: '100%',
                        color: '#666',
                        boxSizing: 'border-box'
                    }}
                />
            </td>

            {/* 匹配规范 */}
            <td style={{ padding: '0 10px', color: '#444', textAlign: 'center', verticalAlign: 'middle' }}>
                {isLoading && <span style={{ color: '#999' }}>查询中...</span>}
                {isError && <span style={{ color: 'red' }}>查询失败</span>}
                {resultStatus === 'not_found' && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px' }}>
                        <span style={{ color: '#f59e0b', fontWeight: 'bold', fontSize: '13px' }}>未找到匹配规范</span>
                        <button onClick={onCheck} style={{ color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px' }}>重试</button>
                    </div>
                )}
                {!resultStatus && standard.code && (
                    <button onClick={onCheck} style={{ color: '#60a5fa', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>点击查询</button>
                )}

                {result && (
                    <div>
                        <div>{result.name} {result.code}</div>
                        <div style={{ fontSize: '11px', color: '#777', marginTop: '3px' }}>
                            版本：{result.edition || result.revision_year || '原始版本'} · 来源：{result.canonical_source || '暂无法确认'}
                        </div>
                        <div style={{ fontSize: '11px', color: '#999' }}>
                            最近核验：{result.last_verified_at ? result.last_verified_at.slice(0, 10) : '暂无'}
                            {result.source_conflict ? ' · 来源冲突' : ''}
                        </div>
                    </div>
                )}
            </td>

            {/* 业务判定 */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                <span style={{
                    color: isIssue ? '#b45309' : '#047857',
                    fontWeight: 'bold',
                    backgroundColor: isIssue ? '#fffbeb' : '#ecfdf5',
                    padding: '4px 8px',
                    borderRadius: '12px',
                    fontSize: '12px'
                }}>
                    {matchLabel}
                </span>
            </td>

            {/* 匹配规范状态 */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                {result && (
                    <span style={{
                        background: statusTone.background,
                        color: statusTone.color,
                        padding: '2px 8px',
                        borderRadius: '2px',
                        fontSize: '12px'
                    }}>
                        {result.business_conclusion || result.status_label || statusLabel(result.status)}
                    </span>
                )}
                {resultStatus === 'not_found' && (
                    <span style={{
                        background: '#f3f4f6',
                        color: '#6b7280',
                        padding: '2px 8px',
                        borderRadius: '2px',
                        fontSize: '12px'
                    }}>
                        暂无法确认
                    </span>
                )}
            </td>

            {/* 匹配结果 - Highlight if inconsistent AND Show Replacement if Abolished */}
            <td style={{
                padding: '0 10px',
                textAlign: 'center',
                verticalAlign: 'middle',
                color: isConsistent.includes('不一致') ? '#dc2626' : '#666',
                fontWeight: isConsistent.includes('不一致') ? 'bold' : 'normal',
                fontSize: '13px'
            }}>
                {/* 1. If Abolished, show replacement info */}
                {result && isInactiveStatus(result.status) ? (
                    isFetchingReplacement ? (
                        <span style={{ color: '#666', fontStyle: 'italic' }}>查询最新规范中...</span>
                    ) : (
                        <span style={{ color: '#b91c1c' }}>{replacementInfo || '-'}</span>
                    )
                ) : (
                    /* 2. Otherwise, show consistency status */
                    isConsistent
                )}
            </td>

            {/* 搜建筑链接 - Updated Logic */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                {soujianzhuKeyword && (
                    <a
                        href={result?.soujianzhu_url || soujianzhuSearchUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`source-action ${result?.soujianzhu_url ? 'source-action--soujianzhu' : 'source-action--search'}`}
                    >
                        {result?.soujianzhu_url ? "搜建筑链接" : "搜建筑搜索"}
                    </a>
                )}
            </td>

            {/* 详细信息 & 操作 */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                    {result && csresUrl ? (
                        <button
                            onClick={() => onViewDetail({ ...result, url: csresUrl })}
                            className="source-action source-action--csres"
                        >
                            工标网查看
                        </button>
                    ) : null}

                    {(!result || !csresUrl || resultStatus === 'not_found' || resultStatus === 'error') && (
                        <button
                            onClick={() => {
                                // Direct Jump: Open CSRES search in new tab using GBK form
                                const keyword = standard.name || standard.code;
                                openCsresSearch(keyword);
                            }}
                            className="source-action source-action--csres-search"
                        >
                            工标网搜索
                        </button>
                    )}

                    <button
                        onClick={onRemove}
                        title="删除"
                        style={{
                            color: '#ef4444',
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '18px',
                            fontWeight: 'bold',
                            padding: '4px'
                        }}
                    >
                        ×
                    </button>
                    <button
                        onClick={onFeedback}
                        title="反馈错误"
                        style={{
                            color: '#666',
                            background: 'none',
                            border: 'none',
                            fontSize: '12px',
                            cursor: 'pointer',
                            marginLeft: '5px',
                            textDecoration: 'underline'
                        }}
                    >
                        反馈
                    </button>
                </div>
            </td>
        </tr>
    );
};
