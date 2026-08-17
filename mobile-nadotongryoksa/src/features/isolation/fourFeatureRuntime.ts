import {
    FOUR_FEATURE_CONTRACTS,
    type FourFeatureId,
    type LifecycleCommandInput,
    type SharedResourceKey,
} from './fourFeatureContracts';
import { createFourFeatureKernel } from './fourFeatureKernel';

const kernel = createFourFeatureKernel();
let activeFeatureId: FourFeatureId | null = null;
let transitionInFlight = false;

export type FeatureQuiesceHandlers = {
    stopCapture?: () => Promise<void> | void;
    stopPlayback?: () => Promise<void> | void;
    cleanup?: () => Promise<void> | void;
    restore?: () => Promise<void> | void;
};

const quiesceHandlerMap = new Map<FourFeatureId, FeatureQuiesceHandlers>();

type LeaseReport = {
    ok: boolean;
    conflicts: Array<{ resource: SharedResourceKey; owner: FourFeatureId }>;
};

export type ExclusiveActivationResult = {
    ok: boolean;
    blockedBy?: FourFeatureId;
    rolledBack?: boolean;
    message?: string;
};

function nowMs(): number {
    return Date.now();
}

function emitLifecycle(input: LifecycleCommandInput): void {
    const events = kernel.handleLifecycleCommand(input);
    if (events.length > 0) {
        console.log('[FOUR_FEATURE_LIFECYCLE]', JSON.stringify(events));
    }
}

async function runSafely(step: string, fn?: () => Promise<void> | void): Promise<void> {
    if (!fn) {
        return;
    }
    try {
        await fn();
    } catch (error) {
        console.warn('[FOUR_FEATURE_QUIESCE_STEP_FAIL]', JSON.stringify({
            step,
            message: error instanceof Error ? error.message : String(error),
        }));
        throw error;
    }
}

export function startFeatureLease(
    featureId: FourFeatureId,
    reason: string,
    source: LifecycleCommandInput['source'] = 'system',
): LeaseReport {
    const contract = FOUR_FEATURE_CONTRACTS[featureId];
    const conflicts: LeaseReport['conflicts'] = [];

    for (const requirement of contract.requiredResources) {
        const result = kernel.claim(requirement.resource, featureId);
        if (!result.ok) {
            conflicts.push({ resource: requirement.resource, owner: result.owner });
        }
    }

    emitLifecycle({
        featureId,
        command: 'start',
        reason,
        source,
        atMs: nowMs(),
    });

    if (conflicts.length > 0) {
        console.warn('[FOUR_FEATURE_LEASE_CONFLICT]', JSON.stringify({ featureId, reason, conflicts }));
    }

    return {
        ok: conflicts.length === 0,
        conflicts,
    };
}

export function stopFeatureLease(
    featureId: FourFeatureId,
    reason: string,
    source: LifecycleCommandInput['source'] = 'system',
): SharedResourceKey[] {
    emitLifecycle({
        featureId,
        command: 'stop',
        reason,
        source,
        atMs: nowMs(),
    });
    return kernel.releaseAll(featureId);
}

export function registerFeatureQuiesceHandlers(featureId: FourFeatureId, handlers: FeatureQuiesceHandlers | null): void {
    if (!handlers) {
        quiesceHandlerMap.delete(featureId);
        return;
    }
    quiesceHandlerMap.set(featureId, handlers);
}

export function getActiveFeatureId(): FourFeatureId | null {
    return activeFeatureId;
}

export function deactivateFeatureExclusive(
    featureId: FourFeatureId,
    reason: string,
    source: LifecycleCommandInput['source'] = 'system',
): SharedResourceKey[] {
    const released = stopFeatureLease(featureId, reason, source);
    if (activeFeatureId === featureId) {
        activeFeatureId = null;
    }
    return released;
}

export async function activateFeatureExclusive(
    featureId: FourFeatureId,
    reason: string,
    source: LifecycleCommandInput['source'] = 'system',
): Promise<ExclusiveActivationResult> {
    if (transitionInFlight) {
        return {
            ok: false,
            blockedBy: activeFeatureId ?? undefined,
            message: 'transition_in_progress',
        };
    }

    if (activeFeatureId === featureId) {
        return { ok: true, message: 'already_active' };
    }

    transitionInFlight = true;
    const previousFeatureId = activeFeatureId;
    const previousHandlers = previousFeatureId ? quiesceHandlerMap.get(previousFeatureId) : null;

    try {
        if (previousFeatureId && previousFeatureId !== featureId) {
            // Hard quiesce order: capture stop -> playback stop -> resource release.
            await runSafely(`${previousFeatureId}:stop_capture`, previousHandlers?.stopCapture);
            await runSafely(`${previousFeatureId}:stop_playback`, previousHandlers?.stopPlayback);
            await runSafely(`${previousFeatureId}:cleanup`, previousHandlers?.cleanup);
            deactivateFeatureExclusive(previousFeatureId, `quiesce_for_${featureId}:${reason}`, 'system');
        }

        const lease = startFeatureLease(featureId, reason, source);
        if (!lease.ok) {
            deactivateFeatureExclusive(featureId, `lease_conflict:${reason}`, 'system');

            if (previousFeatureId && previousFeatureId !== featureId) {
                const rollbackLease = startFeatureLease(previousFeatureId, `rollback_after_conflict:${reason}`, 'system');
                if (rollbackLease.ok) {
                    await runSafely(`${previousFeatureId}:restore`, previousHandlers?.restore);
                    activeFeatureId = previousFeatureId;
                    return {
                        ok: false,
                        blockedBy: lease.conflicts[0]?.owner,
                        rolledBack: true,
                        message: 'lease_conflict_rolled_back',
                    };
                }
            }

            return {
                ok: false,
                blockedBy: lease.conflicts[0]?.owner,
                message: 'lease_conflict',
            };
        }

        activeFeatureId = featureId;
        return { ok: true };
    } catch (error) {
        if (previousFeatureId && previousFeatureId !== featureId) {
            const rollbackLease = startFeatureLease(previousFeatureId, `rollback_after_error:${reason}`, 'system');
            if (rollbackLease.ok) {
                await runSafely(`${previousFeatureId}:restore_after_error`, previousHandlers?.restore);
                activeFeatureId = previousFeatureId;
                return {
                    ok: false,
                    blockedBy: previousFeatureId,
                    rolledBack: true,
                    message: 'transition_failed_rolled_back',
                };
            }
        }

        return {
            ok: false,
            blockedBy: previousFeatureId ?? undefined,
            message: error instanceof Error ? error.message : 'transition_failed',
        };
    } finally {
        transitionInFlight = false;
    }
}

export function getFeatureLeaseOwner(resource: SharedResourceKey): FourFeatureId | null {
    return kernel.getOwner(resource);
}
