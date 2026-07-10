// [기능 분리 Phase5.4] 일반전화+예약(여행 예약) 기능 — 순수 데이터 타입.
// App.tsx 모놀리스에서 추출. 부작용/런타임 의존 없이 형상만 정의한다.

export type SearchCategory = 'all' | 'hotel' | 'airport' | 'restaurant' | 'attraction';

export type NearbyPlace = {
    id: string;
    category: 'hotel' | 'airport' | 'restaurant' | 'attraction';
    category_label: string;
    name: string;
    address: string;
    distance_m: number;
    rating: number;
    price_tier: string;
    booking_supported: boolean;
    phone: string;
    summary: string;
    latitude: number;
    longitude: number;
    google_maps_url: string;
};

export type BookingResponse = {
    confirmation_id: string;
    booking_message: string;
    translated_message: string;
    place_name: string;
    support_phone: string;
    google_maps_url: string;
};
