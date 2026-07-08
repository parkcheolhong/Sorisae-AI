from __future__ import annotations

import json as _json
import logging
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.marketplace import models as marketplace_models
from backend.marketplace.database import get_db
from backend.security_gates import require_lbs_search_quota
from backend.services.nadotongryoksa.translator import NadoTranslator

logger = logging.getLogger(__name__)

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
    recommendation_id: Optional[int] = None
    partner_id: Optional[str] = None


class NearbySearchResponse(BaseModel):
    status: Literal["ok"] = "ok"
    source: str = "nadotongryoksa-lbs"
    target_lang: str
    requested_category: SearchCategory
    radius_m: int
    total: int
    places: List[NearbyPlaceResponse]
    trip_session_id: Optional[str] = None


class BookingRequest(BaseModel):
    place_id: str
    customer_name: str = Field(min_length=1, max_length=80)
    checkin_date: str = Field(min_length=4, max_length=20)
    checkout_date: str = Field(min_length=4, max_length=20)
    guests: int = Field(default=1, ge=1, le=8)
    room_count: int = Field(default=1, ge=1, le=4)
    note: str = Field(default="", max_length=240)
    target_lang: str = Field(default="ko", min_length=2, max_length=5)
    partner_click_ref: Optional[str] = Field(default=None, max_length=120)
    partner_click_event_id: Optional[int] = Field(default=None, ge=1)


class PartnerClickRequest(BaseModel):
    recommendation_id: Optional[int] = Field(default=None, ge=1)
    partner_id: Optional[str] = Field(default=None, max_length=80)
    landing_url: Optional[str] = Field(default=None, max_length=500)
    trip_session_id: Optional[str] = Field(default=None, max_length=64)


class PartnerClickResponse(BaseModel):
    status: Literal["ok"] = "ok"
    click_ref: str
    partner_id: str
    recommendation_id: Optional[int] = None
    click_event_id: Optional[int] = None


class BookingLifecycleRequest(BaseModel):
    booking_ref: str = Field(min_length=6, max_length=120)
    status_note: str = Field(default="", max_length=240)


class BookingLifecycleResponse(BaseModel):
    status: Literal["ok"] = "ok"
    booking_ref: str
    booking_event_id: Optional[int] = None
    stage: Literal["initiated", "confirmed", "completed"]
    partner_id: str


class BookingCancelRefundRequest(BaseModel):
    booking_ref: str = Field(min_length=6, max_length=120)
    reason: str = Field(default="", max_length=240)
    refund_amount: Optional[float] = Field(default=None, ge=0.0)


class BookingCancelRefundResponse(BaseModel):
    status: Literal["ok"] = "ok"
    booking_ref: str
    booking_event_id: Optional[int] = None
    stage: Literal["cancelled", "refunded"]
    partner_id: str
    ledger_adjusted: bool = False
    adjustment_amount: float = 0.0
    currency: str = "USD"


class CommissionSettlementBatchRequest(BaseModel):
    dry_run: bool = True
    limit: int = Field(default=100, ge=1, le=500)
    default_commission_amount: float = Field(default=12.0, ge=0.0)
    commission_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    currency: str = Field(default="USD", min_length=3, max_length=10)


class CommissionSettlementItem(BaseModel):
    booking_ref: str
    booking_event_id: Optional[int] = None
    partner_id: str
    amount: float
    currency: str
    settlement_status: str


class CommissionSettlementBatchResponse(BaseModel):
    status: Literal["ok"] = "ok"
    dry_run: bool
    scanned: int
    created: int
    skipped_existing: int
    total_amount: float
    currency: str
    items: List[CommissionSettlementItem]


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


_BOOKING_EVENT_FALLBACK: Dict[str, Dict[str, Any]] = {}
_SETTLEMENT_LEDGER_FALLBACK: Dict[str, Dict[str, Any]] = {}


def _db_ready(db: Any) -> bool:
    return all(hasattr(db, attr) for attr in ("add", "commit", "rollback"))


def _partner_id_for_place(place: NearbyPlaceResponse) -> str:
    return f"partner-{place.category}-default"


def _ensure_trip_session(
    db: Any,
    *,
    requested_session_id: Optional[str],
    user_id: Optional[int],
    lat: float,
    lon: float,
) -> tuple[Optional[int], str]:
    session_id = (requested_session_id or "").strip() or f"trip-{uuid4().hex[:16]}"
    if not _db_ready(db):
        return None, session_id
    try:
        existing = db.query(marketplace_models.TripSession).filter(
            marketplace_models.TripSession.session_id == session_id,
        ).first()
        if existing is not None:
            return int(existing.id), session_id
        session = marketplace_models.TripSession(
            session_id=session_id,
            user_id=user_id,
            status="active",
            context_json=_json.dumps({"lat": lat, "lon": lon}, ensure_ascii=False),
        )
        db.add(session)
        db.flush()
        db.commit()
        return int(session.id), session_id
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None, session_id


