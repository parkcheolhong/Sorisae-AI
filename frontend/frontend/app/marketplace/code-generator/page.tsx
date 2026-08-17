'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { MarketplaceLeftRail, MarketplaceRightRail } from '@/components/marketplace/marketplace-rails';
import { resolveApiBaseUrl } from '@/lib/api';

const CUSTOMER_TOKEN_KEY = 'customer_token';
const TOKEN_CANDIDATE_KEYS = [CUSTOMER_TOKEN_KEY, 'admin_token', 'token', 'access_token'] as const;

interface GenerateResult {
    project_name: string;
    profile: string;
    task: string;
    file_count: number;
    files: string[];
    metadata: Record<string, unknown>;
    generation_id?: string;
    created_at?: string;
    download_url?: string;
}

interface Profiles {
    python: string[];
    non_python: string[];
    multi: boolean;
}

interface GenerationHistoryItem {
    generation_id: string;
    project_name: string;
    profile: string;
    task_preview: string;
    file_count: number;
    created_at: string;
    download_url: string;
}

export default function CodeGeneratorPage() {
    const apiBaseUrl = resolveApiBaseUrl();
    const [profiles, setProfiles] = useState<Profiles | null>(null);
    const [projectName, setProjectName] = useState('my-project');
    const [task, setTask] = useState('');
    const [selectedProfile, setSelectedProfile] = useState('python_fastapi');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<GenerateResult | null>(null);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [historyItems, setHistoryItems] = useState<GenerationHistoryItem[]>([]);
    const [previewPulse, setPreviewPulse] = useState(0);
    const [interpreterText, setInterpreterText] = useState('안녕하세요');
    const [interpreterSourceLang, setInterpreterSourceLang] = useState('ko');
    const [interpreterTargetLang, setInterpreterTargetLang] = useState('en');
    const [interpreterResult, setInterpreterResult] = useState<string>('');
    const [interpreterMode, setInterpreterMode] = useState<string>('');
    const [interpreterLoading, setInterpreterLoading] = useState(false);
    const [interpreterError, setInterpreterError] = useState<string | null>(null);
    const [tutorLoading, setTutorLoading] = useState(false);
    const [tutorError, setTutorError] = useState<string | null>(null);
    const [tutorMode, setTutorMode] = useState<string>('');
    const [tutorResult, setTutorResult] = useState<string>('');
    // 소리새 AI 튜터 전용 상태
    const [tutorPathItems, setTutorPathItems] = useState<string[]>([]);
    const [tutorChallenge, setTutorChallenge] = useState<string>('');
    const [tutorEncouragement, setTutorEncouragement] = useState<string>('');
    const [tutorFeedback, setTutorFeedback] = useState<string[]>([]);
    const [tutorPanelLoading, setTutorPanelLoading] = useState(false);
    const [tutorPanelError, setTutorPanelError] = useState<string | null>(null);
    const [tutorPanelLoaded, setTutorPanelLoaded] = useState(false);
    const [musicEmotion, setMusicEmotion] = useState('happy');
    const [musicIntensity, setMusicIntensity] = useState('0.7');
    const [musicTheme, setMusicTheme] = useState('소리새 테마');
    const [musicCode, setMusicCode] = useState('def chorus():\n    return "sing"');
    const [musicCodeEmotion, setMusicCodeEmotion] = useState('creative');
    const [musicComposeResult, setMusicComposeResult] = useState<Record<string, unknown> | null>(null);
    const [musicCodeResult, setMusicCodeResult] = useState<Record<string, unknown> | null>(null);
    const [musicFriendResult, setMusicFriendResult] = useState<Record<string, unknown> | null>(null);
    const [musicMode, setMusicMode] = useState<string>('');
    const [musicLoading, setMusicLoading] = useState(false);
    const [musicError, setMusicError] = useState<string | null>(null);

    const getAuthToken = useCallback(() => {
        for (const key of TOKEN_CANDIDATE_KEYS) {
            const value = localStorage.getItem(key);
            if (typeof value === 'string' && value.trim()) {
                return value;
            }
        }
        return '';
    }, []);

    const getAuthHeaders = useCallback(() => {
        const token = getAuthToken();
        const headers: Record<string, string> = {};
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        return headers;
    }, [getAuthToken]);

    const buildApiUrl = (path: string) => {
        if (path.startsWith('http://') || path.startsWith('https://')) {
            return path;
        }
        return `${apiBaseUrl}${path}`;
    };

    const loadHistory = useCallback(async () => {
        const authToken = getAuthToken();
        if (!authToken) {
            setHistoryItems([]);
            return;
        }
        setHistoryLoading(true);
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/code-generator/history`, {
                headers: {
                    Authorization: `Bearer ${authToken}`,
                },
            });
            if (!res.ok) {
                if (res.status === 401) {
                    setHistoryItems([]);
                }
                return;
            }
            const payload = await res.json();
            const items = Array.isArray(payload?.items) ? payload.items : [];
            setHistoryItems(items as GenerationHistoryItem[]);
        } catch {
            /* ignore */
        } finally {
            setHistoryLoading(false);
        }
    }, [apiBaseUrl, getAuthToken]);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${apiBaseUrl}/api/marketplace/code-generator/profiles`);
                if (res.ok) setProfiles(await res.json());
            } catch { /* ignore */ }
        })();
    }, [apiBaseUrl]);

    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    useEffect(() => {
        if (!loading) {
            return;
        }
        const timer = window.setInterval(() => {
            setPreviewPulse((prev) => prev + 1);
        }, 700);
        return () => window.clearInterval(timer);
    }, [loading]);

    // 코드 생성 완료 시 소리새 AI 튜터 자동 활성화
    useEffect(() => {
        if (result) {
            void loadTutorPanel();
            void handleTutorAnalyzeCode(livePreviewCode);
        }
    }, [result]); // eslint-disable-line react-hooks/exhaustive-deps

    const liveStatusText = useMemo(() => {
        if (loading) {
            const dots = '.'.repeat((previewPulse % 3) + 1);
            return `실시간 생성 중${dots}`;
        }
        if (result) {
            return '생성 결과 반영 완료';
        }
        return '대기 중';
    }, [loading, previewPulse, result]);

    const previewFileNames = useMemo(() => {
        if (result?.files?.length) {
            return result.files.slice(0, 8);
        }
        const profileFolder = selectedProfile.replace(/[^a-zA-Z0-9_-]/g, '-');
        return [
            `${projectName || 'my-project'}/README.md`,
            `${projectName || 'my-project'}/src/main.${selectedProfile.includes('python') ? 'py' : 'ts'}`,
            `${projectName || 'my-project'}/src/${profileFolder}/service.${selectedProfile.includes('python') ? 'py' : 'ts'}`,
            `${projectName || 'my-project'}/tests/test_health.${selectedProfile.includes('python') ? 'py' : 'ts'}`,
        ];
    }, [projectName, result, selectedProfile]);

    const livePreviewCode = useMemo(() => {
        const safeTask = (task || '요구사항을 입력하면 코드 미리보기가 실시간으로 갱신됩니다.').replace(/\s+/g, ' ').trim();
        const safeProject = (projectName || 'my-project').trim();
        const lang = selectedProfile.includes('python') ? 'python' : 'typescript';
        if (lang === 'python') {
            return [
                `# project: ${safeProject}`,
                `# profile: ${selectedProfile}`,
                `# status: ${liveStatusText}`,
                '',
                'from fastapi import FastAPI',
                '',
                `app = FastAPI(title="${safeProject}")`,
                '',
                '@app.get("/health")',
                'def health() -> dict[str, str]:',
                `    return {"status": "ok", "task": "${safeTask.slice(0, 80)}"}`,
            ].join('\n');
        }
        return [
            `// project: ${safeProject}`,
            `// profile: ${selectedProfile}`,
            `// status: ${liveStatusText}`,
            '',
            'export type HealthResponse = {',
            '  status: string;',
            '  task: string;',
            '};',
            '',
            'export const health = (): HealthResponse => ({',
            "  status: 'ok',",
            `  task: '${safeTask.slice(0, 80)}',`,
            '});',
        ].join('\n');
    }, [liveStatusText, projectName, selectedProfile, task]);

    const liveLogItems = useMemo(() => {
        if (loading) {
            const step = previewPulse % 4;
            if (step === 0) return ['입력 분석', '프로젝트 구조 설계', '템플릿 생성', '코드 작성'];
            if (step === 1) return ['입력 분석 완료', '프로젝트 구조 설계', '템플릿 생성', '코드 작성'];
            if (step === 2) return ['입력 분석 완료', '구조 설계 완료', '템플릿 생성', '코드 작성'];
            return ['입력 분석 완료', '구조 설계 완료', '템플릿 생성 완료', '코드 작성'];
        }
        if (result) {
            return ['생성 완료', `${result.file_count}개 파일 구성`, 'ZIP 다운로드 가능'];
        }
        return ['생성 요청 대기', '입력값 변경 시 미리보기 자동 반영'];
    }, [loading, previewPulse, result]);

    const readResponsePayload = async (res: Response) => {
        const contentType = res.headers.get('content-type') || '';
        const raw = await res.text();
        if (!raw) {
            return { data: null as any, raw, contentType };
        }
        if (contentType.includes('application/json')) {
            return { data: JSON.parse(raw), raw, contentType };
        }
        try {
            return { data: JSON.parse(raw), raw, contentType };
        } catch {
            return { data: null as any, raw, contentType };
        }
    };

    const handleGenerate = useCallback(async () => {
        if (!task.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/code-generator/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    project_name: projectName.trim(),
                    task: task.trim(),
                    profile: selectedProfile,
                }),
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                const detail = payload.data?.detail || payload.data?.message;
                if (detail) {
                    throw new Error(detail);
                }
                if (payload.raw.trimStart().startsWith('<!DOCTYPE') || payload.raw.trimStart().startsWith('<html')) {
                    throw new Error(`서버 오류 (${res.status}): JSON 대신 HTML이 반환되었습니다. 프록시/라우팅 설정을 확인하세요.`);
                }
                throw new Error(`서버 오류 (${res.status})`);
            }
            if (!payload.data) {
                throw new Error('응답 형식 오류: JSON 본문이 필요합니다.');
            }
            setResult(payload.data);
            loadHistory();
        } catch (err: any) {
            setError(err?.message || '코드 생성 실패');
        } finally {
            setLoading(false);
        }
    }, [apiBaseUrl, loadHistory, projectName, task, selectedProfile]);

    const handleDownload = useCallback(async (downloadUrl: string, fallbackName: string) => {
        try {
            const response = await fetch(buildApiUrl(downloadUrl), {
                headers: {
                    ...getAuthHeaders(),
                },
            });
            if (!response.ok) {
                throw new Error(`다운로드 실패 (${response.status})`);
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = fallbackName;
            anchor.click();
            URL.revokeObjectURL(url);
        } catch (err: any) {
            setError(err?.message || 'ZIP 다운로드 실패');
        }
    }, [apiBaseUrl]);

    const handleInterpreterTranslate = useCallback(async () => {
        const text = interpreterText.trim();
        if (!text) {
            setInterpreterError('번역할 문장을 입력하세요.');
            return;
        }

        setInterpreterLoading(true);
        setInterpreterError(null);
        setInterpreterResult('');
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/interpreter/translate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    text,
                    source_lang: interpreterSourceLang,
                    target_lang: interpreterTargetLang,
                }),
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                throw new Error(payload.data?.detail || `통역 요청 실패 (${res.status})`);
            }
            const translated = String(payload.data?.translated_text || '').trim();
            setInterpreterResult(translated || '(빈 응답)');
            setInterpreterMode(String(payload.data?.mode || 'unknown'));
        } catch (err: any) {
            setInterpreterError(err?.message || '통역 요청 실패');
        } finally {
            setInterpreterLoading(false);
        }
    }, [apiBaseUrl, interpreterSourceLang, interpreterTargetLang, interpreterText]);

    const handleTutorFromInterpreter = useCallback(async () => {
        const translated = interpreterResult.trim();
        const source = interpreterText.trim();
        const tutorInput = translated || source;
        if (!tutorInput) {
            setTutorError('통역 원문 또는 통역 결과가 필요합니다.');
            return;
        }

        setTutorLoading(true);
        setTutorError(null);
        setTutorResult('');
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/sorisae/dispatch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    engine_type: 'decision',
                    entry_fn: 'main',
                    context: {
                        problem: `학습용 튜터 설명 요청: ${tutorInput}`,
                    },
                }),
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                throw new Error(payload.data?.detail?.error_message || payload.data?.detail || `튜터 요청 실패 (${res.status})`);
            }

            const resultPayload = payload.data?.result || {};
            const chosenOption = String(resultPayload?.chosen_option || '').trim();
            const confidence = resultPayload?.confidence_score;
            const reasoning = Array.isArray(resultPayload?.reasoning)
                ? resultPayload.reasoning.filter((item: unknown) => typeof item === 'string' && item.trim()).slice(0, 3)
                : [];

            const lines: string[] = [];
            if (chosenOption) {
                lines.push(`학습 방향: ${chosenOption}`);
            }
            if (typeof confidence === 'number') {
                lines.push(`신뢰도: ${(confidence * 100).toFixed(1)}%`);
            }
            if (reasoning.length) {
                lines.push('튜터 가이드:');
                reasoning.forEach((item: string) => lines.push(`- ${item}`));
            }
            if (!lines.length) {
                lines.push('소리새 튜터 응답이 비어 있습니다. 입력 문장을 바꿔 다시 시도하세요.');
            }

            setTutorResult(lines.join('\n'));
            setTutorMode(String(payload.data?.status || 'ok'));
        } catch (err: any) {
            setTutorError(err?.message || '학습용 튜터 요청 실패');
        } finally {
            setTutorLoading(false);
        }
    }, [apiBaseUrl, getAuthHeaders, interpreterResult, interpreterText]);

    const loadTutorPanel = useCallback(async () => {
        setTutorPanelLoading(true);
        setTutorPanelError(null);
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/sorisae/tutor/path`, {
                headers: { ...getAuthHeaders() },
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                throw new Error(payload.data?.detail || `튜터 로드 실패 (${res.status})`);
            }
            const data = payload.data;
            setTutorPathItems(Array.isArray(data?.learning_path) ? data.learning_path : []);
            setTutorChallenge(typeof data?.challenge === 'string' ? data.challenge : '');
            setTutorEncouragement(typeof data?.encouragement === 'string' ? data.encouragement : '');
            setTutorPanelLoaded(true);
        } catch (err: any) {
            setTutorPanelError(err?.message || '소리새 튜터 로드 실패');
        } finally {
            setTutorPanelLoading(false);
        }
    }, [apiBaseUrl, getAuthHeaders]);

    const handleTutorAnalyzeCode = useCallback(async (code: string) => {
        if (!code.trim()) return;
        try {
            const language = selectedProfile.includes('python') ? 'python' : 'typescript';
            const res = await fetch(`${apiBaseUrl}/api/marketplace/sorisae/tutor/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
                body: JSON.stringify({ code, language }),
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) return;
            const items = Array.isArray(payload.data?.feedback) ? payload.data.feedback : [];
            setTutorFeedback(items);
        } catch { /* non-critical */ }
    }, [apiBaseUrl, getAuthHeaders, selectedProfile]);

    const handleMusicCompose = useCallback(async () => {
        setMusicLoading(true);
        setMusicError(null);
        setMusicComposeResult(null);
        try {
            const intensity = Number.parseFloat(musicIntensity);
            const res = await fetch(`${apiBaseUrl}/api/marketplace/music/compose/emotion`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    emotion: musicEmotion,
                    intensity: Number.isFinite(intensity) ? intensity : 0.7,
                    theme: musicTheme.trim() || undefined,
                }),
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                throw new Error(payload.data?.detail || `음악 생성 실패 (${res.status})`);
            }
            setMusicComposeResult(payload.data as Record<string, unknown>);
            setMusicMode(String(payload.data?.mode || 'unknown'));
        } catch (err: any) {
            setMusicError(err?.message || '음악 생성 실패');
        } finally {
            setMusicLoading(false);
        }
    }, [apiBaseUrl, musicEmotion, musicIntensity, musicTheme]);

    const handleMusicComposeFromCode = useCallback(async () => {
        const code = musicCode.trim();
        if (!code) {
            setMusicError('작곡에 사용할 코드를 입력하세요.');
            return;
        }
        setMusicLoading(true);
        setMusicError(null);
        setMusicCodeResult(null);
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/music/compose/code`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    code,
                    emotion: musicCodeEmotion,
                }),
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                throw new Error(payload.data?.detail || `코드 작곡 실패 (${res.status})`);
            }
            setMusicCodeResult(payload.data as Record<string, unknown>);
            setMusicMode(String(payload.data?.mode || 'unknown'));
        } catch (err: any) {
            setMusicError(err?.message || '코드 작곡 실패');
        } finally {
            setMusicLoading(false);
        }
    }, [apiBaseUrl, musicCode, musicCodeEmotion]);

    const handleMusicCollaboration = useCallback(async () => {
        setMusicLoading(true);
        setMusicError(null);
        setMusicFriendResult(null);
        try {
            const res = await fetch(`${apiBaseUrl}/api/marketplace/music/friends/demo`, {
                method: 'POST',
                headers: {
                    ...getAuthHeaders(),
                },
            });
            const payload = await readResponsePayload(res);
            if (!res.ok) {
                throw new Error(payload.data?.detail || `협업 연결 실패 (${res.status})`);
            }
            setMusicFriendResult(payload.data as Record<string, unknown>);
            setMusicMode(String(payload.data?.mode || 'unknown'));
        } catch (err: any) {
            setMusicError(err?.message || '협업 연결 실패');
        } finally {
            setMusicLoading(false);
        }
    }, [apiBaseUrl]);

    const allProfiles = [
        ...(profiles?.python || []).map(p => ({ id: p, group: 'Python', icon: '🐍' })),
        ...(profiles?.non_python || []).map(p => ({ id: p, group: 'Non-Python', icon: '⚡' })),
    ];

    return (
        <div className="workspace-shell">
            <MarketplaceLeftRail activeRailId="code-generator" />

            <main className="workspace-stage">
                <div className="workspace-topbar">
                    <div>
                        <p className="workspace-overline">Code Generator</p>
                        <h1 className="workspace-page-title">AI 코드 제너레이터</h1>
                        <p className="workspace-page-description">
                            프로필 선택 → 태스크 입력 → AI가 전체 프로젝트 코드를 자동 생성합니다.
                        </p>
                    </div>
                </div>

                <div className="workspace-content-grid workspace-content-grid-with-sidebar">
                    <div className="workspace-main-content" style={{ display: 'grid', gap: 18 }}>
                        <div className="workspace-card">
                            <h2 className="workspace-card-title">⚙️ 프로젝트 설정</h2>
                            <input type="text" placeholder="프로젝트 이름" value={projectName}
                                data-testid="marketplace-codegen-project-name"
                                onChange={e => setProjectName(e.target.value)}
                                style={{ width: '100%', marginTop: 14, padding: '14px 18px', borderRadius: 'var(--workspace-radius-md)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 15 }}
                            />
                            <textarea placeholder="태스크 설명 (예: REST API 사용자 관리 시스템 생성)" value={task}
                                data-testid="marketplace-codegen-task"
                                onChange={e => setTask(e.target.value)}
                                className="workspace-admin-command-textarea"
                                style={{ minHeight: 100, marginTop: 10 }}
                            />
                        </div>

                        <button onClick={handleGenerate} disabled={!task.trim() || loading}
                            data-testid="marketplace-codegen-generate-btn"
                            className="workspace-primary-button"
                            style={{ padding: '18px 32px', fontSize: 16, fontWeight: 800, cursor: task.trim() && !loading ? 'pointer' : 'not-allowed', opacity: task.trim() && !loading ? 1 : 0.5, borderRadius: 'var(--workspace-radius-lg)' }}>
                            {loading ? '⏳ 생성 중...' : '🚀 코드 생성'}
                        </button>

                        {error && (
                            <div style={{ padding: '14px 18px', borderRadius: 'var(--workspace-radius-md)', background: 'rgba(255,107,107,0.1)', border: '1px solid rgba(255,107,107,0.3)', color: 'var(--workspace-danger)', fontSize: 14 }}>
                                ⚠️ {error}
                            </div>
                        )}

                        {/* 소리새 AI 튜터 패널 */}
                        <div className="workspace-card" data-testid="marketplace-sorisae-tutor-panel">
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                                <h2 className="workspace-card-title" style={{ marginBottom: 0 }}>🎓 소리새 AI 튜터</h2>
                                <button
                                    onClick={loadTutorPanel}
                                    disabled={tutorPanelLoading}
                                    className="workspace-primary-button"
                                    style={{ padding: '8px 16px', fontSize: 13, fontWeight: 700, opacity: tutorPanelLoading ? 0.5 : 1, cursor: tutorPanelLoading ? 'not-allowed' : 'pointer' }}
                                >
                                    {tutorPanelLoading ? '⏳ 로딩...' : '🔄 불러오기'}
                                </button>
                            </div>

                            {tutorPanelError && (
                                <div style={{ padding: '10px 14px', borderRadius: 'var(--workspace-radius-sm)', background: 'rgba(255,107,107,0.1)', border: '1px solid rgba(255,107,107,0.3)', color: 'var(--workspace-danger)', fontSize: 13, marginBottom: 12 }}>
                                    ⚠️ {tutorPanelError}
                                </div>
                            )}

                            {!tutorPanelLoaded && !tutorPanelLoading && !tutorPanelError && (
                                <p style={{ fontSize: 13, color: 'var(--workspace-muted)', margin: 0 }}>
                                    코드 생성 후 자동으로 활성화되거나 위 '불러오기' 버튼을 누르세요.
                                </p>
                            )}

                            {tutorEncouragement && (
                                <div style={{ padding: '12px 16px', borderRadius: 'var(--workspace-radius-md)', background: 'rgba(119,212,255,0.06)', border: '1px solid rgba(119,212,255,0.15)', marginBottom: 14 }}>
                                    <p style={{ margin: 0, fontSize: 14, color: 'var(--workspace-text)' }}>{tutorEncouragement}</p>
                                </div>
                            )}

                            {tutorChallenge && (
                                <div style={{ marginBottom: 14 }}>
                                    <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--workspace-accent)', marginBottom: 8 }}>🏆 오늘의 도전 과제</h3>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                                        <span style={{ fontSize: 14, color: 'var(--workspace-text)', flex: 1 }}>{tutorChallenge}</span>
                                        <button
                                            onClick={() => { setTask(tutorChallenge); setProjectName('sorisae-challenge'); }}
                                            style={{ padding: '6px 12px', fontSize: 11, fontWeight: 700, borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-accent)', color: 'var(--workspace-accent)', background: 'rgba(119,212,255,0.08)', cursor: 'pointer', whiteSpace: 'nowrap' }}
                                        >
                                            태스크 적용 →
                                        </button>
                                    </div>
                                </div>
                            )}

                            {tutorPathItems.length > 0 && (
                                <div style={{ marginBottom: 14 }}>
                                    <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--workspace-accent)', marginBottom: 8 }}>📚 맞춤 학습 경로</h3>
                                    <ol style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 6 }}>
                                        {tutorPathItems.map((step, i) => (
                                            <li key={i} style={{ fontSize: 13, color: 'var(--workspace-text)', lineHeight: 1.6 }}>{step}</li>
                                        ))}
                                    </ol>
                                </div>
                            )}

                            {tutorFeedback.length > 0 && (
                                <div>
                                    <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--workspace-accent)', marginBottom: 8 }}>💬 코드 피드백</h3>
                                    <div style={{ display: 'grid', gap: 6 }}>
                                        {tutorFeedback.map((item, i) => (
                                            <div key={i} style={{ padding: '10px 14px', borderRadius: 'var(--workspace-radius-sm)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--workspace-border)', fontSize: 13, color: 'var(--workspace-text)' }}>
                                                {item}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {result && (
                            <div className="workspace-card" data-testid="marketplace-codegen-result">
                                <h2 className="workspace-card-title">✅ 생성 완료</h2>
                                <div className="workspace-metric-grid" style={{ marginTop: 12 }}>
                                    <div className="workspace-metric-card"><div className="workspace-metric-label">프로젝트</div><div className="workspace-metric-value" style={{ fontSize: 18 }}>{result.project_name}</div></div>
                                    <div className="workspace-metric-card"><div className="workspace-metric-label">프로필</div><div className="workspace-metric-value" style={{ fontSize: 16 }}>{result.profile}</div></div>
                                    <div className="workspace-metric-card"><div className="workspace-metric-label">파일 수</div><div className="workspace-metric-value">{result.file_count}</div></div>
                                </div>
                                {result.download_url && (
                                    <div style={{ marginTop: 14 }}>
                                        <button
                                            data-testid="marketplace-codegen-download-btn"
                                            onClick={() => handleDownload(result.download_url || '', `${result.project_name || 'project'}.zip`)}
                                            className="workspace-primary-button"
                                            style={{ padding: '12px 20px', fontSize: 14, fontWeight: 700 }}
                                        >
                                            ZIP 다운로드
                                        </button>
                                    </div>
                                )}
                                <div style={{ marginTop: 16 }}>
                                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>📂 생성된 파일</h3>
                                    <div style={{ background: 'rgba(9,14,22,0.96)', borderRadius: 'var(--workspace-radius-md)', border: '1px solid var(--workspace-border)', padding: 16, maxHeight: 300, overflow: 'auto' }}>
                                        {result.files.map((file, i) => (
                                            <div key={i} style={{ fontSize: 13, color: 'var(--workspace-muted)', lineHeight: 2, fontFamily: 'monospace' }}>
                                                📄 {file}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    <aside className="workspace-sidebar">
                        <div className="workspace-sidebar-card">
                            <h3 className="workspace-card-title">🧰 프로필</h3>
                            <div style={{ display: 'grid', gap: 6, marginTop: 10 }}>
                                {allProfiles.length === 0 && (
                                    <div style={{ fontSize: 12, color: 'var(--workspace-muted)' }}>프로필 로딩 중...</div>
                                )}
                                {allProfiles.map(p => (
                                    <button key={p.id} onClick={() => setSelectedProfile(p.id)}
                                        style={{
                                            padding: '10px 12px', textAlign: 'left',
                                            borderRadius: 'var(--workspace-radius-sm)',
                                            border: selectedProfile === p.id ? '2px solid var(--workspace-accent)' : '1px solid var(--workspace-border)',
                                            background: selectedProfile === p.id ? 'rgba(119,212,255,0.08)' : 'rgba(255,255,255,0.02)',
                                            color: 'var(--workspace-text)', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                                        }}>
                                        {p.icon} {p.id} <span style={{ fontSize: 10, color: 'var(--workspace-muted)' }}>({p.group})</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="workspace-sidebar-card">
                            <h3 className="workspace-card-title">🕘 생성 이력</h3>
                            <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
                                {historyLoading && (
                                    <div style={{ fontSize: 12, color: 'var(--workspace-muted)' }}>이력 로딩 중...</div>
                                )}
                                {!historyLoading && historyItems.length === 0 && (
                                    <div style={{ fontSize: 12, color: 'var(--workspace-muted)' }}>생성 이력이 없습니다.</div>
                                )}
                                {historyItems.map((item) => (
                                    <div
                                        key={item.generation_id}
                                        style={{
                                            border: '1px solid var(--workspace-border)',
                                            borderRadius: 'var(--workspace-radius-sm)',
                                            padding: '10px 10px 12px',
                                            background: 'rgba(255,255,255,0.02)',
                                        }}
                                    >
                                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--workspace-text)' }}>{item.project_name}</div>
                                        <div style={{ fontSize: 11, color: 'var(--workspace-muted)', marginTop: 4 }}>{item.profile} · 파일 {item.file_count}개</div>
                                        <div style={{ fontSize: 11, color: 'var(--workspace-muted)', marginTop: 4 }}>{item.task_preview}</div>
                                        <button
                                            data-testid={`marketplace-codegen-history-download-${item.generation_id}`}
                                            onClick={() => handleDownload(item.download_url, `${item.project_name || 'project'}.zip`)}
                                            style={{
                                                marginTop: 8,
                                                padding: '8px 10px',
                                                fontSize: 11,
                                                fontWeight: 700,
                                                borderRadius: 'var(--workspace-radius-sm)',
                                                border: '1px solid var(--workspace-border)',
                                                color: 'var(--workspace-text)',
                                                background: 'rgba(119,212,255,0.08)',
                                                cursor: 'pointer',
                                            }}
                                        >
                                            ZIP 다운로드
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="workspace-sidebar-card">
                            <h3 className="workspace-card-title">⚡ 실시간 코드 생성 패널</h3>
                            <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
                                <div
                                    style={{
                                        border: '1px solid var(--workspace-border)',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        padding: '8px 10px',
                                        background: 'rgba(119,212,255,0.08)',
                                        fontSize: 11,
                                        fontWeight: 700,
                                        color: 'var(--workspace-text)',
                                    }}
                                >
                                    상태: {liveStatusText}
                                </div>

                                <div style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>
                                    코드미리보기 [생성부 패널]
                                </div>

                                <pre
                                    style={{
                                        margin: 0,
                                        border: '1px solid var(--workspace-border)',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        padding: '10px 12px',
                                        background: 'rgba(8, 14, 24, 0.96)',
                                        color: 'var(--workspace-text)',
                                        fontSize: 11,
                                        lineHeight: 1.6,
                                        maxHeight: 220,
                                        overflow: 'auto',
                                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                    }}
                                >
                                    {livePreviewCode}
                                </pre>

                                <div style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>예상/생성 파일</div>
                                <div
                                    style={{
                                        border: '1px solid var(--workspace-border)',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        padding: '8px 10px',
                                        background: 'rgba(255,255,255,0.02)',
                                        display: 'grid',
                                        gap: 5,
                                    }}
                                >
                                    {previewFileNames.map((name) => (
                                        <div key={name} style={{ fontSize: 11, color: 'var(--workspace-text)' }}>
                                            {name}
                                        </div>
                                    ))}
                                </div>

                                <div style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>실시간 단계</div>
                                <div
                                    style={{
                                        border: '1px solid var(--workspace-border)',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        padding: '8px 10px',
                                        background: 'rgba(255,255,255,0.02)',
                                        display: 'grid',
                                        gap: 4,
                                    }}
                                >
                                    {liveLogItems.map((item, idx) => (
                                        <div key={`${item}-${idx}`} style={{ fontSize: 11, color: 'var(--workspace-text)' }}>
                                            • {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="workspace-sidebar-card">
                            <h3 className="workspace-card-title">🌐 통역 연동 패널</h3>
                            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                                <textarea
                                    data-testid="marketplace-interpreter-input"
                                    value={interpreterText}
                                    onChange={(e) => setInterpreterText(e.target.value)}
                                    className="workspace-admin-command-textarea"
                                    style={{ minHeight: 72 }}
                                    placeholder="번역할 문장을 입력하세요"
                                />
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                    <input
                                        data-testid="marketplace-interpreter-source-lang"
                                        value={interpreterSourceLang}
                                        onChange={(e) => setInterpreterSourceLang(e.target.value.trim())}
                                        placeholder="source (예: ko)"
                                        style={{
                                            width: '100%',
                                            padding: '10px 12px',
                                            borderRadius: 'var(--workspace-radius-sm)',
                                            border: '1px solid var(--workspace-border)',
                                            background: 'rgba(9,14,22,0.96)',
                                            color: 'var(--workspace-text)',
                                            fontSize: 12,
                                        }}
                                    />
                                    <input
                                        data-testid="marketplace-interpreter-target-lang"
                                        value={interpreterTargetLang}
                                        onChange={(e) => setInterpreterTargetLang(e.target.value.trim())}
                                        placeholder="target (예: en)"
                                        style={{
                                            width: '100%',
                                            padding: '10px 12px',
                                            borderRadius: 'var(--workspace-radius-sm)',
                                            border: '1px solid var(--workspace-border)',
                                            background: 'rgba(9,14,22,0.96)',
                                            color: 'var(--workspace-text)',
                                            fontSize: 12,
                                        }}
                                    />
                                </div>
                                <button
                                    data-testid="marketplace-interpreter-translate-btn"
                                    onClick={handleInterpreterTranslate}
                                    disabled={interpreterLoading}
                                    style={{
                                        padding: '10px 12px',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        border: '1px solid var(--workspace-border)',
                                        background: 'rgba(119,212,255,0.12)',
                                        color: 'var(--workspace-text)',
                                        fontSize: 12,
                                        fontWeight: 700,
                                        cursor: interpreterLoading ? 'not-allowed' : 'pointer',
                                        opacity: interpreterLoading ? 0.7 : 1,
                                    }}
                                >
                                    {interpreterLoading ? '통역 처리 중...' : '통역 API 호출'}
                                </button>
                                <button
                                    data-testid="marketplace-interpreter-tutor-btn"
                                    onClick={handleTutorFromInterpreter}
                                    disabled={tutorLoading || interpreterLoading}
                                    style={{
                                        padding: '10px 12px',
                                        borderRadius: 'var(--workspace-radius-sm)',
                                        border: '1px solid var(--workspace-border)',
                                        background: 'rgba(167,139,250,0.15)',
                                        color: 'var(--workspace-text)',
                                        fontSize: 12,
                                        fontWeight: 700,
                                        cursor: tutorLoading || interpreterLoading ? 'not-allowed' : 'pointer',
                                        opacity: tutorLoading || interpreterLoading ? 0.7 : 1,
                                    }}
                                >
                                    {tutorLoading ? '튜터 생성 중...' : '통역 완성본으로 학습용 튜터'}
                                </button>
                                {interpreterMode && (
                                    <div data-testid="marketplace-interpreter-mode" style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>mode: {interpreterMode}</div>
                                )}
                                {interpreterError && (
                                    <div style={{ fontSize: 12, color: 'var(--workspace-danger)' }}>⚠️ {interpreterError}</div>
                                )}
                                {interpreterResult && (
                                    <div
                                        data-testid="marketplace-interpreter-result"
                                        style={{
                                            border: '1px solid var(--workspace-border)',
                                            borderRadius: 'var(--workspace-radius-sm)',
                                            padding: '10px 12px',
                                            background: 'rgba(255,255,255,0.02)',
                                            fontSize: 12,
                                            color: 'var(--workspace-text)',
                                            whiteSpace: 'pre-wrap',
                                            lineHeight: 1.5,
                                        }}
                                    >
                                        {interpreterResult}
                                    </div>
                                )}
                                {tutorMode && (
                                    <div data-testid="marketplace-interpreter-tutor-mode" style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>tutor mode: {tutorMode}</div>
                                )}
                                {tutorError && (
                                    <div style={{ fontSize: 12, color: 'var(--workspace-danger)' }}>⚠️ {tutorError}</div>
                                )}
                                {tutorResult && (
                                    <div
                                        data-testid="marketplace-interpreter-tutor-result"
                                        style={{
                                            border: '1px solid var(--workspace-border)',
                                            borderRadius: 'var(--workspace-radius-sm)',
                                            padding: '10px 12px',
                                            background: 'rgba(167,139,250,0.09)',
                                            fontSize: 12,
                                            color: 'var(--workspace-text)',
                                            whiteSpace: 'pre-wrap',
                                            lineHeight: 1.5,
                                        }}
                                    >
                                        {tutorResult}
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="workspace-sidebar-card" data-testid="marketplace-music-panel">
                            <h3 className="workspace-card-title">🎵 음악 생성·작사·협업 패널</h3>
                            <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
                                <div style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>감정 기반 테마송</div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                                    <input
                                        value={musicEmotion}
                                        onChange={(e) => setMusicEmotion(e.target.value.trim())}
                                        placeholder="emotion"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                    <input
                                        value={musicIntensity}
                                        onChange={(e) => setMusicIntensity(e.target.value.trim())}
                                        placeholder="intensity"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                    <input
                                        value={musicTheme}
                                        onChange={(e) => setMusicTheme(e.target.value)}
                                        placeholder="theme"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                </div>
                                <button
                                    data-testid="marketplace-music-compose-emotion-btn"
                                    onClick={handleMusicCompose}
                                    disabled={musicLoading}
                                    style={{ padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(255,186,73,0.14)', color: 'var(--workspace-text)', fontSize: 12, fontWeight: 700, cursor: musicLoading ? 'not-allowed' : 'pointer', opacity: musicLoading ? 0.7 : 1 }}
                                >
                                    {musicLoading ? '음악 생성 중...' : '감정 기반 음악 생성'}
                                </button>

                                <div style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>코드 기반 작곡</div>
                                <textarea
                                    value={musicCode}
                                    onChange={(e) => setMusicCode(e.target.value)}
                                    className="workspace-admin-command-textarea"
                                    style={{ minHeight: 72 }}
                                    placeholder="작곡 패턴으로 변환할 코드"
                                />
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                                    <input
                                        value={musicCodeEmotion}
                                        onChange={(e) => setMusicCodeEmotion(e.target.value.trim())}
                                        placeholder="emotion"
                                        style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(9,14,22,0.96)', color: 'var(--workspace-text)', fontSize: 12 }}
                                    />
                                    <button
                                        data-testid="marketplace-music-compose-code-btn"
                                        onClick={handleMusicComposeFromCode}
                                        disabled={musicLoading}
                                        style={{ padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(140,210,255,0.12)', color: 'var(--workspace-text)', fontSize: 12, fontWeight: 700, cursor: musicLoading ? 'not-allowed' : 'pointer', opacity: musicLoading ? 0.7 : 1 }}
                                    >
                                        코드 작곡
                                    </button>
                                </div>

                                <button
                                    data-testid="marketplace-music-friends-demo-btn"
                                    onClick={handleMusicCollaboration}
                                    disabled={musicLoading}
                                    style={{ padding: '10px 12px', borderRadius: 'var(--workspace-radius-sm)', border: '1px solid var(--workspace-border)', background: 'rgba(124,255,194,0.12)', color: 'var(--workspace-text)', fontSize: 12, fontWeight: 700, cursor: musicLoading ? 'not-allowed' : 'pointer', opacity: musicLoading ? 0.7 : 1 }}
                                >
                                    협업 데모 연결
                                </button>

                                {musicMode && (
                                    <div data-testid="marketplace-music-mode" style={{ fontSize: 11, color: 'var(--workspace-muted)' }}>mode: {musicMode}</div>
                                )}
                                {musicError && (
                                    <div style={{ fontSize: 12, color: 'var(--workspace-danger)' }}>⚠️ {musicError}</div>
                                )}
                                {musicComposeResult && (
                                    <div data-testid="marketplace-music-compose-result" style={{ border: '1px solid var(--workspace-border)', borderRadius: 'var(--workspace-radius-sm)', padding: '10px 12px', background: 'rgba(255,255,255,0.02)', fontSize: 12, color: 'var(--workspace-text)', display: 'grid', gap: 4 }}>
                                        <div>song: {String(musicComposeResult.song_title || '-')}</div>
                                        <div>lyrics: {String(musicComposeResult.lyrics_title || '-')}</div>
                                        <div>tempo: {String(musicComposeResult.tempo || '-')}</div>
                                        <div>melody: {Array.isArray(musicComposeResult.melody_preview) ? musicComposeResult.melody_preview.join(', ') : '-'}</div>
                                    </div>
                                )}
                                {musicCodeResult && (
                                    <div data-testid="marketplace-music-code-result" style={{ border: '1px solid var(--workspace-border)', borderRadius: 'var(--workspace-radius-sm)', padding: '10px 12px', background: 'rgba(255,255,255,0.02)', fontSize: 12, color: 'var(--workspace-text)', display: 'grid', gap: 4 }}>
                                        <div>song: {String(musicCodeResult.song_title || '-')}</div>
                                        <div>composition: {String(musicCodeResult.code_composition_title || '-')}</div>
                                        <div>chords: {Array.isArray(musicCodeResult.chords) ? musicCodeResult.chords.join(' → ') : '-'}</div>
                                    </div>
                                )}
                                {musicFriendResult && (
                                    <div data-testid="marketplace-music-friends-result" style={{ border: '1px solid var(--workspace-border)', borderRadius: 'var(--workspace-radius-sm)', padding: '10px 12px', background: 'rgba(255,255,255,0.02)', fontSize: 12, color: 'var(--workspace-text)', display: 'grid', gap: 4 }}>
                                        <div>request: {String(musicFriendResult.request_id || '-')}</div>
                                        <div>collaboration: {String(musicFriendResult.collaboration_id || '-')}</div>
                                        <div>friends: {Array.isArray(musicFriendResult.friends_of_a) ? musicFriendResult.friends_of_a.join(', ') : '-'}</div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </aside>
                </div>
            </main>
            <MarketplaceRightRail activeRailId="office-tools" />
        </div>
    );
}
