// App.tsx 에서 분리한 UI 다국어 사전 + getUiText(언어 카운트 치환/폴백).
import { APP_FOOTER_BRAND, APP_FOOTER_BRAND_KO } from './appConstants';
import { SUPPORTED_LANGUAGE_COUNT } from '../features/language/languageCatalog';

// ─────────────────────────────────────────────
// UI 텍스트 다국어 사전 (기본 번역 UI 사전 + 나머지 언어는 영어 fallback)
// ─────────────────────────────────────────────
export const UI_TEXT: Record<string, {
    sourceLang: string; targetLang: string; inputPlaceholder: string;
    swap: string; translate: string; resultPlaceholder: string;
    inputRequired: string; inputRequiredMsg: string; errorMsg: string;
    offlineMsg: string; subtitle: string; footer: string; offlineBadge: string;
    ocrTitle?: string;
    ocrSubtitle?: string;
    ocrPickImage?: string;
    ocrLoading?: string;
    ocrExtractedTitle?: string;
    ocrTranslatedTitle?: string;
    ocrSelectedFile?: string;
    ocrErrorMsg?: string;
    autoVoiceSegmentStatus?: string;
    autoVoiceDuplicateSkipped?: string;
    autoVoiceDetected?: string;
    autoVoiceModeStopped?: string;
    autoVoiceModeStarted?: string;
    manualVoiceOnlyNotice?: string;
    manualLanguageHint?: string;
    profileLanguageLabel?: string;
    profileLanguageHint?: string;
    peerLanguageLabel?: string;
    peerLanguageHint?: string;
    faceConversationOn?: string;
    faceConversationOff?: string;
    faceConversationPeerRequired?: string;
    faceListenProcessing?: string;
    faceSpeakingStatus?: string;
    faceVadHint?: string;
    interAutoRelayDuplicateSkipped?: string;
    interAutoRelayPending?: string;
    voipIncomingTitle?: string;
    voipIncomingAccept?: string;
    voipIncomingReject?: string;
    voipIncomingConnecting?: string;
}> = {
    ko: { sourceLang: '원본 언어', targetLang: '번역 언어', inputPlaceholder: '번역할 텍스트를 입력하세요', swap: '⇄ 언어 스왑', translate: '번역', resultPlaceholder: '번역 결과가 여기에 표시됩니다', inputRequired: '입력 필요', inputRequiredMsg: '번역할 텍스트를 입력하세요.', errorMsg: '[오류] 번역에 실패했습니다. 잠시 후 다시 시도하세요.', offlineMsg: '📡 오프라인 모드 — 인터넷 연결 시 전체 통역 가능', subtitle: '여행 통번역 · 24개국어', footer: `${APP_FOOTER_BRAND_KO}\n24개국어 지원`, offlineBadge: '🔴 오프라인', ocrTitle: '카메라·이미지 번역', ocrSubtitle: '앱 내 카메라로 메뉴판·표지판을 고밀도 촬영하면 즉시 OCR·번역합니다. 갤러리 선택도 가능합니다.', ocrPickImage: '📷 고밀도 카메라 / 🖼️ 갤러리', ocrLoading: 'OCR 추출 중...', ocrExtractedTitle: 'OCR 추출 텍스트', ocrTranslatedTitle: 'OCR 번역 결과', ocrSelectedFile: '선택 파일: {file}', ocrErrorMsg: '이미지 OCR 처리에 실패했습니다. 잠시 후 다시 시도하세요.', autoVoiceSegmentStatus: '🎙️ 듣는 중 · 말이 끝나면 자동 번역', autoVoiceDuplicateSkipped: '↺ 같은 문장 자동 번역은 중복 전송을 방지하기 위해 생략했습니다.', autoVoiceDetected: '🎙️ 자동 감지: {from} → {to}', autoVoiceModeStopped: '🎙️ 대화 통역을 종료했습니다.', autoVoiceModeStarted: '🎙️ 대화 통역 시작 · 말 끝날 때까지 듣습니다', manualVoiceOnlyNotice: '🎙️ 대화 통역 OFF — 텍스트 입력만 사용합니다.', manualLanguageHint: 'GPS 우선 · 필요 시 수동', profileLanguageLabel: '내 언어 (프로필)', profileLanguageHint: '프로필 저장값', peerLanguageLabel: '상대 언어 (GPS/수동)', peerLanguageHint: 'GPS 우선 · 필요 시 수동', faceConversationOn: '🎙️ 대화 통역 ON', faceConversationOff: '대화 통역 OFF', faceConversationPeerRequired: '상대 언어를 GPS 또는 수동 선택으로 지정해 주세요.', faceListenProcessing: '🔄 번역·음성 출력 중...', faceSpeakingStatus: '🔊 통역 음성 출력 중 · 듣기 멈춤', faceVadHint: 'VoIP와 같이 말이 끝날 때까지 마이크가 켜져 있습니다.', interAutoRelayDuplicateSkipped: '↺ 같은 문장 자동 중계는 중복 전송을 방지하기 위해 생략했습니다.', interAutoRelayPending: '⏱️ {delay} 무입력 시 자동 중계 전송', voipIncomingTitle: '📞 수신 보이스톡', voipIncomingAccept: '받기', voipIncomingReject: '거절', voipIncomingConnecting: '서버 연결 중… 잠시만 기다려 주세요' },
    en: { sourceLang: 'Source Language', targetLang: 'Target Language', inputPlaceholder: 'Enter text to translate', swap: '⇄ Swap', translate: 'Translate', resultPlaceholder: 'Translation will appear here', inputRequired: 'Input required', inputRequiredMsg: 'Please enter text to translate.', errorMsg: '[Error] Translation failed. Please try again.', offlineMsg: '📡 Offline mode — Full translation available with internet', subtitle: 'Travel Interpreter · 24 Languages', footer: `${APP_FOOTER_BRAND}\n24 Languages Supported`, offlineBadge: '🔴 Offline', ocrTitle: 'Camera & Image Translation', ocrSubtitle: 'In-app camera captures menus and signs in high density, then OCR and translate instantly. Gallery pick is also available.', ocrPickImage: '📷 HD Camera / 🖼️ Gallery', ocrLoading: 'Running OCR...', ocrExtractedTitle: 'OCR Extracted Text', ocrTranslatedTitle: 'OCR Translation Result', ocrSelectedFile: 'Selected file: {file}', ocrErrorMsg: 'Image OCR failed. Please try again.', autoVoiceSegmentStatus: '🎙️ Listening · auto-translate when you finish speaking', autoVoiceDuplicateSkipped: '↺ Duplicate sentence skipped to prevent repeated auto translation.', autoVoiceDetected: '🎙️ Auto-detected: {from} → {to}', autoVoiceModeStopped: '🎙️ Face conversation mode stopped.', autoVoiceModeStarted: '🎙️ Conversation started · listening until you finish speaking', manualVoiceOnlyNotice: '🎙️ Face conversation OFF — text input only.', manualLanguageHint: 'GPS first · manual override', profileLanguageLabel: 'My language (profile)', profileLanguageHint: 'Saved in profile', peerLanguageLabel: 'Peer language (GPS/manual)', peerLanguageHint: 'GPS first · manual override', faceConversationOn: '🎙️ Conversation ON', faceConversationOff: 'Conversation OFF', faceConversationPeerRequired: 'Set the peer language via GPS or manual selection.', faceListenProcessing: '🔄 Translating & speaking...', faceSpeakingStatus: '🔊 Speaking translation · listening paused', faceVadHint: 'Like VoIP — the mic stays on until you finish speaking.', interAutoRelayDuplicateSkipped: '↺ Duplicate sentence skipped to prevent repeated auto relay.', interAutoRelayPending: '⏱️ Auto relay after {delay} of no input', voipIncomingTitle: '📞 Incoming voice call', voipIncomingAccept: 'Accept', voipIncomingReject: 'Decline', voipIncomingConnecting: 'Connecting to server… please wait' },
    zh: { sourceLang: '源语言', targetLang: '目标语言', inputPlaceholder: '请输入要翻译的文本', swap: '⇄ 切换语言', translate: '翻译', resultPlaceholder: '翻译结果将显示在这里', inputRequired: '需要输入', inputRequiredMsg: '请输入要翻译的文本。', errorMsg: '[错误] 翻译失败，请稍后重试。', offlineMsg: '📡 离线模式 — 联网后可使用完整翻译', subtitle: 'AI 翻译 · 24种语言', footer: `${APP_FOOTER_BRAND}\n支持24种语言`, offlineBadge: '🔴 离线' },
    'zh-tw': { sourceLang: '來源語言', targetLang: '目標語言', inputPlaceholder: '請輸入要翻譯的文字', swap: '⇄ 切換語言', translate: '翻譯', resultPlaceholder: '翻譯結果將顯示在這裡', inputRequired: '需要輸入', inputRequiredMsg: '請輸入要翻譯的文字。', errorMsg: '[錯誤] 翻譯失敗，請稍後再試。', offlineMsg: '📡 離線模式 — 連網後可使用完整翻譯', subtitle: 'AI 翻譯 · 24種語言', footer: `${APP_FOOTER_BRAND}\n支援24種語言`, offlineBadge: '🔴 離線' },
    ja: { sourceLang: '翻訳元言語', targetLang: '翻訳先言語', inputPlaceholder: '翻訳するテキストを入力してください', swap: '⇄ 言語スワップ', translate: '翻訳', resultPlaceholder: '翻訳結果がここに表示されます', inputRequired: '入力が必要です', inputRequiredMsg: '翻訳するテキストを入力してください。', errorMsg: '[エラー] 翻訳に失敗しました。後でもう一度お試しください。', offlineMsg: '📡 オフラインモード — インターネット接続後に完全翻訳可能', subtitle: 'AI 通訳 · 24言語', footer: `${APP_FOOTER_BRAND}\n24言語対応`, offlineBadge: '🔴 オフライン', voipIncomingTitle: '📞 着信ボイストーク', voipIncomingAccept: '応答', voipIncomingReject: '拒否', voipIncomingConnecting: 'サーバー接続中…しばらくお待ちください' },
    es: { sourceLang: 'Idioma de origen', targetLang: 'Idioma de destino', inputPlaceholder: 'Ingrese el texto a traducir', swap: '⇄ Cambiar', translate: 'Traducir', resultPlaceholder: 'La traducción aparecerá aquí', inputRequired: 'Entrada requerida', inputRequiredMsg: 'Por favor ingrese el texto a traducir.', errorMsg: '[Error] La traducción falló. Inténtelo de nuevo.', offlineMsg: '📡 Modo sin conexión — Traducción completa disponible con internet', subtitle: 'Intérprete AI · 24 Idiomas', footer: `${APP_FOOTER_BRAND}\n24 Idiomas`, offlineBadge: '🔴 Sin conexión' },
    fr: { sourceLang: 'Langue source', targetLang: 'Langue cible', inputPlaceholder: 'Entrez le texte à traduire', swap: '⇄ Permuter', translate: 'Traduire', resultPlaceholder: 'La traduction apparaîtra ici', inputRequired: 'Saisie requise', inputRequiredMsg: 'Veuillez entrer le texte à traduire.', errorMsg: '[Erreur] La traduction a échoué. Veuillez réessayer.', offlineMsg: '📡 Mode hors ligne — Traduction complète disponible avec internet', subtitle: 'Interprète AI · 24 Langues', footer: `${APP_FOOTER_BRAND}\n24 Langues`, offlineBadge: '🔴 Hors ligne' },
    de: { sourceLang: 'Quellsprache', targetLang: 'Zielsprache', inputPlaceholder: 'Text zum Übersetzen eingeben', swap: '⇄ Tauschen', translate: 'Übersetzen', resultPlaceholder: 'Übersetzung erscheint hier', inputRequired: 'Eingabe erforderlich', inputRequiredMsg: 'Bitte geben Sie den zu übersetzenden Text ein.', errorMsg: '[Fehler] Übersetzung fehlgeschlagen. Bitte versuchen Sie es erneut.', offlineMsg: '📡 Offline-Modus — Vollständige Übersetzung mit Internet verfügbar', subtitle: 'KI-Dolmetscher · 24 Sprachen', footer: `${APP_FOOTER_BRAND}\n24 Sprachen`, offlineBadge: '🔴 Offline' },
    pt: { sourceLang: 'Idioma de origem', targetLang: 'Idioma de destino', inputPlaceholder: 'Digite o texto para traduzir', swap: '⇄ Trocar', translate: 'Traduzir', resultPlaceholder: 'A tradução aparecerá aqui', inputRequired: 'Entrada necessária', inputRequiredMsg: 'Por favor, insira o texto para traduzir.', errorMsg: '[Erro] A tradução falhou. Por favor, tente novamente.', offlineMsg: '📡 Modo offline — Tradução completa disponível com internet', subtitle: 'Intérprete AI · 24 Idiomas', footer: `${APP_FOOTER_BRAND}\n24 Idiomas`, offlineBadge: '🔴 Offline' },
    ru: { sourceLang: 'Исходный язык', targetLang: 'Целевой язык', inputPlaceholder: 'Введите текст для перевода', swap: '⇄ Поменять', translate: 'Перевести', resultPlaceholder: 'Перевод появится здесь', inputRequired: 'Ввод обязателен', inputRequiredMsg: 'Пожалуйста, введите текст для перевода.', errorMsg: '[Ошибка] Перевод не удался. Попробуйте ещё раз.', offlineMsg: '📡 Офлайн-режим — Полный перевод доступен при наличии интернета', subtitle: 'AI Переводчик · 24 Языка', footer: `${APP_FOOTER_BRAND}\n24 языка`, offlineBadge: '🔴 Офлайн' },
    ar: { sourceLang: 'اللغة المصدر', targetLang: 'اللغة الهدف', inputPlaceholder: 'أدخل النص للترجمة', swap: '⇄ تبديل', translate: 'ترجمة', resultPlaceholder: 'ستظهر الترجمة هنا', inputRequired: 'مطلوب إدخال', inputRequiredMsg: 'الرجاء إدخال النص للترجمة.', errorMsg: '[خطأ] فشلت الترجمة. يرجى المحاولة مرة أخرى.', offlineMsg: '📡 وضع عدم الاتصال — الترجمة الكاملة متاحة مع الإنترنت', subtitle: 'مترجم AI · 24 لغة', footer: `${APP_FOOTER_BRAND}\n24 لغة مدعومة`, offlineBadge: '🔴 غير متصل' },
    hi: { sourceLang: 'स्रोत भाषा', targetLang: 'लक्ष्य भाषा', inputPlaceholder: 'अनुवाद के लिए पाठ दर्ज करें', swap: '⇄ स्वैप', translate: 'अनुवाद करें', resultPlaceholder: 'अनुवाद यहाँ दिखाई देगा', inputRequired: 'इनपुट आवश्यक', inputRequiredMsg: 'कृपया अनुवाद के लिए पाठ दर्ज करें।', errorMsg: '[त्रुटि] अनुवाद विफल हुआ। कृपया पुनः प्रयास करें।', offlineMsg: '📡 ऑफ़लाइन मोड — इंटरनेट के साथ पूर्ण अनुवाद उपलब्ध', subtitle: 'AI दुभाषिया · 24 भाषाएँ', footer: `${APP_FOOTER_BRAND}\n24 भाषाएँ समर्थित`, offlineBadge: '🔴 ऑफ़लाइन' },
    it: { sourceLang: 'Lingua di origine', targetLang: 'Lingua di destinazione', inputPlaceholder: 'Inserisci il testo da tradurre', swap: '⇄ Scambia', translate: 'Traduci', resultPlaceholder: 'La traduzione apparirà qui', inputRequired: 'Input richiesto', inputRequiredMsg: 'Inserisci il testo da tradurre.', errorMsg: '[Errore] Traduzione fallita. Riprovare.', offlineMsg: '📡 Modalità offline — Traduzione completa disponibile con internet', subtitle: 'Interprete AI · 24 Lingue', footer: `${APP_FOOTER_BRAND}\n24 Lingue`, offlineBadge: '🔴 Offline' },
    tr: { sourceLang: 'Kaynak Dil', targetLang: 'Hedef Dil', inputPlaceholder: 'Çevrilecek metni girin', swap: '⇄ Değiştir', translate: 'Çevir', resultPlaceholder: 'Çeviri burada görünecek', inputRequired: 'Giriş gerekli', inputRequiredMsg: 'Lütfen çevrilecek metni girin.', errorMsg: '[Hata] Çeviri başarısız. Lütfen tekrar deneyin.', offlineMsg: '📡 Çevrimdışı mod — İnternet ile tam çeviri mevcut', subtitle: 'AI Tercüman · 24 Dil', footer: `${APP_FOOTER_BRAND}\n24 Dil Destekleniyor`, offlineBadge: '🔴 Çevrimdışı' },
    vi: { sourceLang: 'Ngôn ngữ nguồn', targetLang: 'Ngôn ngữ đích', inputPlaceholder: 'Nhập văn bản cần dịch', swap: '⇄ Hoán đổi', translate: 'Dịch', resultPlaceholder: 'Bản dịch sẽ hiển thị ở đây', inputRequired: 'Cần nhập liệu', inputRequiredMsg: 'Vui lòng nhập văn bản cần dịch.', errorMsg: '[Lỗi] Dịch thất bại. Vui lòng thử lại.', offlineMsg: '📡 Chế độ ngoại tuyến — Dịch đầy đủ khi có internet', subtitle: 'Phiên dịch AI · 24 Ngôn ngữ', footer: `${APP_FOOTER_BRAND}\n24 Ngôn ngữ`, offlineBadge: '🔴 Ngoại tuyến' },
    th: { sourceLang: 'ภาษาต้นทาง', targetLang: 'ภาษาปลายทาง', inputPlaceholder: 'ป้อนข้อความที่ต้องการแปล', swap: '⇄ สลับ', translate: 'แปล', resultPlaceholder: 'ผลการแปลจะแสดงที่นี่', inputRequired: 'ต้องการข้อมูล', inputRequiredMsg: 'กรุณาป้อนข้อความที่ต้องการแปล', errorMsg: '[ข้อผิดพลาด] การแปลล้มเหลว โปรดลองอีกครั้ง', offlineMsg: '📡 โหมดออฟไลน์ — แปลเต็มรูปแบบเมื่อมีอินเทอร์เน็ต', subtitle: 'AI ล่าม · 24 ภาษา', footer: `${APP_FOOTER_BRAND}\n24 ภาษา`, offlineBadge: '🔴 ออฟไลน์' },
    id: { sourceLang: 'Bahasa Sumber', targetLang: 'Bahasa Tujuan', inputPlaceholder: 'Masukkan teks untuk diterjemahkan', swap: '⇄ Tukar', translate: 'Terjemahkan', resultPlaceholder: 'Terjemahan akan muncul di sini', inputRequired: 'Input diperlukan', inputRequiredMsg: 'Silakan masukkan teks untuk diterjemahkan.', errorMsg: '[Kesalahan] Terjemahan gagal. Silakan coba lagi.', offlineMsg: '📡 Mode offline — Terjemahan lengkap tersedia dengan internet', subtitle: 'Penerjemah AI · 24 Bahasa', footer: `${APP_FOOTER_BRAND}\n24 Bahasa`, offlineBadge: '🔴 Offline' },
    ms: { sourceLang: 'Bahasa Sumber', targetLang: 'Bahasa Sasaran', inputPlaceholder: 'Masukkan teks untuk diterjemah', swap: '⇄ Tukar', translate: 'Terjemah', resultPlaceholder: 'Terjemahan akan muncul di sini', inputRequired: 'Input diperlukan', inputRequiredMsg: 'Sila masukkan teks untuk diterjemah.', errorMsg: '[Ralat] Terjemahan gagal. Sila cuba lagi.', offlineMsg: '📡 Mod luar talian — Terjemahan penuh tersedia dengan internet', subtitle: 'Penterjemah AI · 24 Bahasa', footer: `${APP_FOOTER_BRAND}\n24 Bahasa`, offlineBadge: '🔴 Luar Talian' },
    nl: { sourceLang: 'Brontaal', targetLang: 'Doeltaal', inputPlaceholder: 'Voer tekst in om te vertalen', swap: '⇄ Wisselen', translate: 'Vertalen', resultPlaceholder: 'Vertaling verschijnt hier', inputRequired: 'Invoer vereist', inputRequiredMsg: 'Voer de te vertalen tekst in.', errorMsg: '[Fout] Vertaling mislukt. Probeer opnieuw.', offlineMsg: '📡 Offlinemodus — Volledige vertaling beschikbaar met internet', subtitle: 'AI Tolk · 24 Talen', footer: `${APP_FOOTER_BRAND}\n24 Talen`, offlineBadge: '🔴 Offline' },
    pl: { sourceLang: 'Język źródłowy', targetLang: 'Język docelowy', inputPlaceholder: 'Wprowadź tekst do tłumaczenia', swap: '⇄ Zamień', translate: 'Tłumacz', resultPlaceholder: 'Tłumaczenie pojawi się tutaj', inputRequired: 'Wymagane wprowadzenie', inputRequiredMsg: 'Wprowadź tekst do tłumaczenia.', errorMsg: '[Błąd] Tłumaczenie nie powiodło się. Spróbuj ponownie.', offlineMsg: '📡 Tryb offline — Pełne tłumaczenie dostępne z internetem', subtitle: 'Tłumacz AI · 24 Języki', footer: `${APP_FOOTER_BRAND}\n24 Języki`, offlineBadge: '🔴 Offline' },
    uk: { sourceLang: 'Вихідна мова', targetLang: 'Цільова мова', inputPlaceholder: 'Введіть текст для перекладу', swap: '⇄ Замінити', translate: 'Перекласти', resultPlaceholder: "Переклад з'явиться тут", inputRequired: 'Потрібне введення', inputRequiredMsg: 'Будь ласка, введіть текст для перекладу.', errorMsg: '[Помилка] Переклад не вдався. Спробуйте ще раз.', offlineMsg: '📡 Офлайн-режим — Повний переклад доступний при наявності інтернету', subtitle: 'AI Перекладач · 24 Мови', footer: `${APP_FOOTER_BRAND}\n24 мови`, offlineBadge: '🔴 Офлайн' },
    sv: { sourceLang: 'Källspråk', targetLang: 'Målspråk', inputPlaceholder: 'Ange text att översätta', swap: '⇄ Byt', translate: 'Översätt', resultPlaceholder: 'Översättning visas här', inputRequired: 'Inmatning krävs', inputRequiredMsg: 'Ange texten som ska översättas.', errorMsg: '[Fel] Översättning misslyckades. Försök igen.', offlineMsg: '📡 Offlineläge — Full översättning tillgänglig med internet', subtitle: 'AI Tolk · 24 Språk', footer: `${APP_FOOTER_BRAND}\n24 Språk`, offlineBadge: '🔴 Offline' },
    no: { sourceLang: 'Kildespråk', targetLang: 'Målspråk', inputPlaceholder: 'Skriv inn tekst å oversette', swap: '⇄ Bytt', translate: 'Oversett', resultPlaceholder: 'Oversettelse vises her', inputRequired: 'Inndata kreves', inputRequiredMsg: 'Skriv inn tekst å oversette.', errorMsg: '[Feil] Oversettelse mislyktes. Prøv igjen.', offlineMsg: '📡 Frakoblet modus — Full oversettelse tilgengelig med internett', subtitle: 'AI Tolk · 24 Språk', footer: `${APP_FOOTER_BRAND}\n24 Språk`, offlineBadge: '🔴 Frakoblet' },
    da: { sourceLang: 'Kildesprog', targetLang: 'Målsprog', inputPlaceholder: 'Indtast tekst til oversættelse', swap: '⇄ Skift', translate: 'Oversæt', resultPlaceholder: 'Oversættelse vises her', inputRequired: 'Indtastning påkrævet', inputRequiredMsg: 'Indtast tekst til oversættelse.', errorMsg: '[Fejl] Oversættelse mislykkedes. Prøv igen.', offlineMsg: '📡 Offlinetilstand — Fuld oversættelse tilgængelig med internet', subtitle: 'AI Tolk · 24 Sprog', footer: `${APP_FOOTER_BRAND}\n24 Sprog`, offlineBadge: '🔴 Offline' },
};

