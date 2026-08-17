'use client';

import { useState, useCallback, useEffect } from 'react';
import { MarketplaceLeftRail, MarketplaceRightRail } from '@/components/marketplace/marketplace-rails';

interface AdapterStatus {
    adapter_name?: string;
    available?: boolean;
    device?: string;
    reason?: string | null;
    embedding_backend?: string | null;
    adapter_mode?: string;
}

interface FaceRecognitionStatus {
    gpu_available: boolean;
    gpu_name: string | null;
    device: string;
    adapter: AdapterStatus;
    error?: string;
}

interface DetectorsStatus {
    gpu_available: boolean;
    gpu_name: string | null;
    device: string;
    detectors: Record<string, string>;
    model_source: string;
    error?: string;
}

export default function MLDetectorsPage() {
    const [faceStatus, setFaceStatus] = useState<FaceRecognitionStatus | null>(null);
    const [detectorsStatus, setDetectorsStatus] = useState<DetectorsStatus | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            setLoading(true);
            try {
                const [faceRes, detectorsRes] = await Promise.all([
                    fetch('/api/marketplace/face-recognition/status'),
                    fetch('/api/marketplace/ml-detectors/status'),
                ]);
                if (faceRes.ok) setFaceStatus(await faceRes.json());
                if (detectorsRes.ok) setDetectorsStatus(await detectorsRes.json());
            } catch { /* ignore */ }
            setLoading(false);
        })();
    }, []);

    const gpuAvailable = faceStatus?.gpu_available || detectorsStatus?.gpu_available;
    const gpuName = faceStatus?.gpu_name || detectorsStatus?.gpu_name;

    return (
        <div className="workspace-shell">
            <MarketplaceLeftRail activeRailId="market-home" />

            <main className="workspace-stage">
                <div className="workspace-topbar">
                    <div>
                        <p className="workspace-overline">ML Quality Detectors</p>
                        <h1 className="workspace-page-title">ML 검출기 & 얼굴 인식</h1>
                        <p className="workspace-page-description">
                            ArcFace 얼굴 인식, 신체 비율, 손 해부학, 시간적 깜빡임 검출기 런타임 상태를 확인합니다.
                        </p>
                    </div>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: 40, color: 'var(--workspace-muted)', fontSize: 15 }}>
                        ⏳ ML 런타임 상태 로딩 중...
                    </div>
                ) : (
                    <>
                        {/* GPU 상태 */}
                        <div className="workspace-metric-grid" style={{ marginBottom: 22 }}>
                            <div className="workspace-metric-card">
                                <div className="workspace-metric-label">GPU 상태</div>
                                <div className="workspace-metric-value" style={{
                                    color: gpuAvailable ? 'var(--workspace-success)' : 'var(--workspace-danger)',
                                    fontSize: 20,
                                }}>
                                    {gpuAvailable ? '🟢 사용 가능' : '🔴 사용 불가'}
                                </div>
                                <div className="workspace-metric-note">{gpuName || 'CPU only'}</div>
                            </div>
                            <div className="workspace-metric-card">
                                <div className="workspace-metric-label">디바이스</div>
                                <div className="workspace-metric-value" style={{ fontSize: 18 }}>
                                    {faceStatus?.device?.toUpperCase() || '-'}
                                </div>
                            </div>
                            <div className="workspace-metric-card">
                                <div className="workspace-metric-label">얼굴 인식 어댑터</div>
                                <div className="workspace-metric-value" style={{
                                    color: faceStatus?.adapter?.available ? 'var(--workspace-success)' : 'var(--workspace-warning)',
                                    fontSize: 16,
                                }}>
                                    {faceStatus?.adapter?.adapter_name || '-'}
                                </div>
                                <div className="workspace-metric-note">
                                    {faceStatus?.adapter?.available ? '✅ 활성' : `⚠️ ${faceStatus?.adapter?.reason || '비활성'}`}
                                </div>
                            </div>
                            <div className="workspace-metric-card">
                                <div className="workspace-metric-label">모델 소스</div>
                                <div className="workspace-metric-value" style={{ fontSize: 14 }}>
                                    {detectorsStatus?.model_source || '-'}
                                </div>
                            </div>
                        </div>

                        {/* ArcFace 어댑터 상세 */}
                        <div className="workspace-content-grid workspace-content-grid-with-sidebar">
                            <div className="workspace-main-content" style={{ display: 'grid', gap: 18 }}>
                                <div className="workspace-card">
                                    <h2 className="workspace-card-title">🔍 ArcFace 얼굴 인식</h2>
                                    <p className="workspace-card-copy">
                                        InsightFace ArcFace → FaceNet → Torchvision ResNet18 폴백 체인으로 얼굴 임베딩을 추출합니다.
                                    </p>
                                    <div style={{ marginTop: 14, display: 'grid', gap: 8 }}>
                                        {['adapter_name', 'adapter_mode', 'embedding_backend', 'device'].map(key => (
                                            <div key={key} style={{
                                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                padding: '10px 14px', borderRadius: 'var(--workspace-radius-sm)',
                                                border: '1px solid var(--workspace-border)',
                                            }}>
                                                <span style={{ fontSize: 13, color: 'var(--workspace-muted)' }}>{key}</span>
                                                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--workspace-text)' }}>
                                                    {String((faceStatus?.adapter as any)?.[key] ?? '-')}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="workspace-card">
                                    <h2 className="workspace-card-title">🧪 ML 검출기 목록</h2>
                                    <p className="workspace-card-copy">
                                        GPU 가속 Torchvision 사전학습 모델 기반 품질 검출기입니다.
                                    </p>
                                    <div className="workspace-board-grid" style={{ marginTop: 14 }}>
                                        {detectorsStatus?.detectors && Object.entries(detectorsStatus.detectors).map(([key, name]) => {
                                            const icons: Record<string, string> = {
                                                face_consistency: '👤', hand_anatomy: '✋',
                                                body_ratio: '🏃', temporal_flicker: '📹',
                                            };
                                            const labels: Record<string, string> = {
                                                face_consistency: '얼굴 일관성', hand_anatomy: '손 해부학',
                                                body_ratio: '신체 비율', temporal_flicker: '시간적 깜빡임',
                                            };
                                            return (
                                                <div key={key} className="workspace-board-card">
                                                    <div style={{ fontSize: 28, marginBottom: 8 }}>{icons[key] || '🔬'}</div>
                                                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{labels[key] || key}</h3>
                                                    <div style={{ fontSize: 11, color: 'var(--workspace-muted)', fontFamily: 'monospace' }}>{name}</div>
                                                    <div style={{
                                                        marginTop: 8, fontSize: 11, fontWeight: 600,
                                                        color: 'var(--workspace-success)',
                                                        padding: '4px 8px', borderRadius: 6,
                                                        background: 'rgba(116,241,166,0.1)',
                                                        display: 'inline-block',
                                                    }}>
                                                        ✅ 준비됨
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>

                            <aside className="workspace-sidebar">
                                <div className="workspace-sidebar-card">
                                    <h3 className="workspace-card-title">🔗 API 엔드포인트</h3>
                                    <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
                                        {[
                                            { path: '/face-recognition/status', label: '얼굴 인식 상태' },
                                            { path: '/face-recognition/compare', label: '얼굴 유사도 비교' },
                                            { path: '/ml-detectors/status', label: 'ML 검출기 상태' },
                                            { path: '/ml-detectors/run', label: '검출기 실행' },
                                        ].map(ep => (
                                            <a key={ep.path}
                                                href={`/api/marketplace${ep.path}`}
                                                target="_blank" rel="noopener noreferrer"
                                                style={{
                                                    display: 'block', padding: '10px 14px',
                                                    borderRadius: 'var(--workspace-radius-sm)',
                                                    border: '1px solid var(--workspace-border)',
                                                    background: 'rgba(9,14,22,0.7)',
                                                    color: 'var(--workspace-accent)',
                                                    fontSize: 12, textDecoration: 'none', fontWeight: 600,
                                                }}>
                                                📊 {ep.label}
                                            </a>
                                        ))}
                                    </div>
                                </div>
                                <div className="workspace-sidebar-card">
                                    <h3 className="workspace-card-title">ℹ️ 폴백 체인</h3>
                                    <div style={{ marginTop: 8, fontSize: 12, color: 'var(--workspace-muted)', lineHeight: 2.2 }}>
                                        1️⃣ InsightFace ArcFace (CUDA)<br />
                                        2️⃣ FaceNet InceptionResNetV1<br />
                                        3️⃣ Torchvision ResNet18 (폴백)
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </>
                )}
            </main>
            <MarketplaceRightRail activeRailId="ml-detectors" />
        </div>
    );
}
