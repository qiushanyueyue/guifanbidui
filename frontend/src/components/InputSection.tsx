import React, { useState } from 'react';

interface InputSectionProps {
    onExtract: (text: string) => void;
    onCheckAll: () => void;
    isLoading: boolean;
    hasStandards: boolean;
}

export const InputSection: React.FC<InputSectionProps> = ({ onExtract, onCheckAll, isLoading, hasStandards }) => {
    const [text, setText] = useState('');

    const EXAMPLE_TEXT = `设计依据：
(1)《民用建筑设计统一标准》GB 50352-2019
(2)《建筑设计防火规范》GB 50016-2014
(3)《无障碍设计规范》GB 50763-2012
(4)《汽车库、修车库、停车场设计防火规范》GB 50067-2014
(5)《办公建筑设计标准》JGJ 67-2019
(6)《地铁设计规范》（GB 50157-2003）
(7)《公路工程基本建设项目设计文件编制办法》`;

    const handleExampleClick = () => {
        setText(EXAMPLE_TEXT);
    };

    return (
        <div className="input-section card">
            <div className="input-heading">
                <h2>1. 规范输入</h2>
                <button
                    type="button"
                    className="example-button"
                    onClick={handleExampleClick}
                    title="点击填入示例"
                >
                    填入示例
                </button>
            </div>
            <label className="sr-only" htmlFor="standards-input">待查规范文本</label>
            <textarea
                id="standards-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="请输入需要进行查新的规范名称与编号..."
            />

            <div className="button-group">
                <button
                    className="btn-primary"
                    onClick={() => onExtract(text)}
                    disabled={isLoading || !text.trim()}
                >
                    {isLoading ? '正在查新…' : '提取并查新'}
                </button>
                <button
                    className="btn-secondary"
                    onClick={onCheckAll}
                    disabled={!hasStandards || isLoading}
                >
                    重新查新
                </button>
            </div>
        </div>
    );
};
