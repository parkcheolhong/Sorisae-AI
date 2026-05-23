'use client';

import * as React from 'react';
import { MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY, type MarketplaceOrchestratorBridgePayload } from '@/lib/admin-orchestrator-bridge';
import { buildMarketplacePopupTelemetryEvent, recordMarketplacePopupTelemetry } from '@/lib/marketplace-popup-telemetry';
import { resolveApiBaseUrl } from '@/lib/api';

export type FeaturePopupState =
    | 'idle'
    | 'accepted'
    | 'preview_running'
    | 'preview_ready'
    | 'final_running'
    | 'quality_review'
    | 'completed'
    | 'completed_preview_only'
    | 'failed';

export type FeatureCatalogItem = {
    feature_id: string;
    title: string;
    summary: string;
    popup_mode: string;
    status: string;
    supports_photo_upload: boolean;
    supports_final_phase: boolean;
};

export type FeatureExperienceMeta = {
    featureId: string;
    outputKind: 'image' | 'music' | 'document' | 'spreadsheet' | 'video' | 'presentation' | 'code';
    popupKicker: string;
    launcherSummary: string;
    launcherCta: string;
    launcherBadge: string;
    launcherHighlights: string[];
    liveViewTitle: string;
    liveViewDescription: string;
    inputTitle: string;
    inputDescription: string;
    projectPlaceholder: string;
    promptPlaceholder: string;
    templateLabel: string;
    templateOptions: Array<{ value: string; label: string }>;
    finalToggleLabel: string;
    submitLabel: string;
    uploadLabel?: string;
    previewTitle: string;
    finalTitle: string;
    downloadTitle?: string;
    downloadDescription?: string;
    emptyArtifactText: string;
    quickPromptChips: string[];
    statCards: Array<{ id: string; label: string; note: string }>;
};

export type FeatureArtifact = {
    artifact_id?: string | null;
    artifact_type?: string;
    phase?: string;
    state?: string;
    title?: string;
    image_data_url?: string;
    prompt_summary?: string;
    keywords?: string[];
    composition?: {
        template_id?: string;
        photo_reference?: string;
        warnings?: string[];
    };
    sheet_schema?: {
        sheet_name?: string;
        row_goal?: number;
        columns?: Array<{
            name: string;
            type: string;
        }>;
    };
    workbook?: {
        sheet_name?: string;
        column_count?: number;
        row_count?: number;
        sample_rows?: Array<Record<string, unknown>>;
    };
    delivery_assets?: Array<{
        format?: string;
        path?: string;
        path_hint?: string;
        mime_type?: string;
        size_bytes?: number;
        exists?: boolean;
        generated_at?: string;
    }>;
    generated_at?: string;
    notes?: string[];
};

export type FeatureStreamConnection = 'idle' | 'connecting' | 'streaming' | 'completed' | 'failed';

export type FeatureLiveViewArtifact = {
    title: string;
    caption: string;
    image_data_url: string;
    source: 'upload' | 'preview' | 'final';
};

export type SpreadsheetDownloadLink = {
    format: string;
    href: string;
    fileName: string;
    sizeLabel: string;
    ready: boolean;
    completedAt: string;
    completedAtLabel: string;
};

export type SpreadsheetRunSummary = {
    stageLabel: string;
    stageDescription: string;
    sheetName: string;
    columnCount: number;
    rowCount: number;
    promptSummary: string;
};

export type FeatureProgressSnapshot = {
    percent: number;
    step: string;
    state?: FeaturePopupState;
    message: string;
    updated_at: string;
};

type FeatureQualityReview = {
    passed?: boolean;
    score?: number;
    issues?: string[];
    checks?: Record<string, boolean>;
};

type FeatureStageRun = {
    run_id: string;
    current_stage_id?: string;
    status?: string;
    final_completed?: boolean;
};

type StreamEnvelope = {
    event: string;
    payload: {
        run_id?: string;
        state?: FeaturePopupState;
        artifact?: FeatureArtifact;
        artifact_manifest?: {
            preview_artifact?: FeatureArtifact;
            final_artifact?: FeatureArtifact;
        };
        quality_review?: FeatureQualityReview;
        progress?: FeatureProgressSnapshot;
        message?: string;
    };
};

type FeaturePreset = {
    projectName: string;
    prompt: string;
    templateId: string;
    finalEnabled: boolean;
    contextTags: string[];
};

