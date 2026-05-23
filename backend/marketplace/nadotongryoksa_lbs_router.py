from __future__ import annotations

import math
from typing import Any, Dict, List, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.nadotongryoksa.translator import NadoTranslator

PlaceCategory = Literal["hotel", "airport", "restaurant", "attraction"]
SearchCategory = Literal["all", "hotel", "airport", "restaurant", "attraction"]



_CATEGORY_LABELS: Dict[str, Dict[str, str]] = {
    "hotel": {"ko": "호텔", "en": "Hotel", "zh": "酒店", "zh-tw": "飯店", "ja": "ホテル", "es": "Hotel", "fr": "Hôtel", "de": "Hotel", "pt": "Hotel", "ru": "Отель", "ar": "فندق", "hi": "होटल", "it": "Hotel", "tr": "Otel", "vi": "Khách sạn", "th": "โรงแรม", "id": "Hotel", "ms": "Hotel", "nl": "Hotel", "pl": "Hotel", "uk": "Готель", "sv": "Hotell", "no": "Hotell", "da": "Hotel"},
    "airport": {"ko": "공항", "en": "Airport", "zh": "机场", "zh-tw": "機場", "ja": "空港", "es": "Aeropuerto", "fr": "Aéroport", "de": "Flughafen", "pt": "Aeroporto", "ru": "Аэропорт", "ar": "مطار", "hi": "हवाई अड्डा", "it": "Aeroporto", "tr": "Havalimanı", "vi": "Sân bay", "th": "สนามบิน", "id": "Bandara", "ms": "Lapangan Terbang", "nl": "Luchthaven", "pl": "Lotnisko", "uk": "Аеропорт", "sv": "Flygplats", "no": "Flyplass", "da": "Lufthavn"},
    "restaurant": {"ko": "식당", "en": "Restaurant", "zh": "餐厅", "zh-tw": "餐廳", "ja": "レストラン", "es": "Restaurante", "fr": "Restaurant", "de": "Restaurant", "pt": "Restaurante", "ru": "Ресторан", "ar": "مطعم", "hi": "रेस्टोरेंट", "it": "Ristorante", "tr": "Restoran", "vi": "Nhà hàng", "th": "ร้านอาหาร", "id": "Restoran", "ms": "Restoran", "nl": "Restaurant", "pl": "Restauracja", "uk": "Ресторан", "sv": "Restaurang", "no": "Restaurant", "da": "Restaurant"},
    "attraction": {"ko": "관광명소", "en": "Attraction", "zh": "景点", "zh-tw": "景點", "ja": "観光名所", "es": "Atracción", "fr": "Attraction", "de": "Sehenswürdigkeit", "pt": "Atração", "ru": "Достопримечательность", "ar": "معلم سياحي", "hi": "पर्यटन स्थल", "it": "Attrazione", "tr": "Gezi Noktası", "vi": "Điểm tham quan", "th": "สถานที่ท่องเที่ยว", "id": "Tempat Wisata", "ms": "Tarikan Pelancongan", "nl": "Attractie", "pl": "Atrakcja", "uk": "Пам'ятка", "sv": "Sevärdhet", "no": "Attraksjon", "da": "Attraktion"},
}


