import { describe, expect, it, jest } from '@jest/globals';

import { beginSorisaeButtonDrag, markSorisaeButtonDragged, openSorisaeWindowIfTap } from '../features/sorisae/sorisaeOpenButton';

describe('sorisaeOpenButton', () => {
    it('tracks drag movement and opens only on tap', () => {
        const dragMovedRef = { current: true };
        const sorisaeWindowOpenRef = { current: false };
        const setSorisaeWindowOpen = jest.fn();
        const buttonPosition = { extractOffset: jest.fn() };

        beginSorisaeButtonDrag({ dragMovedRef, buttonPosition });
        expect(dragMovedRef.current).toBe(false);
        expect(buttonPosition.extractOffset).toHaveBeenCalled();

        markSorisaeButtonDragged({ dragMovedRef }, 5, 0);
        expect(dragMovedRef.current).toBe(true);

        openSorisaeWindowIfTap({ dragMovedRef, sorisaeWindowOpenRef, setSorisaeWindowOpen });
        expect(sorisaeWindowOpenRef.current).toBe(false);
        expect(setSorisaeWindowOpen).not.toHaveBeenCalled();

        dragMovedRef.current = false;
        openSorisaeWindowIfTap({ dragMovedRef, sorisaeWindowOpenRef, setSorisaeWindowOpen });

        expect(sorisaeWindowOpenRef.current).toBe(true);
        expect(setSorisaeWindowOpen).toHaveBeenCalledWith(true);
    });
});