const FEATURE_EXPERIENCE_META: Record<string, FeatureExperienceMeta> = {
    'ai-document': {
        featureId: 'ai-document',
        outputKind: 'document',
        popupKicker: 'AI Document Builder',
        launcherSummary: '제안서, 보고서, 운영가이드를 위한 개요 preview와 최종 문서 패키지를 준비합니다.',
        launcherCta: '문서 초안 생성',
        launcherBadge: '문서 제작',
        launcherHighlights: ['목차 preview', '독자 맞춤 문체', '최종 문서 패키지'],
        liveViewTitle: '문서 개요 라이브 피드',
        liveViewDescription: 'preview 단계에서는 개요와 목차를, final 단계에서는 내보내기 가능한 문서 패키지를 정리합니다.',
        inputTitle: '문서 제작 입력',
        inputDescription: '문서 목적, 독자, 핵심 메시지, 원하는 문체를 입력하면 초안 UX가 좋아집니다.',
        projectPlaceholder: '예: 신규 서비스 제안서',
        promptPlaceholder: '문서 목적, 독자, 목차, 핵심 메시지, 분량, 원하는 문체를 입력하세요.',
        templateLabel: '문서 템플릿',
        templateOptions: [
            { value: 'document-outline-template', label: '제안서 개요 템플릿' },
            { value: 'report-brief-template', label: '보고서 요약 템플릿' },
            { value: 'manual-guide-template', label: '운영 가이드 템플릿' },
        ],
        finalToggleLabel: '목차 preview 뒤 최종 문서 패키지 생성',
        submitLabel: '문서 초안 생성',
        previewTitle: '문서 Outline Preview',
        finalTitle: '최종 문서 Package',
        emptyArtifactText: '문서 결과가 아직 없습니다. 목적과 독자 정보를 입력해 주세요.',
        quickPromptChips: ['제안서 목차', '운영 가이드', '임원 보고서', '친절한 문체', '핵심 요약 중심'],
        statCards: [
            { id: 'outline', label: '목차 구조', note: 'preview 개요 품질' },
            { id: 'audience', label: '독자 적합도', note: '문체/톤' },
            { id: 'delivery', label: '산출물', note: 'outline + final doc' },
        ],
    },
    'ai-sheet': {
        featureId: 'ai-sheet',
        outputKind: 'spreadsheet',
        popupKicker: 'AI Spreadsheet Builder',
        launcherSummary: '영업, 재고, 운영 시트를 schema preview와 xlsx/csv 패키지까지 한 번에 생성합니다.',
        launcherCta: '엑셀 시트 생성 시작',
        launcherBadge: '엑셀 즉시 생성',
        launcherHighlights: ['컬럼/행 구조 확인', '워크북 패키징', 'xlsx/csv 다운로드'],
        liveViewTitle: '시트 생성 라이브 피드',
        liveViewDescription: '시트 목적에 맞는 schema를 먼저 확인하고, final 단계에서 workbook 패키지와 다운로드 자산을 확정합니다.',
        inputTitle: '엑셀 시트 입력',
        inputDescription: '시트 목적, 컬럼명, 행 수, 숫자/날짜 규칙을 적으면 실사용 가능한 워크북 구조를 바로 확인할 수 있습니다.',
        projectPlaceholder: '예: 영업 리드 관리 시트',
        promptPlaceholder: '시트 목적, 필수 컬럼, 샘플 행 수, 숫자/날짜 형식을 입력하세요.',
        templateLabel: '시트 템플릿',
        templateOptions: [
            { value: 'sheet-schema-template', label: '기본 시트 스키마 템플릿' },
            { value: 'sales-pipeline-template', label: '영업 파이프라인 템플릿' },
            { value: 'inventory-control-template', label: '재고 관리 템플릿' },
        ],
        finalToggleLabel: 'schema preview 뒤 workbook 패키지까지 생성',
        submitLabel: '시트 생성 시작',
        previewTitle: 'Sheet Schema Preview',
        finalTitle: 'Workbook Package',
        downloadTitle: 'Spreadsheet Downloads',
        downloadDescription: 'final phase 가 완료되면 xlsx/csv 결과물을 바로 내려받을 수 있습니다.',
        emptyArtifactText: '시트 결과가 아직 없습니다. 컬럼과 목적을 입력하고 시작하세요.',
        quickPromptChips: ['영업 리드 관리', '재고 관리표', '운영 일정표', '숫자/날짜 혼합', '24행 샘플 데이터'],
        statCards: [
            { id: 'columns', label: '컬럼 설계', note: '구조/타입 미리보기' },
            { id: 'rows', label: '샘플 행', note: '실제 데이터 형태' },
            { id: 'delivery', label: '다운로드', note: 'xlsx/csv 패키지' },
        ],
    },
    'ai-powerpoint': {
        featureId: 'ai-powerpoint',
        outputKind: 'presentation',
        popupKicker: 'AI PowerPoint Builder',
        launcherSummary: '발표 목적에 맞는 슬라이드 구성 preview와 최종 pptx 패키지를 자동 생성합니다.',
        launcherCta: '파워포인트 생성 시작',
        launcherBadge: 'PPT 자동 제작',
        launcherHighlights: ['슬라이드 개요', '핵심 메시지 정리', 'pptx 다운로드'],
        liveViewTitle: '파워포인트 구성 라이브 피드',
        liveViewDescription: 'preview 단계에서 슬라이드 목차와 bullet 구성을 확인하고 final 단계에서 pptx 패키지를 확정합니다.',
        inputTitle: '파워포인트 제작 입력',
        inputDescription: '발표 목적, 청중, 핵심 메시지, 분량을 입력하면 슬라이드 구조와 핵심 문장을 자동 정리합니다.',
        projectPlaceholder: '예: 분기 실적 발표 자료',
        promptPlaceholder: '발표 목적, 청중, 핵심 메시지, 장표 수, 원하는 톤을 입력하세요.',
        templateLabel: 'PPT 템플릿',
        templateOptions: [
            { value: 'pitch-deck-template', label: '피치덱 템플릿' },
            { value: 'business-report-template', label: '사업 보고 템플릿' },
            { value: 'product-launch-template', label: '제품 런칭 템플릿' },
        ],
        finalToggleLabel: '슬라이드 구성 preview 뒤 최종 pptx 패키지 생성',
        submitLabel: '파워포인트 생성',
        previewTitle: 'Presentation Outline Preview',
        finalTitle: '최종 PowerPoint Package',
        downloadTitle: 'PowerPoint Downloads',
        downloadDescription: 'final phase 가 완료되면 pptx 결과물을 바로 내려받을 수 있습니다.',
        emptyArtifactText: '파워포인트 결과가 아직 없습니다. 발표 목적을 입력하고 시작하세요.',
        quickPromptChips: ['분기 실적 보고', '제품 런칭 발표', '투자자 피치덱', '임원 회의 자료', '핵심 KPI 요약'],
        statCards: [
            { id: 'outline', label: '슬라이드 구성', note: '목차/흐름 점검' },
            { id: 'message', label: '핵심 메시지', note: '문장/포인트 요약' },
            { id: 'delivery', label: '산출물', note: 'pptx 패키지' },
        ],
    },
    'ai-web-design': {
        featureId: 'ai-web-design',
        outputKind: 'code',
        popupKicker: 'AI Web App Designer',
        launcherSummary: 'React/Next.js 웹 앱을 디자인부터 컴포넌트 코드까지 풀 자동 생성합니다.',
        launcherCta: '웹 앱 생성 시작',
        launcherBadge: '웹 앱 디자인 자동화',
        launcherHighlights: ['컴포넌트 설계', 'Next.js 스캐폴드', '디자인 시스템 반영'],
        liveViewTitle: '웹 앱 생성 라이브 피드',
        liveViewDescription: 'UI/UX 설계 preview 단계에서 컴포넌트 구조를 확인하고, final 단계에서 완전한 Next.js 코드 패키지를 확정합니다.',
        inputTitle: '웹 앱 제작 입력',
        inputDescription: '앱 목적, 핵심 페이지, 컴포넌트 요구사항, 디자인 스타일을 입력하면 실사용 가능한 코드 구조를 자동으로 생성합니다.',
        projectPlaceholder: '예: SaaS 대시보드 앱',
        promptPlaceholder: '앱 목적, 핵심 페이지, 필요한 컴포넌트, 디자인 가이드, 상태 관리 방식을 입력하세요.',
        templateLabel: '웹 앱 템플릿',
        templateOptions: [
            { value: 'nextjs-dashboard-template', label: 'Next.js 대시보드 템플릿' },
            { value: 'landing-page-template', label: '랜딩 페이지 템플릿' },
            { value: 'saas-app-template', label: 'SaaS 앱 템플릿' },
        ],
        finalToggleLabel: '설계 preview 뒤 최종 코드 패키지 생성',
        submitLabel: '웹 앱 생성 시작',
        previewTitle: 'UI/UX 구조 Preview',
        finalTitle: '최종 코드 Package',
        downloadTitle: '코드 패키지 다운로드',
        downloadDescription: 'final phase 가 완료되면 Next.js 프로젝트 ZIP 패키지를 바로 내려받을 수 있습니다.',
        emptyArtifactText: '웹 앱 결과가 아직 없습니다. 앱 목적과 페이지 구성을 입력하고 시작하세요.',
        quickPromptChips: ['SaaS 대시보드', '랜딩 페이지', '관리자 패널', 'Tailwind 스타일', 'TypeScript 기반'],
        statCards: [
            { id: 'pages', label: '페이지 구성', note: '라우트/컴포넌트 설계' },
            { id: 'components', label: '컴포넌트', note: 'UI 구성 요소' },
            { id: 'delivery', label: '산출물', note: 'Next.js 코드 패키지' },
        ],
    },
'ai-document-mobile': {
    featureId: 'ai-document-mobile',
        outputKind: 'document',
            popupKicker: 'AI Document Builder (모바일 앱)',
                launcherSummary: '📱 모바일 앱으로 설치해 이동 중에도 제안서·보고서·운영가이드를 빠르게 초안 작성합니다.',
                    launcherCta: '모바일 문서 앱 시작',
                        launcherBadge: '📱 모바일 문서 제작',
                            launcherHighlights: ['iOS/Android 앱', '목차 preview', '최종 문서 패키지'],
                                liveViewTitle: '문서 개요 라이브 피드 (모바일)',
                                    liveViewDescription: '모바일 환경에서 preview 단계에서는 개요와 목차를, final 단계에서는 내보내기 가능한 문서 패키지를 정리합니다.',
                                        inputTitle: '문서 제작 입력',
                                            inputDescription: '문서 목적, 독자, 핵심 메시지, 원하는 문체를 입력하면 초안 UX가 좋아집니다.',
                                                projectPlaceholder: '예: 신규 서비스 제안서',
                                                    promptPlaceholder: '문서 목적, 독자, 목차, 핵심 메시지, 분량, 원하는 문체를 입력하세요.',
                                                        templateLabel: '문서 템플릿',
                                                            templateOptions: [
                                                                { value: 'document-outline-template', label: '제안서 개요 템플릿' },
                                                                { value: 'report-brief-template', label: '보고서 요약 템플릿' },
                                                                { value: 'manual-guide-template', label: '운영 가이드 템플릿' },
                                                            ],
                                                                finalToggleLabel: '목차 preview 뒤 최종 문서 패키지 생성',
                                                                    submitLabel: '문서 초안 생성',
                                                                        previewTitle: '문서 Outline Preview',
                                                                            finalTitle: '최종 문서 Package',
                                                                                emptyArtifactText: '문서 결과가 아직 없습니다. 목적과 독자 정보를 입력해 주세요.',
                                                                                    quickPromptChips: ['제안서 목차', '운영 가이드', '임원 보고서', '친절한 문체', '핵심 요약 중심'],
                                                                                        statCards: [
                                                                                            { id: 'outline', label: '목차 구조', note: 'preview 개요 품질' },
                                                                                            { id: 'audience', label: '독자 적합도', note: '문체/톤' },
                                                                                            { id: 'delivery', label: '산출물', note: 'outline + final doc' },
                                                                                        ],
    },
'ai-document-pc': {
    featureId: 'ai-document-pc',
        outputKind: 'document',
            popupKicker: 'AI Document Builder (로컬 PC)',
                launcherSummary: '💻 로컬 PC에서 직접 실행해 대용량 제안서·보고서·운영가이드를 빠르게 생성합니다.',
                    launcherCta: 'PC 문서 앱 시작',
                        launcherBadge: '💻 PC 로컬 문서 제작',
                            launcherHighlights: ['로컬 처리', '목차 preview', '최종 문서 패키지'],
                                liveViewTitle: '문서 개요 라이브 피드 (PC)',
                                    liveViewDescription: '로컬 PC에서 preview 단계에서는 개요와 목차를, final 단계에서는 내보내기 가능한 문서 패키지를 정리합니다.',
                                        inputTitle: '문서 제작 입력',
                                            inputDescription: '문서 목적, 독자, 핵심 메시지, 원하는 문체를 입력하면 초안 UX가 좋아집니다.',
                                                projectPlaceholder: '예: 신규 서비스 제안서',
                                                    promptPlaceholder: '문서 목적, 독자, 목차, 핵심 메시지, 분량, 원하는 문체를 입력하세요.',
                                                        templateLabel: '문서 템플릿',
                                                            templateOptions: [
                                                                { value: 'document-outline-template', label: '제안서 개요 템플릿' },
                                                                { value: 'report-brief-template', label: '보고서 요약 템플릿' },
                                                                { value: 'manual-guide-template', label: '운영 가이드 템플릿' },
                                                            ],
                                                                finalToggleLabel: '목차 preview 뒤 최종 문서 패키지 생성',
                                                                    submitLabel: '문서 초안 생성',
                                                                        previewTitle: '문서 Outline Preview',
                                                                            finalTitle: '최종 문서 Package',
                                                                                emptyArtifactText: '문서 결과가 아직 없습니다. 목적과 독자 정보를 입력해 주세요.',
                                                                                    quickPromptChips: ['제안서 목차', '운영 가이드', '임원 보고서', '친절한 문체', '핵심 요약 중심'],
                                                                                        statCards: [
                                                                                            { id: 'outline', label: '목차 구조', note: 'preview 개요 품질' },
                                                                                            { id: 'audience', label: '독자 적합도', note: '문체/톤' },
                                                                                            { id: 'delivery', label: '산출물', note: 'outline + final doc' },
                                                                                        ],
    },
'ai-sheet-mobile': {
    featureId: 'ai-sheet-mobile',
        outputKind: 'spreadsheet',
            popupKicker: 'AI Spreadsheet Builder (모바일 앱)',
                launcherSummary: '📱 모바일 앱으로 설치해 이동 중에도 영업·재고·운영 시트를 즉시 생성합니다.',
                    launcherCta: '모바일 시트 앱 시작',
                        launcherBadge: '📱 모바일 엑셀 생성',
                            launcherHighlights: ['iOS/Android 앱', '컬럼/행 구조 확인', 'xlsx/csv 다운로드'],
                                liveViewTitle: '시트 생성 라이브 피드 (모바일)',
                                    liveViewDescription: '모바일 환경에서 시트 목적에 맞는 schema를 먼저 확인하고, final 단계에서 workbook 패키지와 다운로드 자산을 확정합니다.',
                                        inputTitle: '엑셀 시트 입력',
                                            inputDescription: '시트 목적, 컬럼명, 행 수, 숫자/날짜 규칙을 적으면 실사용 가능한 워크북 구조를 바로 확인할 수 있습니다.',
                                                projectPlaceholder: '예: 영업 리드 관리 시트',
                                                    promptPlaceholder: '시트 목적, 필수 컬럼, 샘플 행 수, 숫자/날짜 형식을 입력하세요.',
                                                        templateLabel: '시트 템플릿',
                                                            templateOptions: [
                                                                { value: 'sheet-schema-template', label: '기본 시트 스키마 템플릿' },
                                                                { value: 'sales-pipeline-template', label: '영업 파이프라인 템플릿' },
                                                                { value: 'inventory-control-template', label: '재고 관리 템플릿' },
                                                            ],
                                                                finalToggleLabel: 'schema preview 뒤 workbook 패키지까지 생성',
                                                                    submitLabel: '시트 생성 시작',
                                                                        previewTitle: 'Sheet Schema Preview',
                                                                            finalTitle: 'Workbook Package',
                                                                                downloadTitle: 'Spreadsheet Downloads',
                                                                                    downloadDescription: 'final phase 가 완료되면 xlsx/csv 결과물을 바로 내려받을 수 있습니다.',
                                                                                        emptyArtifactText: '시트 결과가 아직 없습니다. 컬럼과 목적을 입력하고 시작하세요.',
                                                                                            quickPromptChips: ['영업 리드 관리', '재고 관리표', '운영 일정표', '숫자/날짜 혼합', '24행 샘플 데이터'],
                                                                                                statCards: [
                                                                                                    { id: 'columns', label: '컬럼 설계', note: '구조/타입 미리보기' },
                                                                                                    { id: 'rows', label: '샘플 행', note: '실제 데이터 형태' },
                                                                                                    { id: 'delivery', label: '다운로드', note: 'xlsx/csv 패키지' },
                                                                                                ],
    },
'ai-sheet-pc': {
    featureId: 'ai-sheet-pc',
        outputKind: 'spreadsheet',
            popupKicker: 'AI Spreadsheet Builder (로컬 PC)',
                launcherSummary: '💻 로컬 PC에서 직접 실행해 대용량 영업·재고·운영 시트를 빠르게 생성합니다.',
                    launcherCta: 'PC 시트 앱 시작',
                        launcherBadge: '💻 PC 로컬 엑셀 생성',
                            launcherHighlights: ['로컬 처리', '컬럼/행 구조 확인', 'xlsx/csv 다운로드'],
                                liveViewTitle: '시트 생성 라이브 피드 (PC)',
                                    liveViewDescription: '로컬 PC에서 시트 목적에 맞는 schema를 먼저 확인하고, final 단계에서 workbook 패키지와 다운로드 자산을 확정합니다.',
                                        inputTitle: '엑셀 시트 입력',
                                            inputDescription: '시트 목적, 컬럼명, 행 수, 숫자/날짜 규칙을 적으면 실사용 가능한 워크북 구조를 바로 확인할 수 있습니다.',
                                                projectPlaceholder: '예: 영업 리드 관리 시트',
                                                    promptPlaceholder: '시트 목적, 필수 컬럼, 샘플 행 수, 숫자/날짜 형식을 입력하세요.',
                                                        templateLabel: '시트 템플릿',
                                                            templateOptions: [
                                                                { value: 'sheet-schema-template', label: '기본 시트 스키마 템플릿' },
                                                                { value: 'sales-pipeline-template', label: '영업 파이프라인 템플릿' },
                                                                { value: 'inventory-control-template', label: '재고 관리 템플릿' },
                                                            ],
                                                                finalToggleLabel: 'schema preview 뒤 workbook 패키지까지 생성',
                                                                    submitLabel: '시트 생성 시작',
                                                                        previewTitle: 'Sheet Schema Preview',
                                                                            finalTitle: 'Workbook Package',
                                                                                downloadTitle: 'Spreadsheet Downloads',
                                                                                    downloadDescription: 'final phase 가 완료되면 xlsx/csv 결과물을 바로 내려받을 수 있습니다.',
                                                                                        emptyArtifactText: '시트 결과가 아직 없습니다. 컬럼과 목적을 입력하고 시작하세요.',
                                                                                            quickPromptChips: ['영업 리드 관리', '재고 관리표', '운영 일정표', '숫자/날짜 혼합', '24행 샘플 데이터'],
                                                                                                statCards: [
                                                                                                    { id: 'columns', label: '컬럼 설계', note: '구조/타입 미리보기' },
                                                                                                    { id: 'rows', label: '샘플 행', note: '실제 데이터 형태' },
                                                                                                    { id: 'delivery', label: '다운로드', note: 'xlsx/csv 패키지' },
                                                                                                ],
    },
'ai-powerpoint-mobile': {
    featureId: 'ai-powerpoint-mobile',
        outputKind: 'presentation',
            popupKicker: 'AI PowerPoint Builder (모바일 앱)',
                launcherSummary: '📱 모바일 앱으로 설치해 이동 중에도 발표 자료·피치덱을 즉시 생성합니다.',
                    launcherCta: '모바일 PPT 앱 시작',
                        launcherBadge: '📱 모바일 PPT 제작',
                            launcherHighlights: ['iOS/Android 앱', '슬라이드 개요', 'pptx 다운로드'],
                                liveViewTitle: '파워포인트 구성 라이브 피드 (모바일)',
                                    liveViewDescription: '모바일 환경에서 preview 단계에서 슬라이드 목차와 bullet 구성을 확인하고 final 단계에서 pptx 패키지를 확정합니다.',
                                        inputTitle: '파워포인트 제작 입력',
                                            inputDescription: '발표 목적, 청중, 핵심 메시지, 분량을 입력하면 슬라이드 구조와 핵심 문장을 자동 정리합니다.',
                                                projectPlaceholder: '예: 분기 실적 발표 자료',
                                                    promptPlaceholder: '발표 목적, 청중, 핵심 메시지, 장표 수, 원하는 톤을 입력하세요.',
                                                        templateLabel: 'PPT 템플릿',
                                                            templateOptions: [
                                                                { value: 'pitch-deck-template', label: '피치덱 템플릿' },
                                                                { value: 'business-report-template', label: '사업 보고 템플릿' },
                                                                { value: 'product-launch-template', label: '제품 런칭 템플릿' },
                                                            ],
                                                                finalToggleLabel: '슬라이드 구성 preview 뒤 최종 pptx 패키지 생성',
                                                                    submitLabel: '파워포인트 생성',
                                                                        previewTitle: 'Presentation Outline Preview',
                                                                            finalTitle: '최종 PowerPoint Package',
                                                                                downloadTitle: 'PowerPoint Downloads',
                                                                                    downloadDescription: 'final phase 가 완료되면 pptx 결과물을 바로 내려받을 수 있습니다.',
                                                                                        emptyArtifactText: '파워포인트 결과가 아직 없습니다. 발표 목적을 입력하고 시작하세요.',
                                                                                            quickPromptChips: ['분기 실적 보고', '제품 런칭 발표', '투자자 피치덱', '임원 회의 자료', '핵심 KPI 요약'],
                                                                                                statCards: [
                                                                                                    { id: 'outline', label: '슬라이드 구성', note: '목차/흐름 점검' },
                                                                                                    { id: 'message', label: '핵심 메시지', note: '문장/포인트 요약' },
                                                                                                    { id: 'delivery', label: '산출물', note: 'pptx 패키지' },
                                                                                                ],
    },
'ai-powerpoint-pc': {
    featureId: 'ai-powerpoint-pc',
        outputKind: 'presentation',
            popupKicker: 'AI PowerPoint Builder (로컬 PC)',
                launcherSummary: '💻 로컬 PC에서 직접 실행해 대용량 발표 자료·피치덱을 빠르게 생성합니다.',
                    launcherCta: 'PC PPT 앱 시작',
                        launcherBadge: '💻 PC 로컬 PPT 제작',
                            launcherHighlights: ['로컬 처리', '슬라이드 개요', 'pptx 다운로드'],
                                liveViewTitle: '파워포인트 구성 라이브 피드 (PC)',
                                    liveViewDescription: '로컬 PC에서 preview 단계에서 슬라이드 목차와 bullet 구성을 확인하고 final 단계에서 pptx 패키지를 확정합니다.',
                                        inputTitle: '파워포인트 제작 입력',
                                            inputDescription: '발표 목적, 청중, 핵심 메시지, 분량을 입력하면 슬라이드 구조와 핵심 문장을 자동 정리합니다.',
                                                projectPlaceholder: '예: 분기 실적 발표 자료',
                                                    promptPlaceholder: '발표 목적, 청중, 핵심 메시지, 장표 수, 원하는 톤을 입력하세요.',
                                                        templateLabel: 'PPT 템플릿',
                                                            templateOptions: [
                                                                { value: 'pitch-deck-template', label: '피치덱 템플릿' },
                                                                { value: 'business-report-template', label: '사업 보고 템플릿' },
                                                                { value: 'product-launch-template', label: '제품 런칭 템플릿' },
                                                            ],
                                                                finalToggleLabel: '슬라이드 구성 preview 뒤 최종 pptx 패키지 생성',
                                                                    submitLabel: '파워포인트 생성',
                                                                        previewTitle: 'Presentation Outline Preview',
                                                                            finalTitle: '최종 PowerPoint Package',
                                                                                downloadTitle: 'PowerPoint Downloads',
                                                                                    downloadDescription: 'final phase 가 완료되면 pptx 결과물을 바로 내려받을 수 있습니다.',
                                                                                        emptyArtifactText: '파워포인트 결과가 아직 없습니다. 발표 목적을 입력하고 시작하세요.',
                                                                                            quickPromptChips: ['분기 실적 보고', '제품 런칭 발표', '투자자 피치덱', '임원 회의 자료', '핵심 KPI 요약'],
                                                                                                statCards: [
                                                                                                    { id: 'outline', label: '슬라이드 구성', note: '목차/흐름 점검' },
                                                                                                    { id: 'message', label: '핵심 메시지', note: '문장/포인트 요약' },
                                                                                                    { id: 'delivery', label: '산출물', note: 'pptx 패키지' },
                                                                                                ],
    },
'ai-web-design-mobile': {
    featureId: 'ai-web-design-mobile',
        outputKind: 'code',
            popupKicker: 'AI Web App Designer (모바일 앱)',
                launcherSummary: '📱 모바일 앱으로 설치해 React/Next.js 웹 앱 설계 및 코드를 어디서나 생성합니다.',
                    launcherCta: '모바일 웹 디자인 앱 시작',
                        launcherBadge: '📱 모바일 웹 앱 생성',
                            launcherHighlights: ['iOS/Android 앱', '컴포넌트 설계', 'Next.js 코드 패키지'],
                                liveViewTitle: '웹 앱 생성 라이브 피드 (모바일)',
                                    liveViewDescription: '모바일 환경에서 UI/UX 설계 preview 단계에서 컴포넌트 구조를 확인하고, final 단계에서 완전한 Next.js 코드 패키지를 확정합니다.',
                                        inputTitle: '웹 앱 제작 입력',
                                            inputDescription: '앱 목적, 핵심 페이지, 컴포넌트 요구사항, 디자인 스타일을 입력하면 실사용 가능한 코드 구조를 자동으로 생성합니다.',
                                                projectPlaceholder: '예: SaaS 대시보드 앱',
                                                    promptPlaceholder: '앱 목적, 핵심 페이지, 필요한 컴포넌트, 디자인 가이드, 상태 관리 방식을 입력하세요.',
                                                        templateLabel: '웹 앱 템플릿',
                                                            templateOptions: [
                                                                { value: 'nextjs-dashboard-template', label: 'Next.js 대시보드 템플릿' },
                                                                { value: 'landing-page-template', label: '랜딩 페이지 템플릿' },
                                                                { value: 'saas-app-template', label: 'SaaS 앱 템플릿' },
                                                            ],
                                                                finalToggleLabel: '설계 preview 뒤 최종 코드 패키지 생성',
                                                                    submitLabel: '웹 앱 생성 시작',
                                                                        previewTitle: 'UI/UX 구조 Preview',
                                                                            finalTitle: '최종 코드 Package',
                                                                                downloadTitle: '코드 패키지 다운로드',
                                                                                    downloadDescription: 'final phase 가 완료되면 Next.js 프로젝트 ZIP 패키지를 바로 내려받을 수 있습니다.',
                                                                                        emptyArtifactText: '웹 앱 결과가 아직 없습니다. 앱 목적과 페이지 구성을 입력하고 시작하세요.',
                                                                                            quickPromptChips: ['SaaS 대시보드', '랜딩 페이지', '관리자 패널', 'Tailwind 스타일', 'TypeScript 기반'],
                                                                                                statCards: [
                                                                                                    { id: 'pages', label: '페이지 구성', note: '라우트/컴포넌트 설계' },
                                                                                                    { id: 'components', label: '컴포넌트', note: 'UI 구성 요소' },
                                                                                                    { id: 'delivery', label: '산출물', note: 'Next.js 코드 패키지' },
                                                                                                ],
    },
'ai-web-design-pc': {
    featureId: 'ai-web-design-pc',
        outputKind: 'code',
            popupKicker: 'AI Web App Designer (로컬 PC)',
                launcherSummary: '💻 로컬 PC에서 직접 실행해 React/Next.js 웹 앱을 풀 자동으로 생성하고 바로 실행합니다.',
                    launcherCta: 'PC 웹 디자인 앱 시작',
                        launcherBadge: '💻 PC 로컬 웹 앱 생성',
                            launcherHighlights: ['로컬 빌드 & 실행', '컴포넌트 설계', 'Next.js 코드 패키지'],
                                liveViewTitle: '웹 앱 생성 라이브 피드 (PC)',
                                    liveViewDescription: '로컬 PC에서 UI/UX 설계 preview 단계에서 컴포넌트 구조를 확인하고, final 단계에서 완전한 Next.js 코드 패키지를 확정합니다.',
                                        inputTitle: '웹 앱 제작 입력',
                                            inputDescription: '앱 목적, 핵심 페이지, 컴포넌트 요구사항, 디자인 스타일을 입력하면 실사용 가능한 코드 구조를 자동으로 생성합니다.',
                                                projectPlaceholder: '예: SaaS 대시보드 앱',
                                                    promptPlaceholder: '앱 목적, 핵심 페이지, 필요한 컴포넌트, 디자인 가이드, 상태 관리 방식을 입력하세요.',
                                                        templateLabel: '웹 앱 템플릿',
                                                            templateOptions: [
                                                                { value: 'nextjs-dashboard-template', label: 'Next.js 대시보드 템플릿' },
                                                                { value: 'landing-page-template', label: '랜딩 페이지 템플릿' },
                                                                { value: 'saas-app-template', label: 'SaaS 앱 템플릿' },
                                                            ],
                                                                finalToggleLabel: '설계 preview 뒤 최종 코드 패키지 생성',
                                                                    submitLabel: '웹 앱 생성 시작',
                                                                        previewTitle: 'UI/UX 구조 Preview',
                                                                            finalTitle: '최종 코드 Package',
                                                                                downloadTitle: '코드 패키지 다운로드',
                                                                                    downloadDescription: 'final phase 가 완료되면 Next.js 프로젝트 ZIP 패키지를 바로 내려받을 수 있습니다.',
                                                                                        emptyArtifactText: '웹 앱 결과가 아직 없습니다. 앱 목적과 페이지 구성을 입력하고 시작하세요.',
                                                                                            quickPromptChips: ['SaaS 대시보드', '랜딩 페이지', '관리자 패널', 'Tailwind 스타일', 'TypeScript 기반'],
                                                                                                statCards: [
                                                                                                    { id: 'pages', label: '페이지 구성', note: '라우트/컴포넌트 설계' },
                                                                                                    { id: 'components', label: '컴포넌트', note: 'UI 구성 요소' },
                                                                                                    { id: 'delivery', label: '산출물', note: 'Next.js 코드 패키지' },
                                                                                                ],
    },
};