_BOOKING_MESSAGE_TEMPLATES: Dict[str, str] = {
    "ko": "예약 요청이 접수되었습니다. 현장 도착 전에 확인 메시지를 보여주세요.",
    "en": "Your reservation request has been received. Please show this confirmation before arrival.",
    "zh": "您的预订请求已收到。到达前请出示此确认信息。",
    "zh-tw": "您的預訂請求已收到。到達前請出示此確認信息。",
    "ja": "予約リクエストを受け付けました。到着前にこの確認画面を提示してください。",
    "es": "Su solicitud de reserva ha sido recibida. Muestre esta confirmación antes de llegar.",
    "fr": "Votre demande de réservation a été reçue. Montrez cette confirmation avant votre arrivée.",
    "de": "Ihre Reservierungsanfrage wurde empfangen. Bitte zeigen Sie diese Bestätigung vor der Ankunft vor.",
    "pt": "Sua solicitação de reserva foi recebida. Mostre esta confirmação antes de chegar.",
    "ru": "Ваш запрос на бронирование получен. Пожалуйста, покажите это подтверждение до прибытия.",
    "ar": "تم استلام طلب الحجز الخاص بك. يرجى إظهار هذا التأكيد قبل الوصول.",
    "hi": "आपका आरक्षण अनुरोध प्राप्त हो गया है। कृपया पहुंचने से पहले यह पुष्टि दिखाएं।",
    "it": "La richiesta di prenotazione è stata ricevuta. Mostri questa conferma prima dell'arrivo.",
    "tr": "Rezervasyon talebiniz alındı. Lütfen varmadan önce bu onayı gösterin.",
    "vi": "Yêu cầu đặt chỗ của bạn đã được nhận. Vui lòng xuất trình xác nhận này trước khi đến.",
    "th": "ได้รับคำขอจองของคุณแล้ว กรุณาแสดงการยืนยันนี้ก่อนเดินทางมาถึง",
    "id": "Permintaan reservasi Anda telah diterima. Tunjukkan konfirmasi ini sebelum tiba.",
    "ms": "Permintaan tempahan anda telah diterima. Sila tunjukkan pengesahan ini sebelum tiba.",
    "nl": "Uw reserveringsverzoek is ontvangen. Toon deze bevestiging voor aankomst.",
    "pl": "Twoja prośba o rezerwację została otrzymana. Proszę pokazać to potwierdzenie przed przybyciem.",
    "uk": "Ваш запит на бронювання отримано. Будь ласка, покажіть це підтвердження до прибуття.",
    "sv": "Din bokningsförfrågan har mottagits. Visa denna bekräftelse innan ankomst.",
    "no": "Din reservasjonsforespørsel er mottatt. Vis denne bekreftelsen før ankomst.",
    "da": "Din reservationsanmodning er modtaget. Vis denne bekræftelse inden ankomst.",
}