def _record_recommendation_events(
    db: Any,
    *,
    trip_session_pk: Optional[int],
    user_id: Optional[int],
    places: List[NearbyPlaceResponse],
) -> None:
    if not _db_ready(db):
        return
    try:
        for rank, place in enumerate(places, start=1):
            partner_id = _partner_id_for_place(place)
            event = marketplace_models.RecommendationEvent(
                trip_session_id=trip_session_pk,
                user_id=user_id,
                category=place.category,
                partner_id=partner_id,
                recommendation_rank=rank,
                recommendation_payload_json=_json.dumps(
                    {
                        "place_id": place.id,
                        "place_name": place.name,
                        "distance_m": place.distance_m,
                    },
                    ensure_ascii=False,
                ),
            )
            db.add(event)
            db.flush()
            place.recommendation_id = int(event.id)
            place.partner_id = partner_id
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def _create_booking_event(
    db: Any,
    *,
    booking_ref: str,
    user_id: Optional[int],
    partner_id: str,
    partner_click_event_id: Optional[int],
    payload: Dict[str, Any],
) -> Optional[int]:
    _BOOKING_EVENT_FALLBACK[booking_ref] = {
        "status": "initiated",
        "partner_id": partner_id,
        "payload": payload,
    }
    if not _db_ready(db):
        return None
    try:
        event = marketplace_models.BookingEvent(
            booking_ref=booking_ref,
            user_id=user_id,
            partner_id=partner_id,
            partner_click_event_id=partner_click_event_id,
            status="initiated",
            raw_payload_json=_json.dumps(payload, ensure_ascii=False),
        )
        db.add(event)
        db.flush()
        db.commit()
        return int(event.id)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _advance_booking_stage(db: Any, booking_ref: str, stage: Literal["confirmed", "completed"], note: str) -> tuple[Optional[int], str]:
    current = _BOOKING_EVENT_FALLBACK.get(booking_ref) or {"status": "initiated", "partner_id": "partner-hotel-default"}
    current["status"] = stage
    if note:
        current["status_note"] = note
    _BOOKING_EVENT_FALLBACK[booking_ref] = current

    if not _db_ready(db):
        return None, str(current.get("partner_id") or "partner-hotel-default")

    try:
        event = db.query(marketplace_models.BookingEvent).filter(
            marketplace_models.BookingEvent.booking_ref == booking_ref,
        ).first()
        if event is None:
            return None, str(current.get("partner_id") or "partner-hotel-default")
        event.status = stage
        payload = _json.loads(event.raw_payload_json or "{}") if event.raw_payload_json else {}
        payload["status_note"] = note
        payload[f"{stage}_at"] = "now"
        event.raw_payload_json = _json.dumps(payload, ensure_ascii=False)
        db.add(event)
        db.commit()
        return int(event.id), str(event.partner_id)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None, str(current.get("partner_id") or "partner-hotel-default")


def _derive_commission_amount(
    amount: Optional[float],
    *,
    default_commission_amount: float,
    commission_rate: float,
) -> float:
    if amount is None or amount <= 0:
        return round(default_commission_amount, 2)
    return round(amount * commission_rate, 2)


def _build_commission_batch_from_fallback(
    *,
    dry_run: bool,
    limit: int,
    default_commission_amount: float,
    commission_rate: float,
    currency: str,
) -> CommissionSettlementBatchResponse:
    candidates = [
        (booking_ref, event)
        for booking_ref, event in _BOOKING_EVENT_FALLBACK.items()
        if str(event.get("status") or "") == "completed"
    ]
    candidates = candidates[:limit]

    created = 0
    skipped_existing = 0
    total_amount = 0.0
    items: List[CommissionSettlementItem] = []

    for booking_ref, event in candidates:
        if booking_ref in _SETTLEMENT_LEDGER_FALLBACK:
            skipped_existing += 1
            continue
        amount = _derive_commission_amount(
            event.get("amount"),
            default_commission_amount=default_commission_amount,
            commission_rate=commission_rate,
        )
        item = CommissionSettlementItem(
            booking_ref=booking_ref,
            booking_event_id=None,
            partner_id=str(event.get("partner_id") or "partner-hotel-default"),
            amount=amount,
            currency=currency,
            settlement_status="pending",
        )
        items.append(item)
        total_amount += amount
        if not dry_run:
            _SETTLEMENT_LEDGER_FALLBACK[booking_ref] = item.model_dump()
        created += 1

    return CommissionSettlementBatchResponse(
        dry_run=dry_run,
        scanned=len(candidates),
        created=created,
        skipped_existing=skipped_existing,
        total_amount=round(total_amount, 2),
        currency=currency,
        items=items,
    )