function buildDefaultCatalogItem(featureId: string): FeatureCatalogItem {
    const preset = FEATURE_PRESETS[featureId] || FEATURE_PRESETS['ai-sheet'];
    const meta = FEATURE_EXPERIENCE_META[featureId] || FEATURE_EXPERIENCE_META['ai-sheet'];
    return {
        feature_id: featureId,
        title: meta.popupKicker.replace('AI ', 'AI '),
        summary: meta.launcherSummary,
        popup_mode: preset.contextTags[1] || meta.outputKind,
        status: 'enabled',
        supports_photo_upload: featureId === 'ai-image',
        supports_final_phase: true,
    };
}

function mergeFeatureCatalog(payload: unknown): FeatureCatalogItem[] {
    const incoming = Array.isArray(payload) ? (payload as FeatureCatalogItem[]) : [];
    const merged = new Map<string, FeatureCatalogItem>();

    // Only expose features that backend explicitly provides.
    // If backend payload is temporarily empty, fall back to canonical runtime 6.
    const fallbackFeatureIds = ['ai-sheet', 'ai-document', 'ai-powerpoint'];
    const sourceFeatureIds = incoming.length > 0
        ? incoming.map((item) => String(item?.feature_id || '').trim()).filter(Boolean)
        : fallbackFeatureIds;

    sourceFeatureIds.forEach((featureId) => {
        merged.set(featureId, buildDefaultCatalogItem(featureId));
    });

    incoming.forEach((item) => {
        if (!item?.feature_id) {
            return;
        }
        const base = merged.get(item.feature_id) || buildDefaultCatalogItem(item.feature_id);
        merged.set(item.feature_id, {
            ...base,
            ...item,
            summary: item.summary || base.summary,
        });
    });
    return Array.from(merged.values());
}

