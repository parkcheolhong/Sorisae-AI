import type { BookingResponse, NearbyPlace } from '../../app/appTypes';

export type NearbySearchControllerDeps = {
    setNearbyLoading: (value: boolean) => void;
    setNearbyError: (value: string) => void;
    setNearbyPlaces: (value: NearbyPlace[]) => void;
    setSelectedNearbyPlaceId: (value: string) => void;
    setBookingResult: (value: BookingResponse | null) => void;
    setBookingSelectionNotice: (value: string) => void;
};

export function beginNearbySearchNow(deps: NearbySearchControllerDeps): void {
    deps.setNearbyLoading(true);
    deps.setNearbyError('');
    deps.setBookingResult(null);
    deps.setBookingSelectionNotice('');
}

export function applyNearbySearchSuccessNow(deps: NearbySearchControllerDeps, places: NearbyPlace[]): void {
    deps.setNearbyPlaces(places);
    deps.setSelectedNearbyPlaceId(places[0]?.id || '');
}

export function applyNearbySearchFailureNow(deps: NearbySearchControllerDeps, message: string): void {
    deps.setNearbyPlaces([]);
    deps.setSelectedNearbyPlaceId('');
    deps.setNearbyError(message);
}

type BookingRequestControllerDeps = {
    setBookingLoading: (value: boolean) => void;
    setBookingError: (value: string) => void;
    setBookingResult: (value: BookingResponse | null) => void;
};

export function beginBookingRequestNow(deps: BookingRequestControllerDeps): void {
    deps.setBookingLoading(true);
    deps.setBookingError('');
    deps.setBookingResult(null);
}

export function applyBookingRequestFailureNow(deps: BookingRequestControllerDeps, message: string): void {
    deps.setBookingError(message);
}

export function applyBookingRequestSuccessNow(deps: BookingRequestControllerDeps, result: BookingResponse): void {
    deps.setBookingResult(result);
}

export function finishBookingRequestNow(deps: BookingRequestControllerDeps): void {
    deps.setBookingLoading(false);
}