def _run_commission_settlement_batch(
    db: Any,
    *,
    dry_run: bool,
    limit: int,
    default_commission_amount: float,
    commission_rate: float,
    currency: str,
) -> CommissionSettlementBatchResponse:
    if not _db_ready(db):
        return _build_commission_batch_from_fallback(
            dry_run=dry_run,
            limit=limit,
            default_commission_amount=default_commission_amount,
            commission_rate=commission_rate,
            currency=currency,
        )

    try:
        candidates = db.query(marketplace_models.BookingEvent).filter(
            marketplace_models.BookingEvent.status == "completed",
        ).order_by(marketplace_models.BookingEvent.id.asc()).limit(limit).all()

        created = 0
        skipped_existing = 0
        total_amount = 0.0
        items: List[CommissionSettlementItem] = []

        for event in candidates:
            existing = db.query(marketplace_models.AttributionLedger).filter(
                marketplace_models.AttributionLedger.booking_event_id == event.id,
                marketplace_models.AttributionLedger.ledger_type == "commission",
            ).first()
            if existing is not None:
                skipped_existing += 1
                continue

            amount = _derive_commission_amount(
                getattr(event, "amount", None),
                default_commission_amount=default_commission_amount,
                commission_rate=commission_rate,
            )
            item = CommissionSettlementItem(
                booking_ref=str(event.booking_ref or ""),
                booking_event_id=int(event.id),
                partner_id=str(event.partner_id),
                amount=amount,
                currency=currency,
                settlement_status="pending",
            )
            items.append(item)
            total_amount += amount

            if not dry_run:
                ledger = marketplace_models.AttributionLedger(
                    booking_event_id=event.id,
                    partner_id=str(event.partner_id),
                    ledger_type="commission",
                    amount=amount,
                    currency=currency,
                    settlement_status="pending",
                    note="draft settlement batch",
                    metadata_json=_json.dumps(
                        {
                            "booking_ref": event.booking_ref,
                            "source": "nadotongryoksa-lbs-commission-batch",
                        },
                        ensure_ascii=False,
                    ),
                )
                db.add(ledger)
            created += 1

        if not dry_run:
            db.commit()

        return CommissionSettlementBatchResponse(
            dry_run=dry_run,
            scanned=len(candidates),
            created=created,
            skipped_existing=skipped_existing,
            total_amount=round(total_amount, 2),
            currency=currency,
            items=items,
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return _build_commission_batch_from_fallback(
            dry_run=dry_run,
            limit=limit,
            default_commission_amount=default_commission_amount,
            commission_rate=commission_rate,
            currency=currency,
        )


def _cancel_or_refund_booking(  # NOSONAR
    db: Any,
    *,
    booking_ref: str,
    stage: Literal["cancelled", "refunded"],
    reason: str,
    refund_amount: Optional[float],
) -> BookingCancelRefundResponse:
    fallback = _BOOKING_EVENT_FALLBACK.get(booking_ref)
    if fallback is not None:
        fallback["status"] = stage
        if reason:
            fallback["reason"] = reason
        if stage == "refunded":
            amount = float(refund_amount if refund_amount is not None else fallback.get("amount") or 0.0)
            if amount > 0:
                _SETTLEMENT_LEDGER_FALLBACK[f"refund:{booking_ref}"] = {
                    "booking_ref": booking_ref,
                    "ledger_type": "refund",
                    "amount": -round(amount, 2),
                    "currency": "USD",
                    "settlement_status": "pending",
                }
            return BookingCancelRefundResponse(
                booking_ref=booking_ref,
                stage=stage,
                partner_id=str(fallback.get("partner_id") or "partner-hotel-default"),
                ledger_adjusted=amount > 0,
                adjustment_amount=round(amount, 2),
            )
        return BookingCancelRefundResponse(
            booking_ref=booking_ref,
            stage=stage,
            partner_id=str(fallback.get("partner_id") or "partner-hotel-default"),
        )

    if not _db_ready(db):
        raise HTTPException(status_code=404, detail="booking_ref not found")  # NOSONAR

    try:
        event = db.query(marketplace_models.BookingEvent).filter(
            marketplace_models.BookingEvent.booking_ref == booking_ref,
        ).first()
        if event is None:
            raise HTTPException(status_code=404, detail="booking_ref not found")

        event.status = stage
        payload = _json.loads(event.raw_payload_json or "{}") if event.raw_payload_json else {}
        if reason:
            payload["reason"] = reason
        payload[f"{stage}_at"] = "now"
        event.raw_payload_json = _json.dumps(payload, ensure_ascii=False)
        db.add(event)

        adjusted = False
        adjustment_amount = 0.0
        currency = str(event.currency or "USD")
        if stage == "refunded":
            source_ledger = db.query(marketplace_models.AttributionLedger).filter(
                marketplace_models.AttributionLedger.booking_event_id == event.id,
                marketplace_models.AttributionLedger.ledger_type == "commission",
            ).first()
            if source_ledger is not None:
                currency = str(source_ledger.currency or currency)
            if refund_amount is not None:
                adjustment_amount = round(float(refund_amount), 2)
            elif source_ledger is not None:
                adjustment_amount = round(float(source_ledger.amount or 0.0), 2)

            if adjustment_amount > 0:
                refund_ledger = marketplace_models.AttributionLedger(
                    booking_event_id=event.id,
                    partner_id=str(event.partner_id),
                    ledger_type="refund",
                    amount=-adjustment_amount,
                    currency=currency,
                    settlement_status="pending",
                    note="refund adjustment",
                    metadata_json=_json.dumps(
                        {
                            "booking_ref": booking_ref,
                            "reason": reason,
                            "source": "nadotongryoksa-lbs-refund",
                        },
                        ensure_ascii=False,
                    ),
                )
                db.add(refund_ledger)
                adjusted = True

        db.commit()
        return BookingCancelRefundResponse(
            booking_ref=booking_ref,
            booking_event_id=int(event.id),
            stage=stage,
            partner_id=str(event.partner_id),
            ledger_adjusted=adjusted,
            adjustment_amount=adjustment_amount,
            currency=currency,
        )
    except HTTPException:
        raise
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="failed to update cancellation/refund state")


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