const FEATURE_PRESETS: Record<string, FeaturePreset> = {
    'ai-sheet': {
        projectName: 'marketplace-sheet-run',
        prompt: '영업 리드 관리용 엑셀 시트를 만들어주세요. 컬럼은 고객사명, 담당자, 예상 매출, 미팅일을 포함하고 24행 샘플 데이터를 채워주세요.',
        templateId: 'sheet-schema-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'spreadsheet-builder'],
    },
    'ai-document': {
        projectName: 'marketplace-document-run',
        prompt: '신규 서비스 제안서를 위한 목차 preview 와 최종 문서 패키지를 만들어주세요.',
        templateId: 'document-outline-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'document-builder'],
    },
    'ai-powerpoint': {
        projectName: 'marketplace-powerpoint-run',
        prompt: '분기 실적 발표를 위한 파워포인트를 만들어주세요. 핵심 KPI, 리스크, 다음 액션 슬라이드를 포함해주세요.',
        templateId: 'pitch-deck-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'powerpoint-builder'],
    },
    'ai-web-design': {
        projectName: 'marketplace-web-design-run',
        prompt: 'SaaS 대시보드 웹 앱을 만들어주세요. 홈, 분석, 설정 페이지를 포함하고 Tailwind CSS와 TypeScript를 사용해주세요.',
        templateId: 'nextjs-dashboard-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'web-app-designer'],
    },
    'ai-document-mobile': {
        projectName: 'marketplace-document-mobile-run',
        prompt: '신규 서비스 제안서를 위한 목차 preview 와 최종 문서 패키지를 만들어주세요.',
        templateId: 'document-outline-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'document-builder', 'platform:mobile'],
    },
    'ai-document-pc': {
        projectName: 'marketplace-document-pc-run',
        prompt: '신규 서비스 제안서를 위한 목차 preview 와 최종 문서 패키지를 만들어주세요.',
        templateId: 'document-outline-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'document-builder', 'platform:pc'],
    },
    'ai-sheet-mobile': {
        projectName: 'marketplace-sheet-mobile-run',
        prompt: '영업 리드 관리용 엑셀 시트를 만들어주세요. 컬럼은 고객사명, 담당자, 예상 매출, 미팅일을 포함하고 24행 샘플 데이터를 채워주세요.',
        templateId: 'sheet-schema-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'spreadsheet-builder', 'platform:mobile'],
    },
    'ai-sheet-pc': {
        projectName: 'marketplace-sheet-pc-run',
        prompt: '영업 리드 관리용 엑셀 시트를 만들어주세요. 컬럼은 고객사명, 담당자, 예상 매출, 미팅일을 포함하고 24행 샘플 데이터를 채워주세요.',
        templateId: 'sheet-schema-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'spreadsheet-builder', 'platform:pc'],
    },
    'ai-powerpoint-mobile': {
        projectName: 'marketplace-powerpoint-mobile-run',
        prompt: '분기 실적 발표를 위한 파워포인트를 만들어주세요. 핵심 KPI, 리스크, 다음 액션 슬라이드를 포함해주세요.',
        templateId: 'pitch-deck-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'powerpoint-builder', 'platform:mobile'],
    },
    'ai-powerpoint-pc': {
        projectName: 'marketplace-powerpoint-pc-run',
        prompt: '분기 실적 발표를 위한 파워포인트를 만들어주세요. 핵심 KPI, 리스크, 다음 액션 슬라이드를 포함해주세요.',
        templateId: 'pitch-deck-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'powerpoint-builder', 'platform:pc'],
    },
    'ai-web-design-mobile': {
        projectName: 'marketplace-web-design-mobile-run',
        prompt: 'SaaS 대시보드 웹 앱을 만들어주세요. 홈, 분석, 설정 페이지를 포함하고 Tailwind CSS와 TypeScript를 사용해주세요.',
        templateId: 'nextjs-dashboard-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'web-app-designer', 'platform:mobile'],
    },
    'ai-web-design-pc': {
        projectName: 'marketplace-web-design-pc-run',
        prompt: 'SaaS 대시보드 웹 앱을 만들어주세요. 홈, 분석, 설정 페이지를 포함하고 Tailwind CSS와 TypeScript를 사용해주세요.',
        templateId: 'nextjs-dashboard-template',
        finalEnabled: true,
        contextTags: ['marketplace-popup', 'web-app-designer', 'platform:pc'],
    },
};

