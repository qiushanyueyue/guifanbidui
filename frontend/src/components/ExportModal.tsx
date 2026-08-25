import React, { useState, useEffect } from 'react';
import './StandardDetailModal.css'; // Reuse modal styles or create new one

import { api, isInactiveStatus, type StandardInfo, type SearchResult } from '../api';

interface ExportModalProps {
    isOpen: boolean;
    onClose: () => void;
    standards: StandardInfo[];
    resultsMap: Record<string, SearchResult | null | 'loading' | 'error' | 'not_found'>;
    getResultKey: (standard: StandardInfo) => string;
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, standards, resultsMap, getResultKey }) => {
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
            const result = resultsMap[getResultKey(std)];
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

            if (result.recommended_citation && wrapName && wrapCode) {
                validLines.push(line + result.recommended_citation);
                return;
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

    const handleExcelExport = async () => {
        const blob = await api.exportStandards(standards);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = '规范查新结果.xlsx';
        anchor.click();
        URL.revokeObjectURL(url);
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay export-modal-overlay" onClick={onClose}>
            <div className="modal-content export-modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>导出规范引用</h3>
                    <button className="close-btn" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body export-modal-body">
                    {/* Left Panel: Options & List */}
                    <div className="export-modal-left">
                        <div className="options-panel export-options-panel">
                            <h4>格式选项</h4>
                            <div className="export-options">
                                <label>
                                    <input type="checkbox" checked={showIndex} onChange={e => setShowIndex(e.target.checked)} />
                                    <span>显示序号</span>
                                </label>
                                <label>
                                    <input type="checkbox" checked={wrapName} onChange={e => setWrapName(e.target.checked)} />
                                    <span>包裹规范名称 《》</span>
                                </label>
                                <label>
                                    <input type="checkbox" checked={wrapCode} onChange={e => setWrapCode(e.target.checked)} />
                                    <span>包裹规范编号 （）</span>
                                </label>
                            </div>
                        </div>

                        <div className="standard-list export-standard-list">
                            <table className="export-standard-table">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>输入规范 (源)</th>
                                        <th>匹配规范 (校正)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {standards.map((std, i) => {
                                        const result = resultsMap[getResultKey(std)];
                                        const hasMatch = result && typeof result === 'object';

                                        const isAbolished = hasMatch && isInactiveStatus(result.status);

                                        // Compare
                                        const isCodeDifferent = hasMatch && !isAbolished && (std.code.replace(/\s/g, '').toUpperCase() !== result.code.replace(/\s/g, '').toUpperCase());
                                        const isNameDifferent = hasMatch && !isAbolished && (std.name?.trim() !== result.name.trim());
                                        const isDifferent = isCodeDifferent || isNameDifferent;

                                        return (
                                            <tr key={getResultKey(std)}>
                                                <td className="export-index-cell">{i + 1}</td>
                                                <td>
                                                    <div className={isNameDifferent && !isAbolished ? 'export-value export-value-different' : 'export-value'}>
                                                        {std.name}
                                                    </div>
                                                    <div className={isCodeDifferent && !isAbolished ? 'export-code export-code-different' : 'export-code'}>
                                                        {std.code}
                                                    </div>
                                                </td>
                                                <td className={isDifferent || isAbolished ? 'export-match-cell is-different' : 'export-match-cell'}>
                                                    {hasMatch ? (
                                                        isAbolished ? (
                                                            <div className="export-abolished-value">
                                                                [已废止] {result.code}
                                                                <div className="export-subtle-text">不建议引用</div>
                                                            </div>
                                                        ) : (
                                                            <>
                                                                <div className={isNameDifferent ? 'export-match-name is-different' : 'export-match-name'}>{result.name}</div>
                                                                <div className={isCodeDifferent ? 'export-match-code is-different' : 'export-match-code'}>{result.code}</div>
                                                            </>
                                                        )
                                                    ) : (
                                                        <span className="export-unmatched">未匹配</span>
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
                    <div className="export-modal-preview">
                        <h4 className="export-preview-heading">
                            预览文本
                            <span>此处为校正后引用</span>
                        </h4>
                        <textarea
                            className="export-preview-text"
                            readOnly
                            value={previewText}
                        />
                    </div>
                </div>
                <div className="modal-footer export-modal-footer">
                    <button className="btn-secondary" onClick={onClose}>关闭</button>
                    <button className="btn-secondary" onClick={handleExcelExport}>导出 Excel</button>
                    <button className="btn-primary" onClick={handleCopy}>复制文本</button>
                </div>
            </div>
        </div>
    );
};
