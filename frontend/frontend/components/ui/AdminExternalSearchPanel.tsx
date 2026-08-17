'use client';

export type AdminExternalSearchEndpoint = 'news' | 'maps-reviews' | 'youtube' | 'trends' | 'shopping';

export interface AdminExternalSearchItem {
    title: string;
    url?: string | null;
    snippet?: string;
    source?: string | null;
    published_at?: string | null;
    thumbnail?: string | null;
    rating?: number | null;
    reviews_count?: number | null;
    price?: string | null;
    channel?: string | null;
    extra?: Record<string, unknown>;
}

export interface AdminExternalSearchResponse {
    status: 'ok' | 'error';
    endpoint: string;
    data: AdminExternalSearchItem[];
    meta?: {
        provider: string;
        engine: string;
        query: string;
        total_items: number;
        elapsed_ms: number;
        request_id: string;
    } | null;
    error?: {
        code: string;
        message: string;
        retryable: boolean;
        http_status: number;
        details?: Record<string, unknown>;
    } | null;
}

interface AdminExternalSearchPanelProps {
    endpoint: AdminExternalSearchEndpoint;
    query: string;
    placeId: string;
    loading: boolean;
    message: string;
    result: AdminExternalSearchResponse | null;
    onChangeEndpoint: (value: AdminExternalSearchEndpoint) => void;
    onChangeQuery: (value: string) => void;
    onChangePlaceId: (value: string) => void;
    onRun: () => Promise<void>;
}

const ENDPOINT_OPTIONS: Array<{ value: AdminExternalSearchEndpoint; label: string; description: string }> = [
    { value: 'news', label: '뉴스', description: '최신 기사/헤드라인 확인' },
    { value: 'maps-reviews', label: '지도 리뷰', description: '장소 검색 또는 place_id 상세 리뷰' },
    { value: 'youtube', label: '유튜브', description: '영상 검색 결과 확인' },
    { value: 'trends', label: '트렌드', description: '검색 관심도 흐름 확인' },
    { value: 'shopping', label: '쇼핑', description: '상품 검색 결과 확인' },
];

