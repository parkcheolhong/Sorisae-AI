import type { Dispatch, SetStateAction } from 'react';

const RUNTIME_PROFILE_CUSTOM_KEY = 'custom';
const DEFAULT_HYBRID_NUM_GPU = 32;

type RuntimeTuningLevel = -1 | 0 | 1;

type AccelerationMode = 'cpu_only' | 'gpu_only';
type ModelRouteKey =
    | 'default'
    | 'reasoning'
    | 'coding'
    | 'chat'
    | 'voice_chat'
    | 'planner'
    | 'coder'
    | 'reviewer'
    | 'designer'
    | 'smart_planner'
    | 'smart_executor'
    | 'smart_designer';

interface RuntimeExecutionControlLike {
    acceleration_mode?: AccelerationMode;
    num_gpu?: number;
    num_thread?: number;
}

interface RuntimeProfileLike {
    key: string;
    label: string;
    model_routes: Record<ModelRouteKey, string>;
    execution_controls?: Partial<Record<ModelRouteKey, RuntimeExecutionControlLike>>;
    settings: Record<string, unknown>;
}

interface FeaturedModelActionLike {
    label: string;
    targets: Partial<Record<ModelRouteKey, string>>;
}

interface FunctionalModelGradeRowLike {
    title: string;
}

interface ModelGradeChoiceLike {
    label: string;
    targets: Partial<Record<ModelRouteKey, string>>;
}

interface AdvisoryControlsLike {
    clarification_questions_enabled: boolean;
    max_clarification_questions: number;
    evidence_panel_enabled: boolean;
    max_evidence_items: number;
    next_action_suggestions_enabled: boolean;
    max_next_actions: number;
    scientific_reasoning_enabled?: boolean;
    systems_thinking_enabled?: boolean;
    future_tech_expansion_enabled?: boolean;
    cross_domain_synthesis_enabled?: boolean;
    innovation_scenarios_enabled?: boolean;
    max_innovation_scenarios?: number;
    max_system_design_alternatives?: number;
}

interface OrchestratorRuntimeConfigLike {
    selected_profile?: string;
    gpu_only_preferred?: boolean;
    code_generation_strategy?: string;
    model_tuning_level?: number;
    token_tuning_level?: number;
    timeout_tuning_level?: number;
    model_routes: Record<ModelRouteKey, string>;
    execution_controls?: Partial<Record<ModelRouteKey, RuntimeExecutionControlLike>>;
    advisory_controls?: AdvisoryControlsLike;
    runtime_profiles?: RuntimeProfileLike[];
    available_models: string[];
    [key: string]: any;
}