_POI_CATALOG: List[Dict[str, Any]] = [
    {"id": "hotel-lotte-seoul", "category": "hotel", "name": "롯데호텔 서울", "lat": 37.5657, "lon": 126.9819, "address": "서울 중구 을지로 30", "rating": 4.8, "price_tier": "₩₩₩₩", "booking_supported": True, "phone": "+82-2-771-1000", "summary": {"ko": "명동과 시청 사이에 있어 관광과 비즈니스 이동이 편리한 프리미엄 호텔입니다.", "en": "A premium hotel between Myeongdong and City Hall, convenient for sightseeing and business travel.", "zh": "位于明洞和市厅之间，适合旅游和商务出行的高端酒店。", "ja": "明洞と市庁の間にあり、観光とビジネス移動に便利なプレミアムホテルです。", "es": "Un hotel premium entre Myeongdong y City Hall, ideal para turismo y viajes de negocios.", "fr": "Un hotel haut de gamme entre Myeongdong et l'hotel de ville, pratique pour les deplacements.", "de": "Ein Premium-Hotel zwischen Myeongdong und Rathaus, praktisch fur Tourismus und Geschaftsreisen.", "pt": "Um hotel premium entre Myeongdong e City Hall, pratico para turismo e negocios.", "ru": "Премиальный отель между Мендоном и мэрией, удобный для туризма и деловых поездок.", "ar": "فندق فاخر بين ميونغ دونغ وقاعة المدينة ومناسب للسياحة والاعمال.", "hi": "म्योंगडोंग और सिटी हॉल के बीच स्थित प्रीमियम होटल, पर्यटन और व्यापार यात्रा दोनों के लिए सुविधाजनक।", "it": "Un hotel premium tra Myeongdong e City Hall, comodo per turismo e viaggi di lavoro.", "tr": "Myeongdong ile Belediye Sarayi arasinda, gezi ve is seyahati icin uygun premium otel."}, "amenities": ["체크인 15:00", "공항 리무진", "영어 응대"], "review_query": "롯데호텔 서울"},
    {"id": "hotel-fourpoints-myeongdong", "category": "hotel", "name": "포포인츠 바이 쉐라톤 명동", "lat": 37.5662, "lon": 126.9912, "address": "서울 중구 저동2가 82-1", "rating": 4.5, "price_tier": "₩₩₩", "booking_supported": True, "phone": "+82-2-6466-6000", "summary": {"ko": "을지로입구와 명동 상권 접근성이 좋아 짧은 도심 체류에 적합한 호텔입니다.", "en": "A hotel suited for short city stays with quick access to Euljiro and Myeongdong shopping areas.", "zh": "靠近乙支路和明洞商圈，适合短期市区住宿的酒店。", "ja": "乙支路と明洞エリアへのアクセスが良く、短期滞在に向いたホテルです。", "es": "Hotel ideal para estancias cortas con acceso rapido a Euljiro y Myeongdong.", "fr": "Hotel adapte aux courts sejours avec acces rapide a Euljiro et Myeongdong.", "de": "Ein Hotel fur kurze Stadtaufenthalte mit schnellem Zugang zu Euljiro und Myeongdong.", "pt": "Hotel ideal para estadias curtas com facil acesso a Euljiro e Myeongdong.", "ru": "Отель для короткого пребывания в центре с быстрым доступом к Ыльчиро и Мендону.", "ar": "فندق مناسب للاقامات القصيرة مع وصول سريع الى يولجيرو وميونغ دونغ.", "hi": "छोटे शहर प्रवास के लिए उपयुक्त होटल, उल्जिरो और म्योंगडोंग तक आसान पहुंच।", "it": "Hotel adatto a soggiorni brevi con accesso rapido a Euljiro e Myeongdong.", "tr": "Euljiro ve Myeongdong'a hizli erisim sunan, kisa sehir konaklamalari icin uygun otel."}, "amenities": ["체크인 15:00", "셀프 체크인", "피트니스"], "review_query": "포포인츠 바이 쉐라톤 명동"},
    {"id": "airport-icn-t1", "category": "airport", "name": "인천국제공항 제1터미널", "lat": 37.4602, "lon": 126.4407, "address": "인천 중구 공항로 272", "rating": 4.7, "price_tier": "교통", "booking_supported": False, "phone": "+82-1577-2600", "summary": {"ko": "국제선 주요 허브로 공항철도, 리무진, 환승 서비스가 잘 연결된 터미널입니다.", "en": "A major international hub terminal with airport rail, limousine buses, and transfer services.", "zh": "国际航线主要枢纽航站楼，机场铁路、巴士和转机服务完善。", "ja": "国際線の主要ハブで、空港鉄道とリムジン、乗り継ぎ導線が整ったターミナルです。", "es": "Una terminal internacional con tren del aeropuerto, autobuses y servicios de conexion.", "fr": "Un terminal international majeur avec train aeroportuaire, bus limousine et services de transit.", "de": "Ein grosses internationales Terminal mit Flughafenbahn, Limousinenbussen und Transferdiensten.", "pt": "Terminal internacional com trem do aeroporto, onibus limousine e servicos de conexao.", "ru": "Крупный международный терминал с аэроэкспрессом, автобусами и удобными пересадками.", "ar": "مبنى رئيسي للرحلات الدولية مع قطار المطار والحافلات وخدمات التحويل.", "hi": "अंतरराष्ट्रीय हब टर्मिनल, जहां एयरपोर्ट रेल, लिमोजिन बस और ट्रांसफर सेवाएं उपलब्ध हैं।", "it": "Un grande terminal internazionale con treno aeroportuale, bus limousine e servizi di transito.", "tr": "Havaalani treni, otobusler ve transfer hizmetleri olan buyuk bir uluslararasi terminal."}, "amenities": ["환전", "면세점", "24시간 안내"], "review_query": "인천국제공항 제1터미널"},
    {"id": "airport-gmp", "category": "airport", "name": "김포국제공항", "lat": 37.5583, "lon": 126.7906, "address": "서울 강서구 하늘길 112", "rating": 4.3, "price_tier": "교통", "booking_supported": False, "phone": "+82-1661-2626", "summary": {"ko": "서울 도심 접근성이 좋아 국내선과 일본, 중국 단거리 국제선 이동에 편리합니다.", "en": "Convenient for domestic and short-haul international flights thanks to quick access to central Seoul.", "zh": "由于靠近首尔市区，适合国内线及日本、中国等短程国际航线。", "ja": "都心アクセスが良く、国内線や日本・中国向け近距離国際線に便利です。", "es": "Conveniente para vuelos nacionales e internacionales de corta distancia por su acceso a Seul.", "fr": "Pratique pour les vols interieurs et internationaux de courte distance grace a son acces a Seoul.", "de": "Praktisch fur Inlands- und Kurzstreckenfluge durch den schnellen Zugang zur Innenstadt von Seoul.", "pt": "Conveniente para voos domesticos e internacionais curtos por causa do acesso rapido a Seul.", "ru": "Удобен для внутренних и коротких международных рейсов благодаря быстрому доступу к центру Сеула.", "ar": "مناسب للرحلات الداخلية والدولية القصيرة بسبب سهولة الوصول الى وسط سيول.", "hi": "सियोल शहर तक तेज पहुंच के कारण घरेलू और लघु अंतरराष्ट्रीय उड़ानों के लिए सुविधाजनक।", "it": "Comodo per voli nazionali e internazionali a corto raggio grazie al rapido accesso a Seoul.", "tr": "Seul merkezine hizli ulasim sayesinde ic hat ve kisa uluslararasi ucuslar icin uygundur."}, "amenities": ["지하철 연결", "렌터카", "국내선 환승"], "review_query": "김포국제공항"},
    {"id": "restaurant-myeongdong-kalguksu", "category": "restaurant", "name": "명동교자 본점", "lat": 37.5635, "lon": 126.9854, "address": "서울 중구 명동10길 29", "rating": 4.6, "price_tier": "₩₩", "booking_supported": False, "phone": "+82-2-776-5348", "summary": {"ko": "칼국수와 만두로 유명한 명동 대표 식당으로 빠른 식사와 관광 동선에 좋습니다.", "en": "A famous Myeongdong spot for noodle soup and dumplings, ideal for quick meals between sightseeing stops.", "zh": "以刀切面和饺子闻名的明洞代表餐厅，适合旅游途中快速用餐。", "ja": "カルグクスと餃子で有名な明洞の定番店で、観光の合間の食事に向いています。", "es": "Un restaurante emblematico de Myeongdong famoso por sus fideos y dumplings.", "fr": "Un restaurant celebre de Myeongdong connu pour ses nouilles et raviolis.", "de": "Ein bekanntes Restaurant in Myeongdong fur Nudelsuppe und Mandu.", "pt": "Restaurante famoso em Myeongdong por macarrao e bolinhos.", "ru": "Знаменитый ресторан Мендона, известный лапшой и пельменями.", "ar": "مطعم مشهور في ميونغ دونغ معروف بحساء المعكرونة ودمبلنغ.", "hi": "म्योंगडोंग का प्रसिद्ध रेस्तरां, नूडल सूप और पकौड़ी के लिए जाना जाता है।", "it": "Un ristorante famoso di Myeongdong noto per noodle soup e ravioli.", "tr": "Myeongdong'da eriste corbasi ve manti ile unlu restoran."}, "amenities": ["현금/카드", "빠른 회전", "영문 메뉴"], "review_query": "명동교자 본점"},
    {"id": "restaurant-gwangjang-bindaetteok", "category": "restaurant", "name": "광장시장 순희네 빈대떡", "lat": 37.5704, "lon": 126.9992, "address": "서울 종로구 창경궁로 88", "rating": 4.4, "price_tier": "₩", "booking_supported": False, "phone": "+82-2-2267-0611", "summary": {"ko": "광장시장 대표 먹거리 구역으로 전통 전과 막걸리를 현지 분위기에서 즐길 수 있습니다.", "en": "A signature food stall area in Gwangjang Market for Korean pancakes and makgeolli in a lively local setting.", "zh": "广藏市场代表性美食摊位，可在当地氛围中享用韩式煎饼和米酒。", "ja": "広蔵市場を代表する屋台で、チヂミとマッコリをローカルな雰囲気で楽しめます。", "es": "Puesto emblematico del mercado Gwangjang para probar jeon y makgeolli en ambiente local.", "fr": "Stand emblematique du marche de Gwangjang pour deguster des jeon et du makgeolli.", "de": "Ein bekannter Stand im Gwangjang-Markt fur koreanische Pfannkuchen und Makgeolli.", "pt": "Barraca famosa no mercado Gwangjang para provar jeon e makgeolli.", "ru": "Знаковая точка рынка Кванджан для корейских оладий и макколи.", "ar": "ركن طعام شهير في سوق غوانغجانغ لتجربة الفطائر الكورية والماكغولي.", "hi": "ग्वांगजांग मार्केट का प्रसिद्ध स्टॉल, जहां कोरियाई पैनकेक और मक्कोली का आनंद लिया जा सकता है।", "it": "Chiosco simbolo del mercato Gwangjang per assaggiare jeon e makgeolli.", "tr": "Gwangjang Pazari'nda Kore pankeki ve makgeolli icin unlu bir durak."}, "amenities": ["시장 먹거리", "현장 결제", "사진 명소"], "review_query": "광장시장 순희네 빈대떡"},
    {"id": "attraction-gyeongbokgung", "category": "attraction", "name": "경복궁", "lat": 37.5796, "lon": 126.9770, "address": "서울 종로구 사직로 161", "rating": 4.8, "price_tier": "입장권", "booking_supported": False, "phone": "+82-2-3700-3900", "summary": {"ko": "조선 왕조의 대표 궁궐로 수문장 교대식과 한복 체험 동선이 잘 갖춰져 있습니다.", "en": "The signature Joseon palace with royal guard ceremonies and strong hanbok photo opportunities.", "zh": "朝鲜王朝代表宫殿，可观看守门将换岗仪式并体验韩服拍照。", "ja": "朝鮮王朝を代表する宮殿で、守門将交代式と韓服体験に向いています。", "es": "El palacio mas representativo de Joseon, con ceremonia de guardia y experiencia con hanbok.", "fr": "Le palais emblematique de Joseon avec releve de la garde et experience hanbok.", "de": "Der bekannteste Joseon-Palast mit Wachwechsel und Hanbok-Erlebnis.", "pt": "O palacio simbolo de Joseon com troca da guarda e experiencia com hanbok.", "ru": "Главный дворец эпохи Чосон с церемонией смены караула и фотосессиями в ханбоке.", "ar": "القصر الاشهر من عهد جوسون مع مراسم تبديل الحرس وتجربة الهانبوك.", "hi": "जोसेन राजवंश का प्रमुख महल, जहां गार्ड परिवर्तन समारोह और हानबोक अनुभव उपलब्ध है।", "it": "Il palazzo simbolo della dinastia Joseon con cambio della guardia ed esperienza hanbok.", "tr": "Joseon doneminin simge sarayi; nobet degisimi ve hanbok deneyimi icin idealdir."}, "amenities": ["궁궐 투어", "한복 입장", "사진 명소"], "review_query": "경복궁"},
    {"id": "attraction-nseoultower", "category": "attraction", "name": "N서울타워", "lat": 37.5512, "lon": 126.9882, "address": "서울 용산구 남산공원길 105", "rating": 4.5, "price_tier": "입장권", "booking_supported": False, "phone": "+82-2-3455-9277", "summary": {"ko": "서울 전경을 한눈에 볼 수 있는 전망 명소로 야간 방문과 케이블카 이동이 인기가 높습니다.", "en": "A skyline attraction for panoramic Seoul views, popular for evening visits and cable car access.", "zh": "可俯瞰首尔全景的观景名所，夜景和缆车路线很受欢迎。", "ja": "ソウル全景を見渡せる展望スポットで、夜景とケーブルカー利用が人気です。", "es": "Mirador panoramico de Seul, famoso por las visitas nocturnas y el teleferico.", "fr": "Un site panoramique sur Seoul, populaire le soir et accessible en telepherique.", "de": "Ein Aussichtspunkt mit Panoramablick auf Seoul, beliebt fur Abendbesuche und Seilbahn.", "pt": "Mirante panoramico de Seul, popular a noite e com acesso por teleferico.", "ru": "Панорамная достопримечательность с видом на Сеул, популярная вечером и с канатной дорогой.", "ar": "معلم بانورامي يطل على سيول ويشتهر بالزيارات الليلية والتلفريك.", "hi": "सियोल का पैनोरमिक दृश्य देने वाला आकर्षण, शाम की यात्रा और केबल कार के लिए प्रसिद्ध।", "it": "Attrazione panoramica su Seoul, popolare per le visite serali e la funivia.", "tr": "Seul'u panoramik goren bir cazibe noktasi; aksam ziyaretleri ve teleferik ile populer."}, "amenities": ["야경", "케이블카", "전망대"], "review_query": "N서울타워"},
]


