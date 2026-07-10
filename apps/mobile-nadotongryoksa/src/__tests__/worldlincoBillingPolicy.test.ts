import {
    getWorldlincoBillingPolicySnapshot,
    isWorldlincoFreeAccessForUser,
    WORLDLINGCO_BILLING_POLICY_DEFAULTS,
} from '../services/worldlincoBillingPolicy';

describe('worldlincoBillingPolicy', () => {
    it('defaults to free beta access', () => {
        expect(WORLDLINGCO_BILLING_POLICY_DEFAULTS.free_access_active).toBe(true);
        expect(WORLDLINGCO_BILLING_POLICY_DEFAULTS.show_pricing_ui).toBe(false);
    });

    it('grants free access for logged-in users when policy is free', () => {
        const policy = getWorldlincoBillingPolicySnapshot();
        expect(isWorldlincoFreeAccessForUser({ ...policy, free_access_active: true }, true)).toBe(true);
        expect(isWorldlincoFreeAccessForUser({ ...policy, free_access_active: true }, false)).toBe(false);
    });

    it('blocks free access when paid mode is active without pause', () => {
        const policy = getWorldlincoBillingPolicySnapshot();
        expect(isWorldlincoFreeAccessForUser({
            ...policy,
            access_mode: 'paid',
            free_access_active: false,
        }, true)).toBe(false);
    });

    it('allows free access when billing collection is paused', () => {
        const policy = getWorldlincoBillingPolicySnapshot();
        expect(isWorldlincoFreeAccessForUser({
            ...policy,
            access_mode: 'paid',
            billing_collection_paused: true,
            free_access_active: true,
        }, true)).toBe(true);
    });
});
