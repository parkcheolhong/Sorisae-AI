'use client';

/**
 * HelpPanel — 시각적 사용설명 패널 (모바일 친화)
 *
 * 범위: 모바일 웹앱 시각적 사용설명 전용
 * - 50개국어 도움말 콘텐츠 딕셔너리 기반
 * - 언어 수동 전환 가능 (localStorage 저장)
 * - 접기/펼치기 지원
 */

import React from 'react';
import { getHelpContent, HELP_SUPPORTED_LANGS } from './helpContent';
import { UI_LANGS_FOR_HELP } from './helpLangList';

interface HelpPanelProps {
    helpLang: string;
    onChangeLang: (lang: string) => void;
    onClose: () => void;
}

export default function HelpPanel({ helpLang, onChangeLang, onClose }: HelpPanelProps) {
    const content = getHelpContent(helpLang);

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.75)',
                zIndex: 300,
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'center',
            }}
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div
                style={{
                    background: '#151b23',
                    border: '1px solid #21262d',
                    borderRadius: '16px 16px 0 0',
                    width: '100%',
                    maxWidth: 600,
                    maxHeight: '88vh',
                    overflowY: 'auto',
                    padding: '20px 16px 32px',
                    boxSizing: 'border-box',
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <h2 style={{ flex: 1, margin: 0, fontSize: 18, fontWeight: 800, color: '#58c9ff' }}>
                        {content.panelTitle}
                    </h2>
                    <button
                        onClick={onClose}
                        aria-label={content.closeLabel}
                        style={{
                            background: '#0f1623',
                            border: '1px solid #21262d',
                            color: '#8b949e',
                            borderRadius: 8,
                            padding: '6px 14px',
                            cursor: 'pointer',
                            fontSize: 13,
                            fontWeight: 600,
                            whiteSpace: 'nowrap',
                        }}
                    >
                        {content.closeLabel}
                    </button>
                </div>

                {/* Language selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
                    <label style={{ fontSize: 12, color: '#8b949e', whiteSpace: 'nowrap' }}>
                        {content.langSelectorLabel}
                    </label>
                    <select
                        value={helpLang}
                        onChange={(e) => onChangeLang(e.target.value)}
                        style={{
                            flex: 1,
                            background: '#0f1623',
                            border: '1px solid #31c45d55',
                            color: '#e6edf3',
                            borderRadius: 8,
                            padding: '7px 10px',
                            fontSize: 13,
                            cursor: 'pointer',
                        }}
                    >
                        {UI_LANGS_FOR_HELP.map((lang) => (
                            <option key={lang.code} value={lang.code}>
                                {lang.label}{HELP_SUPPORTED_LANGS.includes(lang.code) ? '' : ' (EN)'}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Help cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {content.cards.map((card, idx) => (
                        <div
                            key={idx}
                            style={{
                                background: '#0d1117',
                                border: '1px solid #21262d',
                                borderRadius: 12,
                                padding: '14px 16px',
                                display: 'flex',
                                gap: 12,
                                alignItems: 'flex-start',
                            }}
                        >
                            <span style={{ fontSize: 24, lineHeight: 1, flexShrink: 0 }}>{card.icon}</span>
                            <div>
                                <div style={{ fontWeight: 700, color: '#e6edf3', fontSize: 15, marginBottom: 4 }}>
                                    {card.title}
                                </div>
                                <div style={{ fontSize: 13, color: '#8b949e', lineHeight: 1.6 }}>
                                    {card.body}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