export function createRuntimeConfigMutationHelpers<T extends OrchestratorRuntimeConfigLike>(options: {
    setRuntimeDraft: Dispatch<SetStateAction<T | null>>;
    setRuntimeMessage: (value: string) => void;
    defaultAdvisoryControls: AdvisoryControlsLike;
    modelRouteFields: Array<[ModelRouteKey, string]>;
    resolveHybridExecutionNumGpu: (control?: RuntimeExecutionControlLike) => number;
    buildTunedModelRoutes: (draft: T, level: RuntimeTuningLevel) => Record<ModelRouteKey, string>;
    tokenTuningPresets: Record<RuntimeTuningLevel, Partial<T>>;
    timeoutTuningPresets: Record<RuntimeTuningLevel, Partial<T>>;
}) {
    const updateRuntimeField = (field: keyof T, value: string) => {
        options.setRuntimeDraft((prev) => (
            prev
                ? (() => {
                    const trimmedValue = value.trim();
                    const parsedValue = trimmedValue === '' ? 0 : Number(trimmedValue);
                    return Number.isFinite(parsedValue)
                        ? {
                            ...prev,
                            selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                            [field]: Math.trunc(parsedValue),
                        }
                        : prev;
                })()
                : prev
        ));
    };

    const updateRuntimeToggle = (
        field: 'force_complete' | 'allow_synthetic_fallback',
        nextValue: boolean,
    ) => {
        options.setRuntimeDraft((prev) => (
            prev
                ? {
                    ...prev,
                    selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                    [field]: nextValue,
                }
                : prev
        ));
    };

    const updateGlobalExecutionPreference = (gpuOnlyPreferred: boolean) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            const nextExecutionControls = options.modelRouteFields.reduce<Partial<Record<ModelRouteKey, RuntimeExecutionControlLike>>>((acc, [field]) => {
                const currentControl = {
                    ...(prev.execution_controls?.[field] || {}),
                };

                acc[field] = {
                    ...currentControl,
                    acceleration_mode: 'gpu_only',
                    num_gpu: gpuOnlyPreferred ? -1 : options.resolveHybridExecutionNumGpu(currentControl),
                };
                return acc;
            }, {
                ...(prev.execution_controls || {}),
            });

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                gpu_only_preferred: gpuOnlyPreferred,
                execution_controls: nextExecutionControls,
            };
        });
    };

    const parseNullableNumber = (value: string) => {
        const trimmed = value.trim();
        if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'n/a') {
            return null;
        }
        const parsed = Number(trimmed);
        return Number.isFinite(parsed) ? parsed : null;
    };

    const updateGlobalExecutionNumeric = (
        numericField: 'num_gpu' | 'num_thread',
        value: string,
    ) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            const parsedValue = parseNullableNumber(value);
            const gpuOnlyPreferred = prev.gpu_only_preferred !== false;
            const nextExecutionControls = options.modelRouteFields.reduce<Partial<Record<ModelRouteKey, RuntimeExecutionControlLike>>>((acc, [field]) => {
                const currentControl = {
                    ...(prev.execution_controls?.[field] || {}),
                };

                if (numericField === 'num_gpu') {
                    currentControl.acceleration_mode = 'gpu_only';
                    currentControl.num_gpu = gpuOnlyPreferred
                        ? -1
                        : Math.max(1, Math.trunc(parsedValue ?? DEFAULT_HYBRID_NUM_GPU));
                } else if (parsedValue == null) {
                    delete currentControl.num_thread;
                } else {
                    currentControl.num_thread = Math.max(1, Math.trunc(parsedValue));
                }

                acc[field] = currentControl;
                return acc;
            }, {
                ...(prev.execution_controls || {}),
            });

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                execution_controls: nextExecutionControls,
            };
        });
    };

    const updateAdvisoryToggle = (
        field: keyof Pick<AdvisoryControlsLike, 'clarification_questions_enabled' | 'evidence_panel_enabled' | 'next_action_suggestions_enabled'>,
        nextValue: boolean,
    ) => {
        options.setRuntimeDraft((prev) => (
            prev
                ? {
                    ...prev,
                    selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                    advisory_controls: {
                        ...options.defaultAdvisoryControls,
                        ...(prev.advisory_controls || {}),
                        [field]: nextValue,
                    },
                }
                : prev
        ));
    };

    const updateAdvisoryNumeric = (
        field: keyof Pick<AdvisoryControlsLike, 'max_clarification_questions' | 'max_evidence_items' | 'max_next_actions'>,
        value: string,
    ) => {
        options.setRuntimeDraft((prev) => (
            prev
                ? (() => {
                    const trimmedValue = value.trim();
                    const parsedValue = trimmedValue === '' ? 0 : Number(trimmedValue);
                    return Number.isFinite(parsedValue)
                        ? {
                            ...prev,
                            selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                            advisory_controls: {
                                ...options.defaultAdvisoryControls,
                                ...(prev.advisory_controls || {}),
                                [field]: Math.trunc(parsedValue),
                            },
                        }
                        : prev;
                })()
                : prev
        ));
    };

    const updateRuntimeModelRoute = (field: ModelRouteKey, value: string) => {
        options.setRuntimeDraft((prev) => (
            prev
                ? {
                    ...prev,
                    selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                    model_routes: {
                        ...prev.model_routes,
                        [field]: value,
                    },
                }
                : prev
        ));
    };

    const updateRuntimeExecutionMode = (field: ModelRouteKey, value: AccelerationMode) => {
        options.setRuntimeDraft((prev) => (
            prev
                ? (() => {
                    const nextControl: RuntimeExecutionControlLike = {
                        ...(prev.execution_controls?.[field] || {}),
                        acceleration_mode: value,
                    };

                    if (value === 'cpu_only') {
                        nextControl.num_gpu = 0;
                    } else if (nextControl.num_gpu === 0) {
                        delete nextControl.num_gpu;
                    }

                    return {
                        ...prev,
                        selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                        execution_controls: {
                            ...(prev.execution_controls || {}),
                            [field]: nextControl,
                        },
                    };
                })()
                : prev
        ));
    };

    const updateRuntimeExecutionNumeric = (
        field: ModelRouteKey,
        numericField: 'num_gpu' | 'num_thread',
        value: string,
    ) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }
            const trimmedValue = value.trim();
            const parsedValue = trimmedValue === '' ? undefined : Number(trimmedValue);
            const currentControl = {
                ...(prev.execution_controls?.[field] || {}),
            };

            if (parsedValue == null || !Number.isFinite(parsedValue)) {
                delete currentControl[numericField];
            } else {
                currentControl[numericField] = numericField === 'num_thread'
                    ? Math.max(1, Math.trunc(parsedValue))
                    : Math.trunc(parsedValue);
            }

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                execution_controls: {
                    ...(prev.execution_controls || {}),
                    [field]: currentControl,
                },
            };
        });
    };

    const applyRuntimeProfile = (profile: RuntimeProfileLike) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }
            return {
                ...prev,
                ...profile.settings,
                selected_profile: profile.key,
                model_routes: {
                    ...prev.model_routes,
                    ...profile.model_routes,
                },
                execution_controls: {
                    ...(prev.execution_controls || {}),
                    ...(profile.execution_controls || {}),
                },
            };
        });
        options.setRuntimeMessage(`${profile.label} 프리셋을 초안에 반영했습니다. 저장하면 즉시 적용됩니다.`);
    };

    const applyFunctionalModelGrade = (row: FunctionalModelGradeRowLike, grade: ModelGradeChoiceLike) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                model_routes: {
                    ...prev.model_routes,
                    ...grade.targets,
                },
            };
        });
        options.setRuntimeMessage(`${row.title}을 ${grade.label} 등급 초안으로 반영했습니다. 저장하면 즉시 적용됩니다.`);
    };

    const applyFeaturedModelAction = (row: FunctionalModelGradeRowLike, action: FeaturedModelActionLike) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                model_routes: {
                    ...prev.model_routes,
                    ...action.targets,
                },
            };
        });
        options.setRuntimeMessage(`${row.title}을 ${action.label} 초안으로 반영했습니다. 저장하면 즉시 적용됩니다.`);
    };

    const applyModelTuningLevel = (level: RuntimeTuningLevel) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            const selectedProfile = level === 0 && prev.selected_profile && prev.selected_profile !== RUNTIME_PROFILE_CUSTOM_KEY
                ? prev.selected_profile
                : RUNTIME_PROFILE_CUSTOM_KEY;

            return {
                ...prev,
                selected_profile: selectedProfile,
                model_tuning_level: level,
                model_routes: options.buildTunedModelRoutes(prev, level),
            };
        });
        options.setRuntimeMessage(`모델 단계 ${level > 0 ? `+${level}` : level} 초안을 반영했습니다. 저장하면 즉시 적용됩니다.`);
    };

    const applyTokenTuningLevel = (level: RuntimeTuningLevel) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                token_tuning_level: level,
                ...options.tokenTuningPresets[level],
            };
        });
        options.setRuntimeMessage(`토큰 단계 ${level > 0 ? `+${level}` : level} 초안을 반영했습니다. 저장하면 즉시 적용됩니다.`);
    };

    const applyTimeoutTuningLevel = (level: RuntimeTuningLevel) => {
        options.setRuntimeDraft((prev) => {
            if (!prev) {
                return prev;
            }

            return {
                ...prev,
                selected_profile: RUNTIME_PROFILE_CUSTOM_KEY,
                timeout_tuning_level: level,
                ...options.timeoutTuningPresets[level],
            };
        });
        options.setRuntimeMessage(`시간 단계 ${level > 0 ? `+${level}` : level} 초안을 반영했습니다. 저장하면 즉시 적용됩니다.`);
    };

    return {
        updateRuntimeField,
        updateRuntimeToggle,
        updateGlobalExecutionPreference,
        updateGlobalExecutionNumeric,
        updateAdvisoryToggle,
        updateAdvisoryNumeric,
        updateRuntimeModelRoute,
        updateRuntimeExecutionMode,
        updateRuntimeExecutionNumeric,
        applyRuntimeProfile,
        applyFunctionalModelGrade,
        applyFeaturedModelAction,
        applyModelTuningLevel,
        applyTokenTuningLevel,
        applyTimeoutTuningLevel,
    };
}