class NearbyPlaceResponse(BaseModel):
    id: str
    category: PlaceCategory
    category_label: str
    name: str
    address: str
    distance_m: int
    rating: float
    price_tier: str
    booking_supported: bool
    phone: str
    summary: str
    amenities: List[str]
    latitude: float
    longitude: float
    google_maps_url: str
    naver_map_url: str
    review_query: str
    maps_reviews_path: str


class NearbySearchResponse(BaseModel):
    status: Literal["ok"] = "ok"
    source: str = "nadotongryoksa-lbs"
    target_lang: str
    requested_category: SearchCategory
    radius_m: int
    total: int
    places: List[NearbyPlaceResponse]


class BookingRequest(BaseModel):
    place_id: str
    customer_name: str = Field(min_length=1, max_length=80)
    checkin_date: str = Field(min_length=4, max_length=20)
    checkout_date: str = Field(min_length=4, max_length=20)
    guests: int = Field(default=1, ge=1, le=8)
    room_count: int = Field(default=1, ge=1, le=4)
    note: str = Field(default="", max_length=240)
    target_lang: str = Field(default="ko", min_length=2, max_length=5)


class BookingResponse(BaseModel):
    status: Literal["ok"] = "ok"
    confirmation_id: str
    place_id: str
    place_name: str
    customer_name: str
    checkin_date: str
    checkout_date: str
    guests: int
    room_count: int
    booking_message: str
    translated_message: str
    support_phone: str
    google_maps_url: str


