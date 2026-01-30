import React, { useState } from 'react';
import { api, type StandardInfo, type SearchResult } from '../api';
import { StandardDetailModal } from './StandardDetailModal';
import { FeedbackModal } from './FeedbackModal';
import { openCsresSearch } from '../utils/csres';

interface ComparisonTableProps {
    standards: StandardInfo[];
    resultsMap: Record<string, SearchResult | null | 'loading' | 'error' | 'not_found'>; // New Prop
    onCheckSingle: (code: string, name?: string) => Promise<void>; // New Prop
    onClear?: () => void;
    onAdd?: () => void;
    onRemove?: (index: number) => void;
    onUpdate?: (index: number, field: keyof StandardInfo, value: string) => void;
    checkTrigger?: number; // Kept for backward compat if needed, but logic moved up
    stats?: { count: number; last_updated: string }; // New Prop
}

export const ComparisonTable: React.FC<ComparisonTableProps> = ({
    standards,
    resultsMap,
    onCheckSingle,
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

    if (standards.length === 0) return null;

    return (
        <div className="comparison-table" style={{ marginTop: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2>2. 识别结果</h2>
                <div style={{ fontSize: '12px', color: '#666' }}>
                    {stats ? (
                        <>当前收录全行业规范 {stats.count} 条 · 更新日期 {stats.last_updated.replace(/-/g, '.')}</>
                    ) : (
                        '加载统计中...'
                    )}
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button onClick={onAdd} style={{ background: '#fff', color: '#333', border: '1px solid #ccc', cursor: 'pointer' }}>新增一行</button>
                    <button onClick={onClear} style={{ background: '#ef4444', color: '#fff', border: 'none', cursor: 'pointer' }}>清空表格</button>
                    {/* One-click query removed per request (Use top-level 'Standard Check') */}
                </div>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #eee', fontSize: '13px' }}>
                <thead>
                    <tr style={{ background: '#fafafa', color: '#666', height: '45px', textAlign: 'left' }}>
                        <th style={{ padding: '0 10px', width: '50px' }}>序号</th>
                        <th style={{ padding: '0 10px' }}>规范名称(识别)</th>
                        <th style={{ padding: '0 10px' }}>规范编号(识别)</th>
                        <th style={{ padding: '0 10px', width: '25%', textAlign: 'center' }}>匹配规范</th>
                        <th style={{ width: '180px', padding: '12px 10px', textAlign: 'center', fontWeight: '600', color: '#666' }}>匹配信息</th>
                        <th style={{ width: '10%', textAlign: 'center' }}>状态</th>
                        <th style={{ width: '10%', textAlign: 'center' }}>匹配结果</th>
                        <th style={{ width: '10%', textAlign: 'center' }}>搜建筑</th>
                        <th style={{ width: '15%', textAlign: 'center' }}>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {standards.map((std, index) => (
                        <StandardRowControlled
                            key={index}
                            index={index + 1}
                            standard={std}
                            // Use code as primary key, fallback to name
                            resultStatus={resultsMap[std.code || std.name || 'unknown']}
                            onCheck={() => onCheckSingle(std.code, std.name || undefined)}
                            onViewDetail={(result) => handleViewDetail(result, std)}
                            onRemove={() => onRemove && onRemove(index)}
                            onUpdate={(field, value) => onUpdate && onUpdate(index, field, value)}
                            onFeedback={() => handleFeedback(std)}
                        />
                    ))}
                </tbody>
            </table>

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

    // Calculation Logic
    const calculateMatchScore = (sourceName: string, sourceCode: string, result: SearchResult | null) => {
        if (!result) return { score: "-", isConsistent: "-" };

        let score = 0;
        // Normalize codes: uppercase and remove ALL spaces
        const normSourceCode = sourceCode.replace(/\s+/g, '').toUpperCase();
        const normResultCode = result.code.replace(/\s+/g, '').toUpperCase();

        const normSourceName = sourceName.trim();
        const normResultName = result.name.trim();

        // 1. Code Match
        let isCodePerfect = false;
        if (normSourceCode === normResultCode) {
            score += 50;
            isCodePerfect = true;
        } else if (normResultCode.includes(normSourceCode) || normSourceCode.includes(normResultCode)) {
            score += 30; // Partial code match
        }

        // 2. Name Match
        let isNamePerfect = false;
        if (normSourceName === normResultName) {
            score += 50;
            isNamePerfect = true;
        } else {
            // Simple overlap check
            let matchCount = 0;
            for (let char of normSourceName) {
                if (normResultName.includes(char)) matchCount++;
            }
            const similarity = matchCount / Math.max(normSourceName.length, normResultName.length);
            if (similarity > 0.8) score += 30;
            else if (similarity > 0.5) score += 10;
        }

        // 3. Year/Version Match (Source vs Result)
        const versionRegex = /[（(](.*?)[)）]/g;
        const sourceVersions = [...sourceName.matchAll(versionRegex)].map(m => m[1]);

        let versionMismatch = false;
        if (sourceVersions.length > 0) {
            for (const ver of sourceVersions) {
                if (!result.name.includes(ver)) {
                    versionMismatch = true;
                    break;
                }
            }
        }

        // 4. Reverse Year/Version Check (Result vs Source)
        // Check if result has a version year that source is missing (e.g. 2018年版)
        const resultVersions = [...result.name.matchAll(versionRegex)].map(m => m[1]);
        if (resultVersions.length > 0) {
            for (const ver of resultVersions) {
                // Check if this version string looks like a year/edition (contains digit)
                if (/\d/.test(ver) && !sourceName.includes(ver)) {
                    // If source doesn't have it, treating it as version mismatch if code is perfect
                    if (isCodePerfect) {
                        versionMismatch = true;
                    }
                }
            }
        }

        if (versionMismatch) return { score: `${Math.min(score, 80)}%`, isConsistent: "年份/版本不一致" };

        // Perfect Match
        if (isCodePerfect && isNamePerfect) {
            return { score: "100%", isConsistent: "与匹配规范一致" };
        }

        // Code Perfect, Name Differs
        if (isCodePerfect) {
            if (score >= 80) return { score: `${Math.min(score, 95)}%`, isConsistent: "名称/版本不一致" };
            return { score: `${score}%`, isConsistent: "名称不一致" };
        }

        // Final Cap logic for NON-perfect code matches
        if (versionMismatch) return { score: `${Math.min(score, 90)}%`, isConsistent: "年份/版本不一致" };

        // If code differed (even partially), we flag it
        if (normSourceCode !== normResultCode) return { score: `${score}%`, isConsistent: "编号不一致" };
        if (normSourceName !== normResultName) return { score: `${score}%`, isConsistent: "名称不一致" };

        return { score: `${score}%`, isConsistent: "部分匹配" };
    };

    const { score: matchScore, isConsistent } = calculateMatchScore(standard.name || '', standard.code, result);
    // DEBUG:
    if (matchScore !== '100%' && result) {
        console.log(`[Diff] ${standard.code} vs ${result.code}`, {
            sourceName: standard.name,
            resultName: result.name,
            matchScore,
            isConsistent
        });
    }

    // Determine color based on matchScore
    const getScoreColor = (scoreStr: string) => {
        if (scoreStr === "100%") return '#10b981'; // Green
        return '#f59e0b'; // Orange/Yellow for anything non-100%
    };

    // Replacement Info Logic
    const [replacementInfo, setReplacementInfo] = React.useState<string | null>(null);
    const [isFetchingReplacement, setIsFetchingReplacement] = React.useState(false);

    React.useEffect(() => {
        if (result && (result.status.includes('废止') || result.status.includes('作废') || result.status.includes('被替')) && !replacementInfo && !isFetchingReplacement) {
            setIsFetchingReplacement(true);
            api.getStandardDetail(result.url, result.code)
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
    }, [result]);

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
                        border: (isConsistent.includes('编号') || isConsistent.includes('版本') || isConsistent.includes('年份')) ? '1px solid #f59e0b' : '1px solid #ddd',
                        background: (isConsistent.includes('编号') || isConsistent.includes('版本') || isConsistent.includes('年份')) ? '#fffbeb' : '#fff',
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
                    <span>{result.name} {result.code}</span>
                )}
            </td>

            {/* 匹配度 */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                <span style={{
                    color: getScoreColor(matchScore),
                    fontWeight: 'bold',
                    backgroundColor: matchScore === '100%' ? '#ecfdf5' : '#fffbeb',
                    padding: '4px 8px',
                    borderRadius: '12px',
                    fontSize: '12px'
                }}>
                    {matchScore}
                </span>
            </td>

            {/* 匹配规范状态 */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                {result && (
                    <span style={{
                        background: result.status.includes('现行') ? '#f0fdf4' : '#fef2f2',
                        color: result.status.includes('现行') ? '#15803d' : '#b91c1c',
                        padding: '2px 8px',
                        borderRadius: '2px',
                        fontSize: '12px'
                    }}>
                        {result.status}
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
                        未收录
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
                {result && (result.status.includes('废止') || result.status.includes('作废') || result.status.includes('被替')) ? (
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

            {/* 搜建筑链接 - New Column */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                {result && result.soujianzhu_url && (
                    <a
                        href={result.soujianzhu_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-link"
                        style={{
                            display: 'inline-block',
                            padding: '4px 12px',
                            backgroundColor: '#0ea5e9', // Sky blue
                            color: 'white',
                            borderRadius: '4px',
                            fontSize: '12px',
                            textDecoration: 'none',
                            lineHeight: '1.5',
                            border: 'none',
                            cursor: 'pointer'
                        }}
                    >
                        搜建筑链接
                    </a>
                )}
            </td>

            {/* 详细信息 & 操作 */}
            <td style={{ padding: '0 10px', textAlign: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                    {result && typeof result === 'object' && result.url ? (
                        <button
                            onClick={() => onViewDetail(result)}
                            className="btn-link"
                            style={{
                                display: 'inline-block',
                                padding: '4px 12px',
                                backgroundColor: '#4f46e5',
                                color: 'white',
                                borderRadius: '4px',
                                fontSize: '12px',
                                textDecoration: 'none',
                                lineHeight: '1.5',
                                border: 'none',
                                cursor: 'pointer'
                            }}
                        >
                            工标网查看
                        </button>
                    ) : null}

                    {(!result || resultStatus === 'not_found' || resultStatus === 'error') && (
                        <button
                            onClick={() => {
                                // Direct Jump: Open CSRES search in new tab using GBK form
                                const keyword = standard.name || standard.code;
                                openCsresSearch(keyword);
                            }}
                            className="btn-link"
                            style={{
                                display: 'inline-block',
                                padding: '4px 12px',
                                backgroundColor: '#3b82f6', // Changed to button style
                                color: 'white',
                                borderRadius: '4px',
                                fontSize: '12px',
                                textDecoration: 'none',
                                lineHeight: '1.5',
                                border: 'none',
                                cursor: 'pointer'
                            }}
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