function getFeaturePreset(featureId: string): FeaturePreset {
    return FEATURE_PRESETS[featureId] || FEATURE_PRESETS['ai-sheet'];
}

export function getFeatureExperienceMeta(featureId: string): FeatureExperienceMeta {
    return FEATURE_EXPERIENCE_META[featureId] || FEATURE_EXPERIENCE_META['ai-sheet'];
}

function formatFileSizeLabel(size?: number): string {
    const safe = Number(size || 0);
    if (!Number.isFinite(safe) || safe <= 0) {
        return '0 B';
    }
    if (safe >= 1024 * 1024) {
        return `${(safe / (1024 * 1024)).toFixed(1)} MB`;
    }
    if (safe >= 1024) {
        return `${(safe / 1024).toFixed(1)} KB`;
    }
    return `${Math.round(safe)} B`;
}

function buildBridgePrompt(bridge: MarketplaceOrchestratorBridgePayload): {
    featureId: string;
    projectName: string;
    prompt: string;
} {
    if (bridge.source === 'admin-dashboard') {
        return {
            featureId: 'ai-document',
            projectName: bridge.title || 'admin-dashboard-document-request',
            prompt: [bridge.title, bridge.imagePrompt, bridge.backgroundPrompt, bridge.captionText, bridge.scenarioScript].filter(Boolean).join('\n'),
        };
    }
    return {
        featureId: 'ai-document',
        projectName: bridge.projectName || 'admin-llm-document-request',
        prompt: bridge.task || '',
    };
}

