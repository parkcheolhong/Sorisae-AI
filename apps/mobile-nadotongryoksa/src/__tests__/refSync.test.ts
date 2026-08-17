import { describe, expect, it } from '@jest/globals';

import { syncRefCurrent } from '../features/shared/refSync';

describe('refSync', () => {
    it('writes the latest value to the ref', () => {
        const ref = { current: 'before' };

        syncRefCurrent(ref, 'after');

        expect(ref.current).toBe('after');
    });
});