# ---------------------------------------------------------------------------
# 거리·지역 무관 실시간 장소 검색(전세계)
# 정적 카탈로그(_POI_CATALOG)는 서울 8곳뿐이라 지방·해외는 0건이 되는 한계가 있다.
# 따라서 외부 제공자 캐스케이드로 전세계 POI 를 채운다.
#   1순위: SerpApi google_maps(이름·주소·전화·평점, 키 설정 시) — Redis 캐시로 레이트리밋/비용 완화
#   2순위: OpenStreetMap Overpass(무료·전세계, 공개 미러 순회) — SerpApi 실패/빈결과 폴백
#   최종 폴백: 정적 카탈로그(항상 포함)
# 모든 단계는 graceful degradation: 외부 호출이 실패해도 엔드포인트는 정적 결과로 응답한다.
# ---------------------------------------------------------------------------
_LIVE_HTTP_UA = "worldlinco-lbs/1.0 (+https://worldlinco.app)"
_OVERPASS_MIRRORS = (
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_LIVE_SERP_QUERY: Dict[str, str] = {
    "hotel": "hotels",
    "restaurant": "restaurants",
    "attraction": "tourist attractions",
    "airport": "airport",
}
# category="all" 일 때 대표 카테고리 다중 질의(맛집·숙소·명소). 공항은 통상 1~2곳뿐이라 제외.
_LIVE_ALL_CATEGORIES = ("attraction", "restaurant", "hotel")
# 단일 카테고리 검색용 셀렉터(상세). category="all" 은 _OVERPASS_SELECTORS_ALL(경량) 사용.
_OVERPASS_SELECTORS: Dict[str, tuple] = {
    "hotel": ('["tourism"="hotel"]', '["tourism"="guest_house"]', '["tourism"="hostel"]', '["tourism"="motel"]'),
    "restaurant": ('["amenity"="restaurant"]', '["amenity"="cafe"]', '["amenity"="fast_food"]'),
    "attraction": ('["tourism"="attraction"]', '["tourism"="museum"]', '["tourism"="viewpoint"]', '["historic"="monument"]'),
    "airport": ('["aeroway"="aerodrome"]',),
}
# category="all" 은 합집합 쿼리가 무거워 Overpass 가 타임아웃하므로 카테고리당 대표 셀렉터 1개로 경량화.
_OVERPASS_SELECTORS_ALL: Dict[str, tuple] = {
    "hotel": ('["tourism"="hotel"]',),
    "restaurant": ('["amenity"="restaurant"]',),
    "attraction": ('["tourism"="attraction"]',),
}


def _live_provider_enabled() -> bool:
    """라이브 외부 제공자 사용 여부. 테스트(pytest)에서는 기본 비활성(결정적·오프라인)."""
    flag = os.getenv("NADO_LBS_LIVE_PROVIDER", "").strip().lower()
    if os.getenv("PYTEST_CURRENT_TEST"):
        return flag in {"1", "true", "on", "yes"}
    return flag not in {"0", "false", "off", "no"}


def _zoom_for_radius(radius_m: int) -> int:
    """반경(m) → google_maps ll 줌 레벨(넓을수록 낮은 줌)."""
    table = ((1500, 15), (3000, 14), (6000, 13), (12000, 12), (25000, 11),
             (60000, 10), (120000, 9), (250000, 8), (600000, 7))
    for limit_m, zoom in table:
        if radius_m <= limit_m:
            return zoom
    return 6


def _norm_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _classify_osm_category(tags: Dict[str, Any]) -> str:
    tourism = str(tags.get("tourism", ""))
    if tourism in {"hotel", "guest_house", "hostel", "motel", "apartment"}:
        return "hotel"
    if str(tags.get("amenity", "")) in {"restaurant", "cafe", "fast_food", "bar", "pub"}:
        return "restaurant"
    if str(tags.get("aeroway", "")) == "aerodrome":
        return "airport"
    if tourism in {"attraction", "museum", "viewpoint", "gallery", "theme_park", "zoo"} or tags.get("historic"):
        return "attraction"
    return ""


def _osm_address(tags: Dict[str, Any]) -> str:
    if tags.get("addr:full"):
        return str(tags["addr:full"])
    street = " ".join(p for p in (str(tags.get("addr:housenumber", "")), str(tags.get("addr:street", ""))) if p.strip())
    parts = [street, str(tags.get("addr:city", "")), str(tags.get("addr:country", ""))]
    return ", ".join(p for p in parts if p.strip())


def _live_place_from_serp(item: Any, category: str) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    gps = item.get("gps_coordinates") or {}
    lat = gps.get("latitude")
    lon = gps.get("longitude")
    name = str(item.get("title") or "").strip()
    if lat is None or lon is None or not name:
        return None
    place_id = str(item.get("place_id") or item.get("data_id") or "").strip()
    address = str(item.get("address") or item.get("type") or "").strip()
    phone = str(item.get("phone") or "").strip()
    rating = item.get("rating")
    price = str(item.get("price") or "").strip()
    summary_text = str(item.get("description") or item.get("type") or address or name)
    return {
        "id": f"serp-{place_id or abs(hash(name)) % (10 ** 12)}",
        "category": category,
        "name": name,
        "lat": float(lat),
        "lon": float(lon),
        "address": address or name,
        "rating": float(rating) if isinstance(rating, (int, float)) else 0.0,
        "price_tier": price or "-",
        "booking_supported": False,  # 외부 장소는 in-app 구조화 예약(카탈로그 전용) 대신 전화예약 경로 사용
        "phone": phone,
        "summary": {"en": summary_text},
        "amenities": [],
        "review_query": name,
    }


def _fetch_serpapi_places(lat: float, lon: float, category: str, radius_m: int, limit: int, target_lang: str) -> List[Dict[str, Any]]:
    try:
        from backend.api.external_search_router import _serpapi_call
    except Exception:  # noqa: BLE001
        return []
    if not str(os.getenv("SERPAPI_API_KEY", "")).strip():
        return []
    cats = _LIVE_ALL_CATEGORIES if category == "all" else (category,)
    zoom = _zoom_for_radius(radius_m)
    ll = f"@{lat:.6f},{lon:.6f},{zoom}z"
    out: List[Dict[str, Any]] = []
    for cat in cats:
        query = _LIVE_SERP_QUERY.get(cat)
        if not query:
            continue
        try:
            payload = _serpapi_call("google_maps", query, max(limit, 10), 12.0, ll=ll, type="search", hl=_normalize_lang(target_lang))
        except Exception as exc:  # noqa: BLE001
            logger.info("[lbs] serpapi(%s) 실패: %s", cat, exc)
            continue
        for item in (payload.get("local_results") or [])[: max(limit, 10)]:
            place = _live_place_from_serp(item, cat)
            if place:
                out.append(place)
    return out


def _overpass_request(query: str) -> Dict[str, Any]:
    data = ("data=" + query).encode("utf-8")
    last_err: Optional[Exception] = None
    for mirror in _OVERPASS_MIRRORS:
        try:
            req = urllib.request.Request(mirror, data=data, headers={"User-Agent": _LIVE_HTTP_UA})
            with urllib.request.urlopen(req, timeout=22) as resp:
                return _json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            continue
    if last_err is not None:
        logger.info("[lbs] overpass 전 미러 실패: %s", last_err)
    return {}


def _fetch_overpass_places(lat: float, lon: float, category: str, radius_m: int, limit: int, target_lang: str) -> List[Dict[str, Any]]:  # NOSONAR
    if category == "all":
        cats = _LIVE_ALL_CATEGORIES
        selector_map = _OVERPASS_SELECTORS_ALL
    else:
        cats = (category,)
        selector_map = _OVERPASS_SELECTORS
    selectors: List[str] = []
    for cat in cats:
        selectors.extend(selector_map.get(cat, ()))
    if not selectors:
        return []
    around = f"(around:{radius_m},{lat:.6f},{lon:.6f})"
    # nwr = node/way/relation 단축구문(쿼리 경량화). out center 로 way/relation 중심좌표 포함.
    body = "".join(f"nwr{sel}{around};" for sel in selectors)
    out_count = min(max(limit * 4, 20), 80)
    query = f"[out:json][timeout:25];({body});out center {out_count};"
    payload = _overpass_request(query)
    elements = payload.get("elements") or []
    out: List[Dict[str, Any]] = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        tags = el.get("tags") or {}
        name = str(tags.get("name") or tags.get("name:en") or "").strip()
        if not name:
            continue
        cat = _classify_osm_category(tags)
        if not cat:
            continue
        if el.get("type") == "node":
            plat, plon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            plat, plon = center.get("lat"), center.get("lon")
        if plat is None or plon is None:
            continue
        phone = str(tags.get("contact:phone") or tags.get("phone") or "").strip()
        address = _osm_address(tags)
        out.append({
            "id": f"osm-{str(el.get('type', 'n'))[:1]}{el.get('id', '')}",
            "category": cat,
            "name": name,
            "lat": float(plat),
            "lon": float(plon),
            "address": address or name,
            "rating": 0.0,
            "price_tier": "-",
            "booking_supported": False,
            "phone": phone,
            "summary": {"en": address or name},
            "amenities": [],
            "review_query": name,
        })
    return out


def _fetch_live_place_dicts(lat: float, lon: float, category: str, radius_m: int, limit: int, target_lang: str) -> List[Dict[str, Any]]:
    """캐스케이드(SerpApi→Overpass) + Redis 캐시. 원시 dict 리스트 반환(직렬화 가능)."""
    def _do() -> List[Dict[str, Any]]:
        places = _fetch_serpapi_places(lat, lon, category, radius_m, limit, target_lang)
        if places:
            return places
        return _fetch_overpass_places(lat, lon, category, radius_m, limit, target_lang)

    # 좌표를 ~1km 격자로 버킷팅해 인접 검색이 캐시를 공유하도록 한다.
    key = (round(lat, 2), round(lon, 2), category, radius_m, _normalize_lang(target_lang))
    try:
        from backend.services.realtime_cache import cached_fetch
        return cached_fetch("osm", key, _do)
    except Exception:  # noqa: BLE001
        return _do()


def build_nadotongryoksa_lbs_router(contract: Any) -> APIRouter:  # NOSONAR
    router = APIRouter(prefix="/nadotongryoksa/lbs", tags=["marketplace-nadotongryoksa-lbs"])

    @router.get("/nearby", response_model=NearbySearchResponse)
    def nearby_places(
        lat: float = Query(..., ge=-90, le=90),
        lon: float = Query(..., ge=-180, le=180),
        category: SearchCategory = Query("all"),
        radius_m: int = Query(5000, ge=300, le=500000),
        limit: int = Query(8, ge=1, le=20),
        target_lang: str = Query("ko"),
        trip_session_id: Optional[str] = Query(default=None),
        # [보안 보강] 무인증 경로지만 live 시 SerpApi(유료)/Overpass 팬아웃을 유발하므로 IP 단위
        # 레이트리밋으로 비용 증폭/업스트림 남용을 1차 차단(기본 40/분, 초과 시 429+Retry-After).
        _lbs_quota: None = Depends(require_lbs_search_quota),
        db: Session = Depends(get_db),
    ) -> NearbySearchResponse:
        normalized_lang = _normalize_lang(target_lang)
        # 1) 정적 카탈로그(항상 포함, 서울권 보장 + 오프라인/테스트 결정성)
        results: List[NearbyPlaceResponse] = list(
            _filter_places(lat=lat, lon=lon, category=category, radius_m=radius_m, limit=limit, target_lang=normalized_lang)
        )
        # 2) 실시간 외부 제공자(전세계·거리무관) 병합 — 실패해도 정적 결과로 응답
        if _live_provider_enabled():
            try:
                live = _fetch_live_place_dicts(lat, lon, category, radius_m, limit, normalized_lang)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[lbs] live provider 오류: %s", exc)
                live = []
            seen = {_norm_name(r.name) for r in results}
            for place in live or []:
                name_key = _norm_name(str(place.get("name", "")))
                if not name_key or name_key in seen:
                    continue
                if category != "all" and place.get("category") != category:
                    continue
                try:
                    distance_m = _haversine_distance_m(lat, lon, float(place["lat"]), float(place["lon"]))
                except Exception:  # noqa: BLE001
                    continue
                if distance_m > radius_m:
                    continue
                try:
                    results.append(_to_nearby_response(place, target_lang=normalized_lang, distance_m=distance_m))
                except Exception:  # noqa: BLE001
                    continue
                seen.add(name_key)
        results.sort(key=lambda r: r.distance_m)
        results = results[:limit]
        trip_session_pk, resolved_trip_session_id = _ensure_trip_session(
            db,
            requested_session_id=trip_session_id,
            user_id=None,
            lat=lat,
            lon=lon,
        )
        _record_recommendation_events(
            db,
            trip_session_pk=trip_session_pk,
            user_id=None,
            places=results,
        )
        return NearbySearchResponse(
            target_lang=normalized_lang,
            requested_category=category,
            radius_m=radius_m,
            total=len(results),
            places=results,
            trip_session_id=resolved_trip_session_id,
        )

    @router.post("/clicks", response_model=PartnerClickResponse)
    def create_partner_click(
        payload: PartnerClickRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> PartnerClickResponse:
        click_ref = f"CLK-{uuid4().hex[:12].upper()}"
        partner_id = (payload.partner_id or "").strip()
        if not partner_id and payload.recommendation_id and _db_ready(db):
            try:
                recommendation = db.query(marketplace_models.RecommendationEvent).filter(
                    marketplace_models.RecommendationEvent.id == payload.recommendation_id,
                ).first()
                if recommendation is not None and recommendation.partner_id:
                    partner_id = str(recommendation.partner_id)
            except Exception:
                partner_id = ""
        partner_id = partner_id or "partner-hotel-default"

        click_event_id: Optional[int] = None
        if _db_ready(db):
            try:
                event = marketplace_models.PartnerClickEvent(
                    recommendation_event_id=payload.recommendation_id,
                    user_id=getattr(current_user, "id", None),
                    partner_id=partner_id,
                    click_ref=click_ref,
                    landing_url=payload.landing_url,
                    metadata_json=_json.dumps(
                        {
                            "trip_session_id": payload.trip_session_id,
                        },
                        ensure_ascii=False,
                    ),
                )
                db.add(event)
                db.flush()
                click_event_id = int(event.id)
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass

        return PartnerClickResponse(
            click_ref=click_ref,
            partner_id=partner_id,
            recommendation_id=payload.recommendation_id,
            click_event_id=click_event_id,
        )

    @router.post(
        "/bookings/start",
        response_model=BookingLifecycleResponse,
        responses={
            400: {"description": "booking not supported for selected place"},
            404: {"description": "place_id not found"},
        },
    )
    def start_booking(
        payload: BookingRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> BookingLifecycleResponse:
        place = next((item for item in _POI_CATALOG if item["id"] == payload.place_id), None)
        if not place:
            raise HTTPException(status_code=404, detail="place_id not found")
        if place["category"] != "hotel" or not place["booking_supported"]:
            raise HTTPException(status_code=400, detail="예약은 호텔 카테고리에서만 지원됩니다.")

        booking_ref = f"BK-{uuid4().hex[:12].upper()}"
        partner_id = "partner-hotel-default"
        booking_event_id = _create_booking_event(
            db,
            booking_ref=booking_ref,
            user_id=getattr(current_user, "id", None),
            partner_id=partner_id,
            partner_click_event_id=payload.partner_click_event_id,
            payload={
                "place_id": payload.place_id,
                "customer_name": payload.customer_name,
                "checkin_date": payload.checkin_date,
                "checkout_date": payload.checkout_date,
                "guests": payload.guests,
                "room_count": payload.room_count,
                "partner_click_ref": payload.partner_click_ref,
            },
        )
        return BookingLifecycleResponse(
            booking_ref=booking_ref,
            booking_event_id=booking_event_id,
            stage="initiated",
            partner_id=partner_id,
        )

    @router.post("/bookings/{booking_ref}/confirm", response_model=BookingLifecycleResponse)
    def confirm_booking(
        booking_ref: str,
        payload: BookingLifecycleRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> BookingLifecycleResponse:
        _ = current_user
        if payload.booking_ref != booking_ref:
            raise HTTPException(status_code=400, detail="booking_ref mismatch")  # NOSONAR
        booking_event_id, partner_id = _advance_booking_stage(db, booking_ref, "confirmed", payload.status_note)
        return BookingLifecycleResponse(
            booking_ref=booking_ref,
            booking_event_id=booking_event_id,
            stage="confirmed",
            partner_id=partner_id,
        )

    @router.post("/bookings/{booking_ref}/complete", response_model=BookingLifecycleResponse)
    def complete_booking(
        booking_ref: str,
        payload: BookingLifecycleRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> BookingLifecycleResponse:
        _ = current_user
        if payload.booking_ref != booking_ref:
            raise HTTPException(status_code=400, detail="booking_ref mismatch")
        booking_event_id, partner_id = _advance_booking_stage(db, booking_ref, "completed", payload.status_note)
        return BookingLifecycleResponse(
            booking_ref=booking_ref,
            booking_event_id=booking_event_id,
            stage="completed",
            partner_id=partner_id,
        )

    @router.post(
        "/bookings/{booking_ref}/cancel",
        response_model=BookingCancelRefundResponse,
        responses={
            400: {"description": "요청 본문과 경로 booking_ref 가 일치해야 합니다."},
            404: {"description": "booking_ref not found"},
            500: {"description": "취소 상태 업데이트 실패"},
        },
    )
    def cancel_booking(
        booking_ref: str,
        payload: BookingCancelRefundRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> BookingCancelRefundResponse:
        _ = current_user
        if payload.booking_ref != booking_ref:
            raise HTTPException(status_code=400, detail="booking_ref mismatch")
        return _cancel_or_refund_booking(
            db,
            booking_ref=booking_ref,
            stage="cancelled",
            reason=payload.reason,
            refund_amount=None,
        )

    @router.post(
        "/bookings/{booking_ref}/refund",
        response_model=BookingCancelRefundResponse,
        responses={
            400: {"description": "요청 본문과 경로 booking_ref 가 일치해야 합니다."},
            404: {"description": "booking_ref not found"},
            500: {"description": "환불 상태 업데이트 실패"},
        },
    )
    def refund_booking(
        booking_ref: str,
        payload: BookingCancelRefundRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> BookingCancelRefundResponse:
        _ = current_user
        if payload.booking_ref != booking_ref:
            raise HTTPException(status_code=400, detail="booking_ref mismatch")  # NOSONAR
        return _cancel_or_refund_booking(
            db,
            booking_ref=booking_ref,
            stage="refunded",
            reason=payload.reason,
            refund_amount=payload.refund_amount,
        )

    @router.post("/settlements/commission-batch", response_model=CommissionSettlementBatchResponse)
    def run_commission_settlement_batch(
        payload: CommissionSettlementBatchRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> CommissionSettlementBatchResponse:
        _ = current_user
        currency = payload.currency.upper()
        return _run_commission_settlement_batch(
            db,
            dry_run=payload.dry_run,
            limit=payload.limit,
            default_commission_amount=payload.default_commission_amount,
            commission_rate=payload.commission_rate,
            currency=currency,
        )

    @router.post("/bookings", response_model=BookingResponse)
    def create_booking(
        payload: BookingRequest,
        current_user=Depends(contract.get_current_user),
        db: Session = Depends(get_db),
    ) -> BookingResponse:
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
        booking_ref = f"BK-{uuid4().hex[:12].upper()}"
        _create_booking_event(
            db,
            booking_ref=booking_ref,
            user_id=getattr(current_user, "id", None),
            partner_id="partner-hotel-default",
            partner_click_event_id=payload.partner_click_event_id,
            payload={
                "place_id": payload.place_id,
                "customer_name": payload.customer_name,
                "checkin_date": payload.checkin_date,
                "checkout_date": payload.checkout_date,
                "guests": payload.guests,
                "room_count": payload.room_count,
                "partner_click_ref": payload.partner_click_ref,
                "legacy_booking_endpoint": True,
            },
        )
        _advance_booking_stage(db, booking_ref, "confirmed", "legacy auto-confirm")
        _advance_booking_stage(db, booking_ref, "completed", "legacy auto-complete")

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
