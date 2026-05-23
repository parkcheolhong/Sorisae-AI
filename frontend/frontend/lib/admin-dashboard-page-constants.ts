import type { AdminSystemSettingStatusSection } from '@/lib/admin-system-settings-service';

export const ADMIN_MANUAL_ORCHESTRATOR_STATE_STORAGE_KEY = 'admin_manual_orchestrator_state_v1';
export const ADMIN_MANUAL_ORCHESTRATOR_META_STORAGE_KEY = 'admin_manual_orchestrator_meta_v1';
export const ADMIN_MANUAL_ORCHESTRATOR_STAGE_RUN_ID_STORAGE_KEY = 'admin_manual_orchestrator_stage_run_id_v1';
export const ADMIN_HIDE_EMPTY_CATEGORIES_STORAGE_KEY = 'admin_hide_empty_categories_v1';
export const ADMIN_CATEGORY_SORT_STORAGE_KEY = 'admin_category_sort_v1';
export const ADMIN_LIVE_LOGS_STORAGE_KEY = 'admin_live_logs_v1';
export const ADMIN_SAMPLE_SETTINGS_STORAGE_KEY = 'admin_sample_settings_v1';
export const ADMIN_ALERT_VOICE_ENABLED_STORAGE_KEY = 'admin_alert_voice_enabled_v1';
export const ADMIN_AUTO_RECOVERY_HISTORY_STORAGE_KEY = 'admin_auto_recovery_history_v1';
export const ADMIN_DASHBOARD_PREFERENCES_STORAGE_KEY = 'admin_dashboard_preferences_v1';

export const ADMIN_HUMAN_OBJECT_INTERACTION_RULES = [
    '손이 컵에 먼저 닿은 뒤에만 컵이 떠오를 수 있습니다.',
    '손-컵-입 이동은 중간 포즈 없이 순간이동하면 안 됩니다.',
    '걷기와 뛰기는 보폭, 몸통 기울기, 팔 흔들림이 달라야 합니다.',
    '4D 디자이너는 자연어로 키프레임 이미지를 만들고 영상 단계는 편집/이음 연결 중심으로 해석합니다.',
    '모델 제스처를 허용하고 손, 팔, 어깨, 시선이 함께 자연스럽게 연동되어야 합니다.',
    '자연 표정을 유지하고 얼굴이 고정되거나 기계적으로 멈추면 안 됩니다.',
    '전신 자유 모션을 허용하고 상체만 움직이는 반쪽 모션으로 제한하지 않습니다.',
    '포즈 반복을 금지하고 인접 컷에서 같은 자세를 복제하지 않습니다.',
] as const;

export const GENERATOR_ENV_KEY_MAP: Record<string, string[]> = {
    python_fastapi: ['LLM_MODEL_REASONING', 'LLM_MODEL_PLANNER', 'LLM_MODEL_SMART_PLANNER'],
    python_worker: ['LLM_MODEL_CODER', 'LLM_MODEL_SMART_EXECUTOR'],
    nextjs_react: ['LLM_MODEL_CHAT', 'LLM_MODEL_DESIGNER', 'LLM_MODEL_SMART_DESIGNER'],
    node_service: ['LLM_MODEL_CODING', 'LLM_MODEL_CODER'],
    go_service: ['LLM_MODEL_REVIEWER'],
    rust_service: ['LLM_MODEL_DEFAULT'],
};

export const OPTIMIZED_GENERATOR_DEFAULTS: Record<string, string[]> = {
    reasoning: ['qwen2.5-coder:32b-q6k', 'deepseek-r1:32b', 'deepseek-r1:70b'],
    coding: ['qwen2.5-coder:32b-q5km', 'qwen2.5-coder:32b-q8'],
    template: ['qwen2.5-coder:32b-q4km', 'qwen2.5-coder:32b-q5km'],
    uiux: ['gemma3:27b', 'qwen2.5-coder:32b-q4km'],
    ad_video: ['glm4:latest', 'gemma3:27b', 'qwen2.5:72b'],
};

