import { describe, expect, it, jest } from '@jest/globals';

import { applyBookingRequestFailureNow, applyBookingRequestSuccessNow, applyNearbySearchFailureNow, applyNearbySearchSuccessNow, beginBookingRequestNow, beginNearbySearchNow, finishBookingRequestNow } from '../features/travel-booking/travelBookingController';

describe('travelBookingController', () => {
    it('initializes nearby search state', () => {
        const events: string[] = [];

        beginNearbySearchNow({
            setNearbyLoading: (value) => events.push(`loading:${String(value)}`),
            setNearbyError: (value) => events.push(`error:${value}`),
            setNearbyPlaces: (value) => events.push(`places:${value.length}`),
            setSelectedNearbyPlaceId: (value) => events.push(`selected:${value}`),
            setBookingResult: (value) => events.push(`booking:${String(value)}`),
            setBookingSelectionNotice: (value) => events.push(`notice:${value}`),
        });

        expect(events).toEqual([
            'loading:true',
            'error:',
            'booking:null',
            'notice:',
        ]);
    });

    it('applies nearby search results', () => {
        const events: string[] = [];

        applyNearbySearchSuccessNow({
            setNearbyLoading: () => undefined,
            setNearbyError: () => undefined,
            setNearbyPlaces: (value) => events.push(`places:${value.length}`),
            setSelectedNearbyPlaceId: (value) => events.push(`selected:${value}`),
            setBookingResult: () => undefined,
            setBookingSelectionNotice: () => undefined,
        }, [{ id: 'p-1' } as any, { id: 'p-2' } as any]);

        expect(events).toEqual(['places:2', 'selected:p-1']);
    });

    it('applies nearby search failure state', () => {
        const events: string[] = [];

        applyNearbySearchFailureNow({
            setNearbyLoading: () => undefined,
            setNearbyError: (value) => events.push(`error:${value}`),
            setNearbyPlaces: (value) => events.push(`places:${value.length}`),
            setSelectedNearbyPlaceId: (value) => events.push(`selected:${value}`),
            setBookingResult: () => undefined,
            setBookingSelectionNotice: () => undefined,
        }, '주변검색 오류');

        expect(events).toEqual(['places:0', 'selected:', 'error:주변검색 오류']);
    });

    it('tracks booking request lifecycle', () => {
        const events: string[] = [];
        const deps = {
            setBookingLoading: (value: boolean) => events.push(`loading:${String(value)}`),
            setBookingError: (value: string) => events.push(`error:${value}`),
            setBookingResult: (value: any) => events.push(`result:${String(value?.confirmation_id ?? value)}`),
        };

        beginBookingRequestNow(deps);
        applyBookingRequestSuccessNow(deps, { confirmation_id: 'bk-1' } as any);
        applyBookingRequestFailureNow(deps, '예약 실패');
        finishBookingRequestNow(deps);

        expect(events).toEqual(['loading:true', 'error:', 'result:null', 'result:bk-1', 'error:예약 실패', 'loading:false']);
    });
});