export default function AdminExternalSearchPanel({
    endpoint,
    query,
    placeId,
    loading,
    message,
    result,
    onChangeEndpoint,
    onChangeQuery,
    onChangePlaceId,
    onRun,
}: AdminExternalSearchPanelProps) {
    const selectedOption = ENDPOINT_OPTIONS.find((item) => item.value === endpoint) || ENDPOINT_OPTIONS[0];

    return (
        <div className="mb-3 rounded-xl border border-[#2b3548] bg-[radial-gradient(circle_at_top_left,_rgba(43,108,176,0.22),_rgba(11,18,32,0.96)_58%)] p-4 text-sm text-[#dbe7f5]">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-[#f8fbff]">외부 검색 즉시 호출</p>
                    <p className="mt-1 text-xs text-[#9fb3c8]">관리자 패널에서 우선순위 5개 API를 즉시 호출해 표준 스키마 결과를 확인합니다.</p>
                </div>
                <div className="rounded-full border border-[#4a6a8e] px-3 py-1 text-[11px] font-semibold text-[#9ecbff]">
                    Bing 이미지/비디오는 백엔드 확장 완료
                </div>
            </div>

            <div className="mt-4 grid gap-3 xl:grid-cols-[1.6fr_1fr]">
                <div className="rounded-xl border border-[#304057] bg-[#0b1220]/80 p-3">
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                        {ENDPOINT_OPTIONS.map((item) => {
                            const active = item.value === endpoint;
                            return (
                                <button
                                    key={item.value}
                                    type="button"
                                    onClick={() => onChangeEndpoint(item.value)}
                                    className={`rounded-xl border px-3 py-3 text-left transition ${active ? 'border-[#79c0ff] bg-[#11243d] text-[#f8fbff]' : 'border-[#2b3548] bg-[#0f1726] text-[#9fb3c8]'}`}
                                >
                                    <p className="text-xs font-semibold">{item.label}</p>
                                    <p className="mt-1 text-[11px] leading-4">{item.description}</p>
                                </button>
                            );
                        })}
                    </div>

                    <div className="mt-3 grid gap-3 lg:grid-cols-[1.5fr_1fr_auto]">
                        <label htmlFor="admin-external-search-query" className="space-y-2 text-xs text-[#9fb3c8]">
                            <span className="block font-semibold text-[#dbe7f5]">검색어</span>
                            <input
                                id="admin-external-search-query"
                                name="external_search_query"
                                value={query}
                                onChange={(event) => onChangeQuery(event.target.value)}
                                placeholder={endpoint === 'maps-reviews' ? '예: 스타벅스 강남 or 비워두고 place_id만 사용' : `예: ${selectedOption.label} 검색어`}
                                className="w-full rounded-lg border border-[#35506c] bg-[#08111d] px-3 py-2 text-sm text-[#f8fbff] placeholder:text-[#60758f]"
                            />
                        </label>
                        <label htmlFor="admin-external-search-place-id" className={`space-y-2 text-xs text-[#9fb3c8] ${endpoint === 'maps-reviews' ? '' : 'opacity-60'}`}>
                            <span className="block font-semibold text-[#dbe7f5]">place_id</span>
                            <input
                                id="admin-external-search-place-id"
                                name="external_search_place_id"
                                value={placeId}
                                onChange={(event) => onChangePlaceId(event.target.value)}
                                disabled={endpoint !== 'maps-reviews'}
                                placeholder="Google Maps place_id"
                                className="w-full rounded-lg border border-[#35506c] bg-[#08111d] px-3 py-2 text-sm text-[#f8fbff] placeholder:text-[#60758f] disabled:cursor-not-allowed disabled:opacity-60"
                            />
                        </label>
                        <button
                            type="button"
                            onClick={() => {
                                void onRun();
                            }}
                            disabled={loading}
                            className="h-fit rounded-xl bg-[#2f6f99] px-4 py-3 text-sm font-semibold text-[#041018] disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {loading ? '호출 중...' : '즉시 호출'}
                        </button>
                    </div>
                    {message && <p className="mt-3 rounded-lg border border-[#35506c] bg-[#0f1726] px-3 py-2 text-xs text-[#9ecbff]">{message}</p>}
                </div>

                <div className="rounded-xl border border-[#304057] bg-[#0b1220]/80 p-3 text-xs text-[#9fb3c8]">
                    <p className="font-semibold text-[#f8fbff]">최근 결과 메타</p>
                    <div className="mt-2 space-y-1">
                        <p>endpoint: {result?.endpoint || '-'}</p>
                        <p>provider: {result?.meta?.provider || '-'}</p>
                        <p>engine: {result?.meta?.engine || '-'}</p>
                        <p>items: {result?.meta?.total_items ?? result?.data?.length ?? 0}</p>
                        <p>elapsed_ms: {result?.meta?.elapsed_ms ?? '-'}</p>
                    </div>
                    {result?.error && (
                        <div className="mt-3 rounded-lg border border-[#8b2d2d] bg-[#2a1414] px-3 py-2 text-[#ffb4b4]">
                            <p className="font-semibold">{result.error.code}</p>
                            <p className="mt-1">{result.error.message}</p>
                        </div>
                    )}
                </div>
            </div>

            {result && result.data.length > 0 && (
                <div className="mt-4 grid gap-3 xl:grid-cols-2">
                    {result.data.map((item, index) => (
                        <div key={`${item.title}-${index}`} className="rounded-xl border border-[#304057] bg-[#0b1220]/80 p-3">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <p className="text-sm font-semibold text-[#f8fbff]">{item.title}</p>
                                    <p className="mt-1 text-[11px] text-[#9ecbff]">{item.source || item.channel || '-'}</p>
                                </div>
                                {typeof item.rating === 'number' && <span className="rounded-full border border-[#a98030] px-2 py-1 text-[10px] font-semibold text-[#f2cc60]">rating {item.rating}</span>}
                            </div>
                            {item.snippet && <p className="mt-2 text-xs leading-5 text-[#c8d5e4]">{item.snippet}</p>}
                            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-[#8ea3b9]">
                                {item.published_at && <span className="rounded-full border border-[#2b3548] px-2 py-1">{item.published_at}</span>}
                                {typeof item.reviews_count === 'number' && <span className="rounded-full border border-[#2b3548] px-2 py-1">reviews {item.reviews_count}</span>}
                                {item.price && <span className="rounded-full border border-[#2b3548] px-2 py-1">{item.price}</span>}
                            </div>
                            {item.url && (
                                <a href={item.url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs text-[#79c0ff] underline">
                                    {item.url}
                                </a>
                            )}
                            {item.extra && Object.keys(item.extra).length > 0 && (
                                <pre className="mt-3 overflow-x-auto rounded-lg border border-[#243446] bg-[#08111d] p-2 text-[11px] text-[#8ea3b9]">
                                    {JSON.stringify(item.extra, null, 2)}
                                </pre>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}