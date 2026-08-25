import React, { useEffect, useState } from 'react';
import './StandardDetailModal.css';
import { api, isInactiveStatus, statusLabel, type SearchResult, type StandardDetail } from '../api';

interface StandardDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    detail: SearchResult | null;
    identifiedName: string | null;
    identifiedCode: string | null;
}

export const StandardDetailModal: React.FC<StandardDetailModalProps> = ({
    isOpen,
    onClose,
    detail,
    identifiedName,
    identifiedCode
}) => {
    const [fullDetail, setFullDetail] = useState<StandardDetail | null>(null);
    const [redirectUrl, setRedirectUrl] = useState<string>('');
    const detailKey = detail ? `${detail.id ?? ''}:${detail.code}` : '';
    const [loadedKey, setLoadedKey] = useState('');


    useEffect(() => {
        if (isOpen && detail) {
            api.getStandardDetail(detail.url || undefined, detail.code)
                .then(data => {
                    setFullDetail(data);
                    setLoadedKey(detailKey);
                })
                .catch(err => {
                    console.error("Failed to fetch detail", err);
                    setLoadedKey(detailKey);
                })
            const keyword = detail.name || detail.code || '';
            if (keyword && !detail.url) {
                api.getCsresRedirectUrl(keyword)
                    .then(url => setRedirectUrl(url))
                    .catch(err => console.error("Failed to get redirect url", err));
            }
        }
    }, [isOpen, detail, detailKey, detail?.url, detail?.name, detail?.code]);

    if (!isOpen || !detail) return null;

    // Determine Status Class
    const getStatusClass = (status: string) => {
        if (!status) return '';
        if (status === 'current') return 'active';
        if (isInactiveStatus(status)) return 'abolished';
        return '';
    };

    const targetUrl = fullDetail?.url || detail.url || redirectUrl;
    const isLoading = loadedKey !== detailKey;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>标准详细信息</h3>
                    <button className="close-button" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body">
                    {/* Left Sidebar: Identified Info & History */}
                    <div className="modal-sidebar">
                        <div className="sidebar-section">
                            <label>识别名称</label>
                            <div className="info-box">{identifiedName || '-'}</div>
                        </div>
                        <div className="sidebar-section">
                            <label>识别编号</label>
                            <div className="info-box">{identifiedCode}</div>
                        </div>

                        <div className="sidebar-section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                            <label>版本沿革</label>
                            {/* History Timeline */}
                            <div className="timeline" style={{ overflowY: 'auto' }}>
                                {fullDetail?.replaces && (
                                    <div className="timeline-item">
                                        <div className="timeline-dot"></div>
                                        <div className="timeline-content">
                                            <div className="timeline-tag">替代:</div>
                                            <div className="timeline-text">{fullDetail.replaces}</div>
                                            <div className="abolished-tag">已作废/废止</div>
                                        </div>
                                    </div>
                                )}
                                <div className={`timeline-item ${detail.status === 'current' ? 'current' : ''}`}>
                                    <div className="timeline-dot"></div>
                                    <div className="timeline-content">
                                        <div className="timeline-text" style={{ fontWeight: 'bold' }}>{detail.name}</div>
                                        <div className="timeline-code">{detail.code}</div>
                                        {detail.status && (
                                            <div className={detail.status === 'current' ? 'current-tag' : 'abolished-tag'}>
                                                {detail.status_label || statusLabel(detail.status)}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                {fullDetail?.replaced_by && (
                                    <div className="timeline-item">
                                        <div className="timeline-dot"></div>
                                        <div className="timeline-content">
                                            <div className="timeline-tag">被替代为:</div>
                                            <div className="timeline-text">{fullDetail.replaced_by}</div>
                                            <div className="current-tag">后续规范（待核验）</div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Content: Detailed Info */}
                    <div className="modal-main-info">
                        <div className="main-header">
                            <h2>{detail.name}</h2>
                            <div className="header-meta">
                                <span>规范编号: {detail.code}</span>
                                {detail.status && <span className={`status-tag ${getStatusClass(detail.status)}`}>
                                    {detail.status_label || statusLabel(detail.status)}
                                </span>}
                            </div>
                            <div className="header-badges">
                                <span className="header-match high">匹配度 100%</span>
                                <span className="header-match" style={{ marginLeft: '10px' }}>发布日期 {fullDetail?.release_date || '-'}</span>
                                {fullDetail && isInactiveStatus(fullDetail.status) && (
                                    <span className="header-match" style={{ marginLeft: '10px' }}>废止日期 {fullDetail.obsolete_date || '-'}</span>
                                )}
                                <span className="header-match" style={{ marginLeft: '10px' }}>实施日期 {fullDetail?.implement_date || '-'}</span>
                            </div>
                        </div>

                        {isLoading ? (
                            <div style={{ padding: '40px', textAlign: 'center', color: '#666', marginTop: '20px' }}>
                                <div className="loading-spinner" style={{ marginBottom: '10px' }}></div>
                                正在从本地规范数据库读取...
                            </div>
                        ) : (
                            <>
                                <div className="info-grid">
                                    <div className="info-item full-width">
                                        <label>英文名称</label>
                                        <div>{fullDetail?.englishName || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>发布部门</label>
                                        <div>{fullDetail?.department || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>归口单位</label>
                                        <div>{fullDetail?.technical_committee || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>发布日期</label>
                                        <div>{fullDetail?.release_date || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>实施日期</label>
                                        <div>{fullDetail?.implement_date || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>出版社</label>
                                        <div>{fullDetail?.publisher || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>页数</label>
                                        <div>{fullDetail?.pages || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>ICS分类</label>
                                        <div>{fullDetail?.ics || '-'}</div>
                                    </div>
                                    <div className="info-item">
                                        <label>中标分类</label>
                                        <div>{fullDetail?.ccs || '-'}</div>
                                    </div>
                                    <div className="info-item full-width">
                                        <label>替代情况</label>
                                        <div>{fullDetail?.replaces || '-'}</div>
                                    </div>
                                    <div className="info-item full-width">
                                        <label>被替代为</label>
                                        <div>{fullDetail?.replaced_by || '-'}</div>
                                    </div>
                                </div>

                                <div className="description-section">
                                    <label>说明</label>
                                    <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px', marginBottom: '20px', minHeight: '60px' }}>
                                        {fullDetail?.replaces ? `替代${fullDetail.replaces}废止` : '暂无替代说明'}
                                    </div>

                                    <label>简介</label>
                                    <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px', minHeight: '80px' }}>
                                        本规范适用于... (此处为工标网暂未爬取的简介内容)
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>

                <div className="modal-footer">
                    {targetUrl && (
                        <a href={targetUrl} target="_blank" rel="noreferrer" className="source-link" style={{ marginRight: 'auto', display: 'flex', alignItems: 'center', color: '#2563eb', textDecoration: 'none', fontWeight: 'bold', fontSize: '14px' }}>
                            详细信息跳转 &gt;
                        </a>
                    )}
                    <button className="close-btn" onClick={onClose}>关闭</button>
                </div>
            </div>
        </div>
    );
};
