import { useCallback } from 'react';
import {
    refreshAdminStageRunAction,
    runCostSimulationAction,
    updateAdminStageStatusAction,
} from '@/lib/admin-dashboard-actions';
import type { AdminPageActionsParams, AdminPageActionsResult } from '@/app/admin/admin-page-types';
import { clearAdminToken } from '@/lib/admin-session';
import { hardRedirectToAdminLogin } from '@/lib/admin-navigation';

export function useAdminPageActions(params: AdminPageActionsParams): AdminPageActionsResult {
    const {
        apiBaseUrl,
        setAdminUser,
        setAuthChecked,
        setAuthStatusMessage,
        setError,
        setAdVideoOrders,
        setAdVideoTotal,
        setAdminStageRun,
        setAdminStageSubstepChecks,
        adminStageRun,
        adminStageNoteDraft,
        adminStageRevisionNote,
        adminStageSubstepChecks,
        pushLiveLog,
        setAdminStageRevisionNote,
        setAdminStageNoteDraft,
        setAdminStageUpdateLoading,
        costSimulatorForm,
        setCostSimulatorLoading,
        setCostSimulatorError,
        setCostSimulatorResult,
        setGeneratorModelOverrides,
        generatorEnvKeyMap,
        updateSystemSettingValue,
    } = params;

    const handleAdminUnauthorized = useCallback((message = '관리자 세션이 만료되었습니다. 다시 로그인하세요.') => {
        clearAdminToken();
        setAdminUser(null);
        setAuthChecked(false);
        setAuthStatusMessage(message);
        setError(null);
        setAdVideoOrders([]);
        setAdVideoTotal(0);
        hardRedirectToAdminLogin();
    }, [setAdVideoOrders, setAdVideoTotal, setAdminUser, setAuthChecked, setAuthStatusMessage, setError]);

    const refreshAdminStageRun = useCallback((runId: string) => refreshAdminStageRunAction({
        apiBaseUrl,
        runId,
        onUnauthorized: () => handleAdminUnauthorized(),
        setAdminStageRun,
        setAdminStageSubstepChecks,
    }), [apiBaseUrl, handleAdminUnauthorized, setAdminStageRun, setAdminStageSubstepChecks]);

    const updateAdminStageStatus = useCallback((status: 'passed' | 'failed' | 'manual_correction') => updateAdminStageStatusAction({
        apiBaseUrl,
        adminStageRun,
        adminStageNoteDraft,
        adminStageRevisionNote,
        adminStageSubstepChecks,
        status,
        onUnauthorized: () => handleAdminUnauthorized(),
        pushLiveLog,
        setAdminStageRun,
        setAdminStageSubstepChecks,
        setAdminStageRevisionNote,
        setAdminStageNoteDraft,
        setAdminStageUpdateLoading,
    }), [
        adminStageNoteDraft,
        adminStageRevisionNote,
        adminStageRun,
        adminStageSubstepChecks,
        apiBaseUrl,
        handleAdminUnauthorized,
        pushLiveLog,
        setAdminStageNoteDraft,
        setAdminStageRevisionNote,
        setAdminStageRun,
        setAdminStageSubstepChecks,
        setAdminStageUpdateLoading,
    ]);

    const runCostSimulation = useCallback(() => runCostSimulationAction({
        apiBaseUrl,
        costSimulatorForm,
        onUnauthorized: () => handleAdminUnauthorized(),
        setCostSimulatorLoading,
        setCostSimulatorError,
        setCostSimulatorResult,
    }), [
        apiBaseUrl,
        costSimulatorForm,
        handleAdminUnauthorized,
        setCostSimulatorError,
        setCostSimulatorLoading,
        setCostSimulatorResult,
    ]);

    const applyGeneratorModelOverride = useCallback((profileId: string, modelName: string) => {
        setGeneratorModelOverrides((prev) => ({
            ...prev,
            [profileId]: modelName,
        }));
        const envKeys = generatorEnvKeyMap[profileId] || [];
        envKeys.forEach((envKey) => updateSystemSettingValue(envKey, modelName));
    }, [generatorEnvKeyMap, setGeneratorModelOverrides, updateSystemSettingValue]);

    return {
        handleAdminUnauthorized,
        refreshAdminStageRun,
        updateAdminStageStatus,
        runCostSimulation,
        applyGeneratorModelOverride,
    };
}