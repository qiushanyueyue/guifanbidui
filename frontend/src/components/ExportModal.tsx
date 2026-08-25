import React, { useState, useEffect } from 'react';
import './StandardDetailModal.css'; // Reuse modal styles or create new one

import { isInactiveStatus, type StandardInfo, type SearchResult } from '../api';

interface ExportModalProps {
    isOpen: boolean;
    onClose: () => void;
    standards: StandardInfo[];
    resultsMap: Record<string, SearchResult | null | 'loading' | 'error' | 'not_found'>;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, standards, resultsMap }) => {
    const [showIndex, setShowIndex] = useState(true);
    const [wrapName, setWrapName] = useState(true);
    const [wrapCode, setWrapCode] = useState(true);
    const [previewText, setPreviewText] = useState('');

    useEffect(() => {
        if (!isOpen) return;
        generatePreview();
    // generatePreview is local and intentionally recreated with modal props.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, showIndex, wrapName, wrapCode, standards, resultsMap]);

    const generatePreview = () => {
        const validLines: string[] = [];
        let validIndex = 1;

        standards.forEach((std) => {
            const result = resultsMap[std.code || std.name || 'unknown'];
            const hasMatch = result && typeof result === 'object';

            // Unknown/conflict records must not be presented as verified
            // current citations. Abolished/replaced records are also omitted.
            const isInactive = hasMatch && isInactiveStatus(result.status);
            const isUnverified = hasMatch && ['unknown', 'conflict'].includes(result.status);
            const isUnmatched = !hasMatch || isInactive || isUnverified;

            // Strict 100% check:
            // 1. Must match
            // 2. Must be verified enough for an export (not abolished,
            // replaced, unknown, or source-conflicted)
            // 3. Name and Code must roughly match (though we use the matched result, so consistency is implied if we trust the result. 
            //    But user said "100% no problem". If we found a result but it has a different year, it's usually considered a match 
            //    but maybe we should only check status.)
            // The user request says: "Right side displayed must be 100% no problem". 
            // Usually this means valid, active standards.

            if (isUnmatched) {
                return; // Skip this standard in preview
            }

            const finalName = result.name;
            const finalCode = result.code;

            let line = '';
            if (showIndex) {
                line += `${validIndex}. `;
                validIndex++;
            }

            if (wrapName) {
                line += `《${finalName}》`;
            } else {
                line += finalName;
            }

            if (finalCode) {
                line += ' ';
                if (wrapCode) {
                    line += `（${finalCode}）`;
                } else {
                    line += finalCode;
                }
            }
            validLines.push(line);
        });
        setPreviewText(validLines.join('\n'));
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(previewText);
        alert('已复制到剪贴板');
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" style={{ width: '900px', maxWidth: '95%', display: 'flex', flexDirection: 'column', maxHeight: '85vh' }} onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>导出规范引用</h3>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body" style={{ display: 'flex', gap: '20px', flex: 1, overflow: 'hidden' }}>
                    {/* Left Panel: Options & List */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <div className="options-panel" style={{ marginBottom: '15px', padding: '15px', background: '#f8fafc', borderRadius: '6px' }}>
                            <h4 style={{ margin: '0 0 10px 0' }}>格式选项</h4>
                            <div style={{ display: 'flex', gap: '20px' }}>
                                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={showIndex} onChange={e => setShowIndex(e.target.checked)} />
                                    <span style={{ marginLeft: '6px' }}>显示序号</span>
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={wrapName} onChange={e => setWrapName(e.target.checked)} />
                                    <span style={{ marginLeft: '6px' }}>包裹规范名称 《》</span>
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={wrapCode} onChange={e => setWrapCode(e.target.checked)} />
                                    <span style={{ marginLeft: '6px' }}>包裹规范编号 （）</span>
                                </label>
                            </div>
                        </div>

                        <div className="standard-list" style={{ flex: 1, overflowY: 'auto', border: '1px solid #eee', borderRadius: '4px' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                                <thead style={{ background: '#f1f5f9', position: 'sticky', top: 0 }}>
                                    <tr>
                                        <th style={{ padding: '8px', textAlign: 'left', width: '40px' }}>#</th>
                                        <th style={{ padding: '8px', textAlign: 'left' }}>输入规范 (源)</th>
                                        <th style={{ padding: '8px', textAlign: 'left' }}>匹配规范 (校正)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {standards.map((std, i) => {
                                        const result = resultsMap[std.code || std.name || 'unknown'];
                                        const hasMatch = result && typeof result === 'object';

                                        const isAbolished = hasMatch && isInactiveStatus(result.status);

                                        // Compare
                                        const isCodeDifferent = hasMatch && !isAbolished && (std.code.replace(/\s/g, '').toUpperCase() !== result.code.replace(/\s/g, '').toUpperCase());
                                        const isNameDifferent = hasMatch && !isAbolished && (std.name?.trim() !== result.name.trim());
                                        const isDifferent = isCodeDifferent || isNameDifferent;

                                        return (
                                            <tr key={i} style={{ borderBottom: '1px solid #f1f1f1' }}>
                                                <td style={{ padding: '8px', color: '#999' }}>{i + 1}</td>
                                                <td style={{ padding: '8px' }}>
                                                    <div style={{ textDecoration: isNameDifferent && !isAbolished ? 'line-through' : 'none', color: isNameDifferent ? '#ef4444' : '#333' }}>
                                                        {std.name}
                                                    </div>
                                                    <div style={{ fontSize: '12px', color: isCodeDifferent ? '#ef4444' : '#666', textDecoration: isCodeDifferent && !isAbolished ? 'line-through' : 'none' }}>
                                                        {std.code}
                                                    </div>
                                                </td>
                                                <td style={{ padding: '8px', background: (isDifferent || isAbolished) ? '#fef2f2' : 'transparent' }}>
                                                    {hasMatch ? (
                                                        isAbolished ? (
                                                            <div style={{ color: '#dc2626', fontWeight: 'bold' }}>
                                                                [已废止] {result.code}
                                                                <div style={{ fontSize: '12px', fontWeight: 'normal' }}>不建议引用</div>
                                                            </div>
                                                        ) : (
                                                            <>
                                                                <div style={{ color: '#15803d', fontWeight: isNameDifferent ? 'bold' : 'normal' }}>{result.name}</div>
                                                                <div style={{ fontSize: '12px', color: '#15803d', fontWeight: isCodeDifferent ? 'bold' : 'normal' }}>{result.code}</div>
                                                            </>
                                                        )
                                                    ) : (
                                                        <span style={{ color: '#ef4444', fontWeight: 'bold' }}>未匹配</span>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Right Panel: Preview */}
                    <div style={{ width: '350px', display: 'flex', flexDirection: 'column' }}>
                        <h4 style={{ margin: '0 0 10px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            预览文本
                            <span style={{ fontSize: '12px', fontWeight: 'normal', color: '#666' }}>此处为校正后引用</span>
                        </h4>
                        <textarea
                            readOnly
                            value={previewText}
                            style={{
                                flex: 1,
                                width: '100%',
                                resize: 'none',
                                padding: '15px',
                                border: '1px solid #ddd',
                                borderRadius: '6px',
                                fontFamily: 'monospace',
                                lineHeight: '1.6',
                                backgroundColor: '#fffbf0', // Light yellow background as requested by "preview paper" look
                                color: '#333'
                            }}
                        />
                    </div>
                </div>
                <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '15px', borderTop: '1px solid #eee' }}>
                    <button className="btn-secondary" onClick={onClose}>关闭</button>
                    <button className="btn-primary" onClick={handleCopy}>复制文本</button>
                </div>
            </div>
        </div>
    );
};