_SUPPORTED_LANGS = {
    "ko", "en", "zh", "zh-tw", "ja", "es", "fr", "de", "pt", "ru",
    "ar", "hi", "it", "tr", "vi", "th", "id", "ms", "nl", "pl",
    "uk", "sv", "no", "da",
}


def _normalize_lang(lang: str) -> str:
    value = (lang or "ko").strip().lower()
    return value if value in _SUPPORTED_LANGS else "en"


def _translate_value(values: Dict[str, str], target_lang: str) -> str:
    normalized = _normalize_lang(target_lang)
    return values.get(normalized) or values.get("en") or next(iter(values.values()))


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(radius_km * c * 1000)


def _build_map_links(name: str, lat: float, lon: float) -> Dict[str, str]:
    encoded_name = name.replace(" ", "+")
    return {
        "google": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}&query_place_id={encoded_name}",
        "naver": f"https://map.naver.com/p/search/{encoded_name}",
    }


def _to_nearby_response(place: Dict[str, Any], *, target_lang: str, distance_m: int) -> NearbyPlaceResponse:
    links = _build_map_links(place["name"], place["lat"], place["lon"])
    category = str(place["category"])
    return NearbyPlaceResponse(
        id=str(place["id"]),
        category=category,  # type: ignore[arg-type]
        category_label=_translate_value(_CATEGORY_LABELS[category], target_lang),
        name=str(place["name"]),
        address=str(place["address"]),
        distance_m=distance_m,
        rating=float(place["rating"]),
        price_tier=str(place["price_tier"]),
        booking_supported=bool(place["booking_supported"]),
        phone=str(place["phone"]),
        summary=_translate_value(place["summary"], target_lang),
        amenities=list(place["amenities"]),
        latitude=float(place["lat"]),
        longitude=float(place["lon"]),
        google_maps_url=links["google"],
        naver_map_url=links["naver"],
        review_query=str(place["review_query"]),
        maps_reviews_path=f"/api/external-search/maps-reviews?q={place['review_query']}",
    )


