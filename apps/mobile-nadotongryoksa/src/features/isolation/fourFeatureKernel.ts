import type {
    FeatureOutputEvent,
    FourFeatureId,
    LifecycleCommandInput,
    SharedResourceKey,
} from './fourFeatureContracts';

type ResourceOwnerMap = Map<SharedResourceKey, FourFeatureId>;

export type ClaimResult =
    | { ok: true }
    | { ok: false; owner: FourFeatureId };

export type FourFeatureKernel = {
    claim: (resource: SharedResourceKey, owner: FourFeatureId) => ClaimResult;
    releaseAll: (owner: FourFeatureId) => SharedResourceKey[];
    handleLifecycleCommand: (input: LifecycleCommandInput) => FeatureOutputEvent[];
    getOwner: (resource: SharedResourceKey) => FourFeatureId | null;
};

export function createFourFeatureKernel(): FourFeatureKernel {
    const owners: ResourceOwnerMap = new Map();

    function claim(resource: SharedResourceKey, owner: FourFeatureId): ClaimResult {
        const current = owners.get(resource);
        if (!current || current === owner) {
            owners.set(resource, owner);
            return { ok: true };
        }
        return { ok: false, owner: current };
    }

    function releaseAll(owner: FourFeatureId): SharedResourceKey[] {
        const released: SharedResourceKey[] = [];
        for (const [resource, currentOwner] of owners.entries()) {
            if (currentOwner === owner) {
                owners.delete(resource);
                released.push(resource);
            }
        }
        return released;
    }

    function handleLifecycleCommand(input: LifecycleCommandInput): FeatureOutputEvent[] {
        const events: FeatureOutputEvent[] = [];

        if (input.command === 'stop' || input.command === 'quiesce') {
            const released = releaseAll(input.featureId);
            for (const resource of released) {
                events.push({
                    type: 'resource-release',
                    featureId: input.featureId,
                    resource,
                    atMs: input.atMs,
                });
            }
        }

        events.push({
            type: 'status',
            featureId: input.featureId,
            message: `${input.command}:${input.reason}`,
            atMs: input.atMs,
        });

        return events;
    }

    function getOwner(resource: SharedResourceKey): FourFeatureId | null {
        return owners.get(resource) ?? null;
    }

    return {
        claim,
        releaseAll,
        handleLifecycleCommand,
        getOwner,
    };
}
