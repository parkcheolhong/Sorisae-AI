'use client';

import * as React from 'react';
import { resolveApiBaseUrl } from '@/lib/api';

const CUSTOMER_TOKEN_KEY = 'customer_token';

export type SorisaeEngineSpec = {
    engine_type: string;
    label: string;
    description: string;
    default_entry_fn?: string;
    default_context?: Record<string, unknown>;
    adapter_entry_candidates?: string[];
    badge?: string;
};

type DispatchResult = {
    status?: string;
    result?: unknown;   // 백엔드가 반환하는 실제 결과 필드
    output?: unknown;
    error?: string | null;
    entry_fn?: string;
    module?: string;
    adapter_used?: boolean;
    elapsed_ms?: number;
};

type Props = {
    engines: SorisaeEngineSpec[];
    categoryLabel: string;
    categoryId: string;
};

export default function SorisaeExpPanel({ engines, categoryLabel, categoryId }: Props) {
    const apiBaseUrl = React.useMemo(() => resolveApiBaseUrl(), []);
    const [token, setToken] = React.useState('');
    const [selectedEngine, setSelectedEngine] = React.useState<SorisaeEngineSpec | null>(null);
    const [contextInput, setContextInput] = React.useState('{}');
    const [running, setRunning] = React.useState(false);
    const [result, setResult] = React.useState<DispatchResult | null>(null);
    const [dispatchError, setDispatchError] = React.useState('');

    React.useEffect(() => {
        if (typeof window !== 'undefined') {
            setToken(localStorage.getItem(CUSTOMER_TOKEN_KEY) || '');
        }
    }, []);

    const handleSelect = React.useCallback((engine: SorisaeEngineSpec) => {
        setSelectedEngine(engine);
        setContextInput(JSON.stringify(engine.default_context ?? {}, null, 2));
        setResult(null);
        setDispatchError('');
    }, []);

    const handleDispatch = React.useCallback(async () => {
        if (!selectedEngine) return;
        setRunning(true);
        setResult(null);
        setDispatchError('');
        try {
            let contextObj: Record<string, unknown> = {};
            try {
                contextObj = JSON.parse(contextInput);
            } catch {
                throw new Error('컨텍스트 JSON 형식이 올바르지 않습니다.');
            }

            const body: Record<string, unknown> = {
                engine_type: selectedEngine.engine_type,
                entry_fn: selectedEngine.default_entry_fn ?? 'main',
                use_module_adapter: true,
                context: contextObj,
            };
            if (selectedEngine.adapter_entry_candidates?.length) {
                body.adapter_entry_candidates = selectedEngine.adapter_entry_candidates;
            }

            const headers: Record<string, string> = { 'Content-Type': 'application/json' };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(`${apiBaseUrl}/api/marketplace/sorisae/dispatch`, {
                method: 'POST',
                headers,
                body: JSON.stringify(body),
            });

            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload?.detail ?? `HTTP ${response.status}`);
            }
            setResult(payload as DispatchResult);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.';
            setDispatchError(message);
        } finally {
            setRunning(false);
        }
    }, [apiBaseUrl, contextInput, selectedEngine, token]);

    return (
        <div className="workspace-section-stack" data-testid={`sorisae-exp-panel-${categoryId}`}>
            {/* 엔진 카드 그리드 */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {engines.map((engine) => {
                    const isSelected = selectedEngine?.engine_type === engine.engine_type;
                    return (
                        <button
                            key={engine.engine_type}
                            type="button"
                            onClick={() => handleSelect(engine)}
                            className={`workspace-project-card text-left transition-all ${isSelected ? 'ring-2 ring-[#5b8df0]' : 'hover:ring-1 hover:ring-[#5b8df0]/40'}`}
                            data-testid={`engine-card-${engine.engine_type}`}
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <p className="workspace-card-kicker">{categoryLabel}</p>
                                    <h3 className="workspace-card-heading text-sm font-semibold">{engine.label}</h3>
                                </div>
                                <span className="workspace-chip workspace-chip-active text-xs">
                                    {engine.badge ?? '실험적'}
                                </span>
                            </div>
                            <p className="workspace-card-body text-xs mt-2">{engine.description}</p>
                            <div className="mt-3">
                                <code className="text-xs text-[#a0aec0] font-mono">{engine.engine_type}</code>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* dispatch 패널 */}
            {selectedEngine && (
                <div className="workspace-card mt-2" data-testid="sorisae-dispatch-panel">
                    <p className="workspace-card-kicker">실험 실행</p>
                    <h3 className="workspace-card-heading">{selectedEngine.label}</h3>
                    <p className="workspace-card-copy text-xs mb-4">
                        엔진: <code className="font-mono">{selectedEngine.engine_type}</code>
                        {selectedEngine.default_entry_fn ? ` · 진입함수: ${selectedEngine.default_entry_fn}` : ''}
                    </p>

                    {!token ? (
                        <div className="flex flex-col gap-3 rounded-xl border border-[#3a4a6a] bg-[#0e1521] px-5 py-5">
                            <p className="text-sm font-semibold text-white">🔒 로그인 후 실행 가능합니다</p>
                            <p className="text-xs text-[#a0aec0]">
                                소리새 실험 엔진은 마켓플레이스 계정 인증이 필요합니다.<br />
                                로그인하면 이 페이지에서 바로 엔진을 실행하고 결과를 확인할 수 있습니다.
                            </p>
                            <a
                                href="/marketplace"
                                className="workspace-primary-button inline-flex items-center justify-center w-fit text-sm"
                            >
                                마켓플레이스 로그인 →
                            </a>
                        </div>
                    ) : (
                        <>
                            <div className="mb-4">
                                <label className="workspace-card-kicker mb-1 block" htmlFor={`context-input-${selectedEngine.engine_type}`}>
                                    컨텍스트 JSON
                                </label>
                                <textarea
                                    id={`context-input-${selectedEngine.engine_type}`}
                                    value={contextInput}
                                    onChange={(e) => setContextInput(e.target.value)}
                                    rows={6}
                                    className="workspace-input font-mono text-xs w-full"
                                    placeholder="{}"
                                    spellCheck={false}
                                />
                            </div>

                            <button
                                type="button"
                                onClick={() => void handleDispatch()}
                                disabled={running}
                                className="workspace-primary-button"
                                data-testid="dispatch-run-button"
                            >
                                {running ? '실행 중...' : '▶ 실행'}
                            </button>

                            {dispatchError && (
                                <div className="mt-4 rounded-xl border border-red-500 bg-[#1a0e0e] px-4 py-3 text-sm text-red-400 font-mono" data-testid="dispatch-error">
                                    ✗ {dispatchError}
                                </div>
                            )}

                            {result && (
                                <div className="mt-4 workspace-card bg-[#0e1521]" data-testid="dispatch-result">
                                    <div className="flex flex-wrap gap-2 mb-3">
                                        <span className={`workspace-chip ${result.status === 'ok' ? 'workspace-chip-active' : 'border-red-500 text-red-400'}`}>
                                            {result.status === 'ok' ? '✓ 성공' : `✗ ${result.status ?? '오류'}`}
                                        </span>
                                        {result.entry_fn && <span className="workspace-chip">fn: {result.entry_fn}</span>}
                                        {result.elapsed_ms != null && (
                                            <span className="workspace-chip">{result.elapsed_ms.toFixed(0)} ms</span>
                                        )}
                                        {result.adapter_used && <span className="workspace-chip">adapter</span>}
                                    </div>
                                    {result.error ? (
                                        <p className="text-red-400 text-xs font-mono whitespace-pre-wrap">{String(result.error)}</p>
                                    ) : (() => {
                                        const data = result.result ?? result.output;
                                        if (data == null) return null;
                                        return (
                                            <pre className="text-xs text-[#a0f0c0] font-mono whitespace-pre-wrap break-all overflow-auto max-h-96">
                                                {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
                                            </pre>
                                        );
                                    })()}
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