def _filter_places(*, lat: float, lon: float, category: SearchCategory, radius_m: int, limit: int, target_lang: str) -> List[NearbyPlaceResponse]:
    candidates: List[tuple[int, Dict[str, Any]]] = []
    for place in _POI_CATALOG:
        if category != "all" and place["category"] != category:
            continue
        distance_m = _haversine_distance_m(lat, lon, float(place["lat"]), float(place["lon"]))
        if distance_m <= radius_m:
            candidates.append((distance_m, place))
    candidates.sort(key=lambda item: (item[0], -float(item[1]["rating"])))
    return [_to_nearby_response(place, target_lang=target_lang, distance_m=distance) for distance, place in candidates[:limit]]


def build_nadotongryoksa_lbs_router(contract: Any) -> APIRouter:
    router = APIRouter(prefix="/nadotongryoksa/lbs", tags=["marketplace-nadotongryoksa-lbs"])

    @router.get("/nearby", response_model=NearbySearchResponse)
    def nearby_places(
        lat: float = Query(..., ge=-90, le=90),
        lon: float = Query(..., ge=-180, le=180),
        category: SearchCategory = Query("all"),
        radius_m: int = Query(5000, ge=300, le=50000),
        limit: int = Query(8, ge=1, le=20),
        target_lang: str = Query("ko"),
    ) -> NearbySearchResponse:
        normalized_lang = _normalize_lang(target_lang)
        filtered = _filter_places(lat=lat, lon=lon, category=category, radius_m=radius_m, limit=limit, target_lang=normalized_lang)
        return NearbySearchResponse(target_lang=normalized_lang, requested_category=category, radius_m=radius_m, total=len(filtered), places=filtered)

    @router.post("/bookings", response_model=BookingResponse)
    def create_booking(payload: BookingRequest, current_user=Depends(contract.get_current_user)) -> BookingResponse:
        _ = current_user
        target_lang = _normalize_lang(payload.target_lang)
        place = next((item for item in _POI_CATALOG if item["id"] == payload.place_id), None)
        if not place:
            raise HTTPException(status_code=404, detail="place_id not found")
        if place["category"] != "hotel" or not place["booking_supported"]:
            raise HTTPException(status_code=400, detail="예약은 호텔 카테고리에서만 지원됩니다.")

        translator = NadoTranslator.get_instance()
        translated_message = _BOOKING_MESSAGE_TEMPLATES.get(target_lang) or _BOOKING_MESSAGE_TEMPLATES["en"]
        if target_lang != "ko":
            try:
                probe = translator.translate("감사합니다", "ko", target_lang)
                if probe and probe != "감사합니다":
                    translated_message = f"{translated_message} {probe}"
            except Exception:
                pass

        links = _build_map_links(str(place["name"]), float(place["lat"]), float(place["lon"]))
        return BookingResponse(
            confirmation_id=f"NADO-{uuid4().hex[:10].upper()}",
            place_id=str(place["id"]),
            place_name=str(place["name"]),
            customer_name=payload.customer_name,
            checkin_date=payload.checkin_date,
            checkout_date=payload.checkout_date,
            guests=payload.guests,
            room_count=payload.room_count,
            booking_message=(f"{payload.customer_name}님의 예약 요청이 접수되었습니다. {payload.checkin_date} 체크인, {payload.checkout_date} 체크아웃, {payload.guests}명 / 객실 {payload.room_count}개 기준입니다."),
            translated_message=translated_message,
            support_phone=str(place["phone"]),
            google_maps_url=links["google"],
        )

    return router