export function getUiText(lang: string) {
    const fallback = UI_TEXT['en'];
    const selected = UI_TEXT[lang] ?? fallback;
    const applyLanguageCount = (value: string) => value.replace(/24/g, String(SUPPORTED_LANGUAGE_COUNT));
    return {
        ...selected,
        subtitle: applyLanguageCount(selected.subtitle),
        footer: applyLanguageCount(selected.footer),
        ocrTitle: selected.ocrTitle ?? fallback.ocrTitle ?? 'Image OCR Translation',
        ocrSubtitle: selected.ocrSubtitle ?? fallback.ocrSubtitle ?? 'Pick an image to extract text and translate it.',
        ocrPickImage: selected.ocrPickImage ?? fallback.ocrPickImage ?? '🖼️ Pick image',
        ocrLoading: selected.ocrLoading ?? fallback.ocrLoading ?? 'Running OCR...',
        ocrExtractedTitle: selected.ocrExtractedTitle ?? fallback.ocrExtractedTitle ?? 'OCR Extracted Text',
        ocrTranslatedTitle: selected.ocrTranslatedTitle ?? fallback.ocrTranslatedTitle ?? 'OCR Translation Result',
        ocrSelectedFile: selected.ocrSelectedFile ?? fallback.ocrSelectedFile ?? 'Selected file: {file}',
        ocrErrorMsg: selected.ocrErrorMsg ?? fallback.ocrErrorMsg ?? 'Image OCR failed. Please try again.',
        autoVoiceSegmentStatus: selected.autoVoiceSegmentStatus ?? fallback.autoVoiceSegmentStatus ?? '🎙️ Auto voice translation: processing in {delay} chunks.',
        autoVoiceDuplicateSkipped: selected.autoVoiceDuplicateSkipped ?? fallback.autoVoiceDuplicateSkipped ?? '↺ Duplicate sentence skipped to prevent repeated auto translation.',
        autoVoiceDetected: selected.autoVoiceDetected ?? fallback.autoVoiceDetected ?? '🎙️ Auto-detected: {from} → {to}',
        autoVoiceModeStopped: selected.autoVoiceModeStopped ?? fallback.autoVoiceModeStopped ?? '🎙️ Auto voice translation mode has stopped.',
        autoVoiceModeStarted: selected.autoVoiceModeStarted ?? fallback.autoVoiceModeStarted ?? '🎙️ Auto voice translation mode started ({delay} interval)',
        manualVoiceOnlyNotice: selected.manualVoiceOnlyNotice ?? fallback.manualVoiceOnlyNotice ?? '🎤 Recording starts only when you press the mic. Select both source and target languages manually.',
        manualLanguageHint: selected.manualLanguageHint ?? fallback.manualLanguageHint ?? 'Manual selection',
        profileLanguageLabel: selected.profileLanguageLabel ?? fallback.profileLanguageLabel ?? 'My language (profile)',
        profileLanguageHint: selected.profileLanguageHint ?? fallback.profileLanguageHint ?? 'Saved in profile',
        peerLanguageLabel: selected.peerLanguageLabel ?? fallback.peerLanguageLabel ?? 'Peer language (GPS/manual)',
        peerLanguageHint: selected.peerLanguageHint ?? fallback.peerLanguageHint ?? 'GPS first · manual override',
        faceConversationOn: selected.faceConversationOn ?? fallback.faceConversationOn ?? '🎙️ Conversation ON',
        faceConversationOff: selected.faceConversationOff ?? fallback.faceConversationOff ?? 'Conversation OFF',
        faceConversationPeerRequired: selected.faceConversationPeerRequired ?? fallback.faceConversationPeerRequired ?? 'Set the peer language via GPS or manual selection.',
        faceListenProcessing: selected.faceListenProcessing ?? fallback.faceListenProcessing ?? '🔄 Translating & speaking...',
        faceSpeakingStatus: selected.faceSpeakingStatus ?? fallback.faceSpeakingStatus ?? '🔊 Speaking translation · listening paused',
        faceVadHint: selected.faceVadHint ?? fallback.faceVadHint ?? 'The mic stays on until you finish speaking.',
        interAutoRelayDuplicateSkipped: selected.interAutoRelayDuplicateSkipped ?? fallback.interAutoRelayDuplicateSkipped ?? '↺ Duplicate sentence skipped to prevent repeated auto relay.',
        interAutoRelayPending: selected.interAutoRelayPending ?? fallback.interAutoRelayPending ?? '⏱️ Auto relay after {delay} of no input',
        voipIncomingTitle: selected.voipIncomingTitle ?? fallback.voipIncomingTitle ?? '📞 Incoming voice call',
        voipIncomingAccept: selected.voipIncomingAccept ?? fallback.voipIncomingAccept ?? 'Accept',
        voipIncomingReject: selected.voipIncomingReject ?? fallback.voipIncomingReject ?? 'Decline',
        voipIncomingConnecting: selected.voipIncomingConnecting ?? fallback.voipIncomingConnecting ?? 'Connecting to server… please wait',
    };
}
