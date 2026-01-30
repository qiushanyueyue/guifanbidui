import React, { useState } from 'react';
import emailjs from '@emailjs/browser';

interface FeedbackModalProps {
    isOpen: boolean;
    onClose: () => void;
    // Contextual info to pre-fill or send
    identifiedName?: string | null;
    identifiedCode?: string | null;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose, identifiedName, identifiedCode }) => {
    const [problemType, setProblemType] = useState('规范提取错误');
    const [description, setDescription] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [sendingStatus, setSendingStatus] = useState<'idle' | 'success' | 'error'>('idle');

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSending(true);
        setSendingStatus('idle');

        // EmailJS Configuration from Environment Variables
        const SERVICE_ID = import.meta.env.VITE_EMAILJS_SERVICE_ID;
        const TEMPLATE_ID = import.meta.env.VITE_EMAILJS_TEMPLATE_ID;
        const PUBLIC_KEY = import.meta.env.VITE_EMAILJS_PUBLIC_KEY;

        const templateParams = {
            to_name: 'Admin', // Optional, depending on your template
            problem_type: problemType,
            description: description,
            identified_name: identifiedName || 'N/A',
            identified_code: identifiedCode || 'N/A',
            user_agent: navigator.userAgent, // Helpful for debugging
        };

        try {
            if (!SERVICE_ID || !TEMPLATE_ID || !PUBLIC_KEY) {
                console.warn('EmailJS env vars missing. Simulating send.');
                await new Promise(r => setTimeout(r, 1000));
                // Show success even in sim mode to not confuse user during local dev without keys
            } else {
                await emailjs.send(SERVICE_ID, TEMPLATE_ID, templateParams, PUBLIC_KEY);
            }
            setSendingStatus('success');
            setTimeout(() => {
                onClose();
                setSendingStatus('idle');
                setDescription('');
            }, 2000);
        } catch (error) {
            console.error('EmailJS Error:', error);
            setSendingStatus('error');
        } finally {
            setIsSending(false);
        }
    };

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000
        }}>
            <div style={{
                background: '#fff', padding: '24px', borderRadius: '8px', width: '500px',
                maxWidth: '90%'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0 }}>🔍 问题反馈</h3>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer' }}>&times;</button>
                </div>

                <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '6px', marginBottom: '16px', border: '1px solid #e2e8f0' }}>
                    <div style={{ color: '#64748b', fontSize: '13px', marginBottom: '4px' }}>当前规范信息</div>
                    <div style={{ fontWeight: 500 }}>{identifiedName}</div>
                    <div style={{ background: '#e2e8f0', display: 'inline-block', padding: '2px 6px', borderRadius: '4px', fontSize: '12px', marginTop: '4px', color: '#475569' }}>
                        {identifiedCode}
                    </div>
                </div>

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>问题类型</label>
                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                            {['规范提取错误', '规范名称识别错误', '最新规范检索错误', '规范编号识别错误', '版本沿革错误'].map(type => (
                                <label key={type} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', cursor: 'pointer' }}>
                                    <input
                                        type="radio"
                                        name="problemType"
                                        value={type}
                                        checked={problemType === type}
                                        onChange={e => setProblemType(e.target.value)}
                                    />
                                    {type}
                                </label>
                            ))}
                        </div>
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>详细说明</label>
                        <textarea
                            rows={4}
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            placeholder="例如：正确的规范名称应该是... 或者：这个规范的最新版本是..."
                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}
                        />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                        <button type="button" onClick={onClose} style={{ padding: '8px 16px', border: '1px solid #cbd5e1', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>稍后再说</button>
                        <button
                            type="submit"
                            disabled={isSending}
                            style={{
                                padding: '8px 16px',
                                border: 'none',
                                borderRadius: '4px',
                                background: isSending ? '#94a3b8' : '#4f46e5',
                                color: 'white',
                                cursor: isSending ? 'not-allowed' : 'pointer',
                                display: 'flex', alignItems: 'center', gap: '6px'
                            }}
                        >
                            {isSending ? '发送中...' : '提交反馈'}
                        </button>
                    </div>

                    {sendingStatus === 'success' && <div style={{ marginTop: '10px', color: '#10b981', textAlign: 'center' }}>反馈已发送，感谢您的贡献！</div>}
                    {sendingStatus === 'error' && <div style={{ marginTop: '10px', color: '#ef4444', textAlign: 'center' }}>发送失败，请稍后重试。</div>}
                </form>
            </div>
        </div>
    );
};
