export type SorisaeMapPoint = {
    name?: string;
    display_label?: string;
    display_name?: string;
    map_url?: string | null;
};

export type SorisaeTransportScheduleOption = {
    provider_label?: string;
    route_label?: string;
    origin_stop?: string;
    destination_stop?: string;
    departure_local?: string;
    arrival_local?: string;
    trip_headsign?: string;
    source_url?: string;
};

export type SorisaeMapContext = {
    source?: string;
    origin?: SorisaeMapPoint | null;
    destination?: SorisaeMapPoint | null;
    origin_hubs?: SorisaeMapPoint[];
    destination_hubs?: SorisaeMapPoint[];
    transport_schedule_options?: SorisaeTransportScheduleOption[];
    transport_schedule_grounding?: string;
};

export type SorisaeQaEntry = {
    id: number;
    question: string;
    questionLang: string;
    answer: string;
    answerLang: string;
    atMs: number;
    mapContext?: SorisaeMapContext | null;
};