export function useFeatureOrchestrator() {
    const apiBaseUrl = React.useMemo(() => resolveApiBaseUrl(), []);
    const initialPreset = React.useMemo(() => getFeaturePreset('ai-sheet'), []);
    const featureMetaById = React.useMemo(() => FEATURE_EXPERIENCE_META, []);
    const [catalog, setCatalog] = React.useState<FeatureCatalogItem[]>([]);
    const [catalogLoading, setCatalogLoading] = React.useState(true);
    const [catalogError, setCatalogError] = React.useState('');
    const [isPopupOpen, setIsPopupOpen] = React.useState(false);
    const [activeFeatureId, setActiveFeatureId] = React.useState<string>('ai-sheet');
    const [projectName, setProjectName] = React.useState(initialPreset.projectName);
    const [prompt, setPrompt] = React.useState(initialPreset.prompt);
    const [templateId, setTemplateId] = React.useState(initialPreset.templateId);
    const [finalEnabled, setFinalEnabled] = React.useState(initialPreset.finalEnabled);
    const [photoFileName, setPhotoFileName] = React.useState('');
    const [photoContentType, setPhotoContentType] = React.useState('');
    const [photoSize, setPhotoSize] = React.useState<number | undefined>(undefined);
    const [photoPreviewUrl, setPhotoPreviewUrl] = React.useState('');
    const [popupState, setPopupState] = React.useState<FeaturePopupState>('idle');
    const [runId, setRunId] = React.useState('');
    const [stageRun, setStageRun] = React.useState<FeatureStageRun | null>(null);
    const [previewArtifact, setPreviewArtifact] = React.useState<FeatureArtifact | null>(null);
    const [finalArtifact, setFinalArtifact] = React.useState<FeatureArtifact | null>(null);
    const [qualityReview, setQualityReview] = React.useState<FeatureQualityReview | null>(null);
    const [submitLoading, setSubmitLoading] = React.useState(false);
    const [errorText, setErrorText] = React.useState('');
    const [eventLog, setEventLog] = React.useState<Array<{ state: FeaturePopupState; at: string }>>([]);
    const [streamConnection, setStreamConnection] = React.useState<FeatureStreamConnection>('idle');
    const [streamStartedAt, setStreamStartedAt] = React.useState('');
    const [latestEventAt, setLatestEventAt] = React.useState('');
    const [elapsedSeconds, setElapsedSeconds] = React.useState(0);
    const [progressSnapshot, setProgressSnapshot] = React.useState<FeatureProgressSnapshot | null>(null);
    const [progressHistory, setProgressHistory] = React.useState<FeatureProgressSnapshot[]>([]);
    const popupOpenedAtRef = React.useRef<string>('');

    const activeFeature = React.useMemo(() => catalog.find((item) => item.feature_id === activeFeatureId) || null, [activeFeatureId, catalog]);
    const activeFeatureMeta = React.useMemo(() => getFeatureExperienceMeta(activeFeatureId), [activeFeatureId]);

    React.useEffect(() => {
        let cancelled = false;
        const loadCatalog = async () => {
            setCatalogLoading(true);
            setCatalogError('');
            try {
                const response = await fetch(`${apiBaseUrl}/api/marketplace/feature-catalog`, { cache: 'no-store' });
                const payload = await response.json().catch(() => []);
                if (!response.ok) {
                    throw new Error('feature catalog 를 불러오지 못했습니다.');
                }
                if (!cancelled) {
                    setCatalog(mergeFeatureCatalog(payload));
                }
            } catch (error: any) {
                if (!cancelled) {
                    setCatalog(mergeFeatureCatalog([]));
                    setCatalogError('');
                }
            } finally {
                if (!cancelled) {
                    setCatalogLoading(false);
                }
            }
        };
        void loadCatalog();
        return () => {
            cancelled = true;
        };
    }, [apiBaseUrl]);

    React.useEffect(() => () => {
        if (photoPreviewUrl) {
            window.URL.revokeObjectURL(photoPreviewUrl);
        }
    }, [photoPreviewUrl]);

    React.useEffect(() => {
        if (!streamStartedAt) {
            setElapsedSeconds(0);
            return;
        }
        const updateElapsed = () => {
            const startedAt = new Date(streamStartedAt).getTime();
            if (Number.isNaN(startedAt)) {
                setElapsedSeconds(0);
                return;
            }
            setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
        };
        updateElapsed();
        if (streamConnection !== 'connecting' && streamConnection !== 'streaming') {
            return;
        }
        const timer = window.setInterval(updateElapsed, 1000);
        return () => {
            window.clearInterval(timer);
        };
    }, [streamConnection, streamStartedAt]);

    React.useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        const raw = window.localStorage.getItem(MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY);
        if (!raw) {
            return;
        }
        try {
            const parsed = JSON.parse(raw) as MarketplaceOrchestratorBridgePayload;
            const bridged = buildBridgePrompt(parsed);
            const preset = getFeaturePreset(bridged.featureId);
            const meta = getFeatureExperienceMeta(bridged.featureId);
            React.startTransition(() => {
                setActiveFeatureId(bridged.featureId);
                setProjectName(bridged.projectName);
                setPrompt(bridged.prompt);
                popupOpenedAtRef.current = new Date().toISOString();
                recordMarketplacePopupTelemetry(buildMarketplacePopupTelemetryEvent('popup_open', {
                    featureId: bridged.featureId,
                    popupMode: preset.contextTags[1] || meta.outputKind,
                    trigger: 'bridge_open',
                    metadata: {
                        projectName: bridged.projectName,
                    },
                }));
                setIsPopupOpen(true);
            });
        } catch {
        } finally {
            window.localStorage.removeItem(MARKETPLACE_ORCHESTRATOR_BRIDGE_KEY);
        }
    }, []);

    const openFeature = React.useCallback((featureId: string) => {
        const preset = getFeaturePreset(featureId);
        const meta = getFeatureExperienceMeta(featureId);
        setActiveFeatureId(featureId);
        setProjectName(preset.projectName);
        setPrompt(preset.prompt);
        setTemplateId(preset.templateId);
        setFinalEnabled(preset.finalEnabled);
        setErrorText('');
        popupOpenedAtRef.current = new Date().toISOString();
        recordMarketplacePopupTelemetry(buildMarketplacePopupTelemetryEvent('popup_open', {
            featureId,
            popupMode: activeFeature?.popup_mode || preset.contextTags[1] || meta.outputKind,
            metadata: {
                projectName: preset.projectName,
                templateId: preset.templateId,
            },
        }));
        setIsPopupOpen(true);
    }, [activeFeature?.popup_mode]);

    const closePopup = React.useCallback((trigger: string = 'close_button') => {
        const openedAt = popupOpenedAtRef.current ? new Date(popupOpenedAtRef.current).getTime() : Number.NaN;
        const elapsed = Number.isNaN(openedAt) ? undefined : Math.max(0, Math.floor((Date.now() - openedAt) / 1000));
        if (!popupOpenedAtRef.current) {
            setIsPopupOpen(false);
            return;
        }
        recordMarketplacePopupTelemetry(buildMarketplacePopupTelemetryEvent('popup_close', {
            featureId: activeFeatureId,
            popupMode: activeFeature?.popup_mode || getFeaturePreset(activeFeatureId).contextTags[1],
            runId,
            elapsedSeconds: elapsed,
            trigger,
            metadata: {
                popupState,
            },
        }));
        recordMarketplacePopupTelemetry(buildMarketplacePopupTelemetryEvent('popup_dwell_time', {
            featureId: activeFeatureId,
            popupMode: activeFeature?.popup_mode || getFeaturePreset(activeFeatureId).contextTags[1],
            runId,
            elapsedSeconds: elapsed,
            trigger,
            metadata: {
                popupState,
            },
        }));
        popupOpenedAtRef.current = '';
        setIsPopupOpen(false);
    }, [activeFeature?.popup_mode, activeFeatureId, popupState, runId]);

    const applyPhotoFile = React.useCallback((file: File | null) => {
        if (photoPreviewUrl) {
            window.URL.revokeObjectURL(photoPreviewUrl);
        }
        if (!file) {
            setPhotoFileName('');
            setPhotoContentType('');
            setPhotoSize(undefined);
            setPhotoPreviewUrl('');
            return;
        }
        setPhotoFileName(file.name);
        setPhotoContentType(file.type || 'application/octet-stream');
        setPhotoSize(file.size);
        setPhotoPreviewUrl(window.URL.createObjectURL(file));
    }, [photoPreviewUrl]);

    const refreshStageRun = React.useCallback(async (nextRunId: string) => {
        const response = await fetch(`${apiBaseUrl}/api/marketplace/feature-orchestrate/stage-runs/${encodeURIComponent(nextRunId)}`, { cache: 'no-store' });
        const payload = await response.json().catch(() => null);
        if (response.ok && payload) {
            setStageRun(payload as FeatureStageRun);
        }
    }, [apiBaseUrl]);

    React.useEffect(() => {
        if (!runId || (streamConnection !== 'connecting' && streamConnection !== 'streaming')) {
            return;
        }
        let cancelled = false;
        let timer: number | null = null;
        const pollStageRun = async () => {
            try {
                await refreshStageRun(runId);
            } catch {
            } finally {
                if (!cancelled) {
                    timer = window.setTimeout(() => {
                        void pollStageRun();
                    }, 1500);
                }
            }
        };
        void pollStageRun();
        return () => {
            cancelled = true;
            if (timer !== null) {
                window.clearTimeout(timer);
            }
        };
    }, [refreshStageRun, runId, streamConnection]);

    const applyEvent = React.useCallback(async (envelope: StreamEnvelope) => {
        const nextState = envelope.payload.state;
        const observedAt = new Date().toISOString();
        setLatestEventAt(observedAt);
        if (nextState) {
            setPopupState(nextState);
            setEventLog((prev) => [...prev, { state: nextState, at: observedAt }]);
            if (nextState === 'failed') {
                setStreamConnection('failed');
            } else if (nextState === 'completed' || nextState === 'completed_preview_only') {
                setStreamConnection('completed');
            } else {
                setStreamConnection('streaming');
            }
        }
        if (envelope.payload.progress) {
            setProgressSnapshot(envelope.payload.progress);
            setProgressHistory((prev) => [...prev, envelope.payload.progress as FeatureProgressSnapshot]);
        }
        if (envelope.payload.artifact) {
            setPreviewArtifact(envelope.payload.artifact);
        }
        if (envelope.event === 'quality_review' && envelope.payload.quality_review) {
            setQualityReview(envelope.payload.quality_review);
        }
        if (envelope.event === 'completed') {
            if (envelope.payload.artifact_manifest?.preview_artifact) {
                setPreviewArtifact(envelope.payload.artifact_manifest.preview_artifact);
            }
            if (envelope.payload.artifact_manifest?.final_artifact) {
                setFinalArtifact(envelope.payload.artifact_manifest.final_artifact);
            }
            if (envelope.payload.quality_review) {
                setQualityReview(envelope.payload.quality_review);
            }
        }
        if (envelope.event === 'failed') {
            setStreamConnection('failed');
            setErrorText(envelope.payload.message || 'feature orchestrator 실행 중 오류가 발생했습니다.');
        }
        if (envelope.payload.run_id) {
            await refreshStageRun(envelope.payload.run_id);
        }
    }, [refreshStageRun]);

    const submitFeature = React.useCallback(async () => {
        if (!prompt.trim()) {
            setErrorText('프롬프트를 입력하세요.');
            return;
        }
        setSubmitLoading(true);
        setErrorText('');
        setPopupState('accepted');
        setPreviewArtifact(null);
        setFinalArtifact(null);
        setQualityReview(null);
        const startedAt = new Date().toISOString();
        setEventLog([{ state: 'accepted', at: startedAt }]);
        setStreamConnection('connecting');
        setStreamStartedAt(startedAt);
        setLatestEventAt(startedAt);
        setProgressSnapshot({ percent: 0, step: 'accepted', state: 'accepted', message: '요청을 수락하고 스트림 연결을 준비합니다.', updated_at: startedAt });
        setProgressHistory([{ percent: 0, step: 'accepted', state: 'accepted', message: '요청을 수락하고 스트림 연결을 준비합니다.', updated_at: startedAt }]);
        recordMarketplacePopupTelemetry(buildMarketplacePopupTelemetryEvent('popup_submit', {
            featureId: activeFeatureId,
            popupMode: activeFeature?.popup_mode || getFeaturePreset(activeFeatureId).contextTags[1],
            runId,
            elapsedSeconds,
            trigger: 'submit_button',
            metadata: {
                templateId,
                finalEnabled,
                hasPhoto: Boolean(photoFileName),
            },
        }));
        try {
            const acceptedResponse = await fetch(`${apiBaseUrl}/api/marketplace/feature-orchestrate/accepted`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    feature_id: activeFeatureId,
                    project_name: projectName,
                    prompt,
                    template_id: templateId,
                    photo_reference: photoFileName || undefined,
                    photo_content_type: photoContentType || undefined,
                    photo_size: photoSize,
                    final_enabled: finalEnabled,
                    context_tags: getFeaturePreset(activeFeatureId).contextTags,
                }),
            });
            const acceptedPayload = await acceptedResponse.json().catch(() => null);
            if (!acceptedResponse.ok || !acceptedPayload) {
                throw new Error('feature orchestrator accepted 요청에 실패했습니다.');
            }
            setRunId(String(acceptedPayload.run_id || ''));
            setStageRun((acceptedPayload.stage_run || null) as FeatureStageRun | null);

            const streamResponse = await fetch(`${apiBaseUrl}/api/marketplace/feature-orchestrate/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ run_id: acceptedPayload.run_id }),
            });
            if (!streamResponse.ok || !streamResponse.body) {
                throw new Error('feature orchestrator stream 연결에 실패했습니다.');
            }
            setStreamConnection('streaming');
            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    break;
                }
                buffer += decoder.decode(value, { stream: true });
                const chunks = buffer.split('\n\n');
                buffer = chunks.pop() || '';
                for (const chunk of chunks) {
                    const line = chunk.split('\n').find((item) => item.startsWith('data: '));
                    if (!line) {
                        continue;
                    }
                    const envelope = JSON.parse(line.slice(6)) as StreamEnvelope;
                    await applyEvent(envelope);
                }
            }
            setStreamConnection((current) => (current === 'failed' ? current : 'completed'));
        } catch (error: any) {
            setPopupState('failed');
            setStreamConnection('failed');
            setLatestEventAt(new Date().toISOString());
            setErrorText(error?.message || 'feature orchestrator 실행에 실패했습니다.');
        } finally {
            setSubmitLoading(false);
        }
    }, [activeFeature?.popup_mode, activeFeatureId, apiBaseUrl, applyEvent, elapsedSeconds, finalEnabled, photoContentType, photoFileName, photoSize, projectName, prompt, runId, templateId]);

    const liveViewArtifact = React.useMemo<FeatureLiveViewArtifact | null>(() => {
        if (finalArtifact?.image_data_url) {
            return {
                title: '최종 산출물 라이브뷰',
                caption: 'final artifact 가 도착하면 즉시 최신 결과를 전면에 보여줍니다.',
                image_data_url: finalArtifact.image_data_url,
                source: 'final',
            };
        }
        if (previewArtifact?.image_data_url) {
            return {
                title: '프리뷰 라이브뷰',
                caption: 'preview 단계에서 준비된 이미지를 실시간으로 노출합니다.',
                image_data_url: previewArtifact.image_data_url,
                source: 'preview',
            };
        }
        if (photoPreviewUrl) {
            return {
                title: '참조 이미지 대기 화면',
                caption: '생성 전에는 업로드한 참조 이미지를 기준 화면으로 유지합니다.',
                image_data_url: photoPreviewUrl,
                source: 'upload',
            };
        }
        return null;
    }, [finalArtifact, photoPreviewUrl, previewArtifact]);

    const spreadsheetDownloadLinks = React.useMemo<SpreadsheetDownloadLink[]>(() => {
        const supportsDeliveryDownload = Boolean(finalArtifact?.delivery_assets?.length);
        if (!supportsDeliveryDownload || !runId) {
            return [];
        }
        const defaultBaseNames: Record<string, string> = {
            'ai-sheet': 'spreadsheet-result',
            'ai-powerpoint': 'powerpoint-result',
            'ai-document': 'document-result',
        };
        const defaultBaseName = defaultBaseNames[activeFeatureId] || 'feature-result';
        return (finalArtifact?.delivery_assets || [])
            .filter((asset) => Boolean(asset.format))
            .map((asset) => {
                const format = String(asset.format || '').toLowerCase();
                const generatedAt = String(asset.generated_at || finalArtifact?.generated_at || latestEventAt || '');
                return {
                    format,
                    href: `${apiBaseUrl}/api/marketplace/feature-orchestrate/stage-runs/${encodeURIComponent(runId)}/delivery-assets/${encodeURIComponent(format)}`,
                    fileName: `${projectName || defaultBaseName}.${format || 'bin'}`,
                    sizeLabel: formatFileSizeLabel(asset.size_bytes),
                    ready: Boolean(asset.exists),
                    completedAt: generatedAt,
                    completedAtLabel: generatedAt ? new Date(generatedAt).toLocaleString('ko-KR') : '기록 없음',
                };
            });
    }, [activeFeatureId, apiBaseUrl, finalArtifact?.delivery_assets, finalArtifact?.generated_at, latestEventAt, projectName, runId]);

    const spreadsheetRunSummary = React.useMemo<SpreadsheetRunSummary | null>(() => {
        if (activeFeatureId !== 'ai-sheet') {
            return null;
        }
        const sheetSchema = previewArtifact?.sheet_schema;
        const workbook = finalArtifact?.workbook;
        const stageMap: Record<FeaturePopupState, { label: string; description: string }> = {
            idle: { label: '대기', description: 'spreadsheet-builder 실행 전 상태입니다.' },
            accepted: { label: '요청 수락', description: '백엔드가 시트 생성 작업을 수락하고 실행 준비를 시작했습니다.' },
            preview_running: { label: '시트 schema 생성 중', description: '컬럼 구조와 목표 행 수를 계산하고 있습니다.' },
            preview_ready: { label: 'schema preview 준비', description: '시트 schema preview 결과를 확인할 수 있습니다.' },
            final_running: { label: 'workbook 패키징 중', description: 'xlsx/csv workbook 패키지를 생성하고 있습니다.' },
            quality_review: { label: 'quality 검토', description: '생성된 workbook 과 delivery asset 계약을 검증하고 있습니다.' },
            completed: { label: '완료', description: '최종 workbook 패키지와 다운로드 자산이 준비되었습니다.' },
            completed_preview_only: { label: 'preview 중심 완료', description: 'preview 기준 결과를 유지하며 final 품질 승격은 보류되었습니다.' },
            failed: { label: '실패', description: '실행 중 오류가 발생했습니다. 로그와 오류 메시지를 확인하세요.' },
        };
        const summary = stageMap[popupState];
        return {
            stageLabel: summary.label,
            stageDescription: summary.description,
            sheetName: String(workbook?.sheet_name || sheetSchema?.sheet_name || 'GeneratedSheet'),
            columnCount: Number(workbook?.column_count || sheetSchema?.columns?.length || 0),
            rowCount: Number(workbook?.row_count || sheetSchema?.row_goal || 0),
            promptSummary: String(finalArtifact?.prompt_summary || previewArtifact?.prompt_summary || prompt || ''),
        };
    }, [activeFeatureId, finalArtifact?.prompt_summary, finalArtifact?.workbook, popupState, previewArtifact?.prompt_summary, previewArtifact?.sheet_schema, prompt]);

    return {
        catalog,
        catalogLoading,
        catalogError,
        featureMetaById,
        activeFeature,
        activeFeatureMeta,
        activeFeatureId,
        isPopupOpen,
        openFeature,
        closePopup,
        projectName,
        setProjectName,
        prompt,
        setPrompt,
        templateId,
        setTemplateId,
        finalEnabled,
        setFinalEnabled,
        photoFileName,
        photoPreviewUrl,
        applyPhotoFile,
        popupState,
        runId,
        stageRun,
        previewArtifact,
        finalArtifact,
        qualityReview,
        submitLoading,
        submitFeature,
        errorText,
        eventLog,
        streamConnection,
        streamStartedAt,
        latestEventAt,
        elapsedSeconds,
        liveViewArtifact,
        spreadsheetDownloadLinks,
        spreadsheetRunSummary,
        progressSnapshot,
        progressHistory,
    };
}