export const OPTIMIZED_RUNTIME_ROUTE_ENV_MAP: Record<string, string> = {
    default: 'LLM_MODEL_DEFAULT',
    reasoning: 'LLM_MODEL_REASONING',
    coding: 'LLM_MODEL_CODING',
    chat: 'LLM_MODEL_CHAT',
    voice_chat: 'LLM_MODEL_VOICE_CHAT',
    planner: 'LLM_MODEL_PLANNER',
    coder: 'LLM_MODEL_CODER',
    reviewer: 'LLM_MODEL_REVIEWER',
    designer: 'LLM_MODEL_DESIGNER',
    smart_planner: 'LLM_MODEL_SMART_PLANNER',
    smart_executor: 'LLM_MODEL_SMART_EXECUTOR',
    smart_designer: 'LLM_MODEL_SMART_DESIGNER',
};

export const OPTIMIZED_RUNTIME_ROUTE_PRESETS: Record<string, string[]> = {
    default: OPTIMIZED_GENERATOR_DEFAULTS.coding,
    reasoning: OPTIMIZED_GENERATOR_DEFAULTS.reasoning,
    coding: OPTIMIZED_GENERATOR_DEFAULTS.coding,
    chat: OPTIMIZED_GENERATOR_DEFAULTS.template,
    voice_chat: OPTIMIZED_GENERATOR_DEFAULTS.ad_video,
    planner: OPTIMIZED_GENERATOR_DEFAULTS.reasoning,
    coder: OPTIMIZED_GENERATOR_DEFAULTS.coding,
    reviewer: OPTIMIZED_GENERATOR_DEFAULTS.reasoning,
    designer: OPTIMIZED_GENERATOR_DEFAULTS.uiux,
    smart_planner: OPTIMIZED_GENERATOR_DEFAULTS.reasoning,
    smart_executor: OPTIMIZED_GENERATOR_DEFAULTS.coding,
    smart_designer: OPTIMIZED_GENERATOR_DEFAULTS.uiux,
};

export const ADMIN_ACTION_TEMPLATE_LABELS: Record<string, string> = {
    cup_lift_drink: '컵 집기 · 들기 · 마시기',
    walk_or_run_pass: '걷기/뛰기 이동',
};

export const ADMIN_SYSTEM_SETTINGS_STATUS_SECTIONS: AdminSystemSettingStatusSection[] = [
    {
        id: 'domain_network',
        title: '도메인 / 네트워크',
        usage: '접속 주소, 포트, 프록시 기준 변경',
        description: '도메인, 허용 Origin, 게이트웨이 포트를 조정하는 전역 설정 영역입니다.',
    },
    {
        id: 'marketplace_storage',
        title: '스토리지 / 다운로드 정책',
        usage: '산출물 루트, 보관 기간, 다운로드 제한 조정',
        description: '마켓플레이스 산출물 저장 경로와 다운로드 정책을 제어하는 영역입니다.',
    },
    {
        id: 'video_engine',
        title: '전용 영상 엔진',
        usage: '영상 엔진 주소, 타임아웃, fallback 정책 조정',
        description: '전용 영상 엔진 주소와 폴링/대기 정책을 제어하는 영역입니다.',
    },
    {
        id: 'llm_defaults',
        title: 'LLM 기본 환경값',
        usage: '부팅 기본 모델 환경값 점검 / 교체',
        description: '역할별 기본 모델 환경값과 부팅 시 참조되는 기본 구성을 다룹니다.',
    },
    {
        id: 'orchestrator_self_engine',
        title: '오케스트레이터 / 셀프 엔진',
        usage: '자가 실행 게이트와 로컬 생성 파라미터 조정',
        description: '자가 실행 게이트와 로컬 생성형 엔진 파라미터를 조정하는 영역입니다.',
    },
];
