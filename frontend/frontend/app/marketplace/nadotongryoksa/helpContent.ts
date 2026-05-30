/**
 * WorldLinco – 사용설명 도움말 콘텐츠 사전
 *
 * 50개 언어 코드를 커버합니다. 미번역 언어는 영어(en)로 폴백됩니다.
 * 범위: 모바일 웹앱 시각적 사용설명 전용 (전체 UI 번역 아님)
 */

export type HelpLangCode = string;

export interface HelpCard {
    icon: string;
    title: string;
    body: string;
}

export interface HelpContent {
    panelTitle: string;
    langSelectorLabel: string;
    closeLabel: string;
    cards: HelpCard[];
}

const HELP_EN: HelpContent = {
    panelTitle: '📖 How to Use WorldLinco',
    langSelectorLabel: 'Help language',
    closeLabel: 'Close',
    cards: [
        {
            icon: '🌐',
            title: 'Text Translation',
            body: 'Select source & target languages, type or paste text, then tap Translate (or Ctrl+Enter). Results appear instantly.',
        },
        {
            icon: '🎤',
            title: 'Voice Input',
            body: 'Tap the 🎤 button, speak in the source language, and your speech will be transcribed automatically.',
        },
        {
            icon: '📡',
            title: 'GPS Language Detection',
            body: 'Tap "GPS Language Detect" to auto-set the target language based on your current location.',
        },
        {
            icon: '📞',
            title: 'Interpreter Call Mode',
            body: 'Tap "Interpreter Call" to enable real-time two-way voice interpretation — each side speaks in turn and hears the translated output.',
        },
        {
            icon: '📍',
            title: 'Nearby Places Search',
            body: 'Enter your latitude/longitude or tap "Use Current Location", choose a category and radius, then tap "Find Nearby" to see hotels, airports, restaurants, and attractions.',
        },
        {
            icon: '🏨',
            title: 'Hotel Booking',
            body: 'Select a bookable hotel from nearby results, fill in dates and guest count, then tap "Send Booking Request". A confirmation ID will be returned.',
        },
        {
            icon: '💳',
            title: 'Payment',
            body: 'After receiving your booking confirmation, tap "Proceed to Payment" to open the secure payment page. Login is required.',
        },
        {
            icon: '📱',
            title: 'Mobile App Install',
            body: 'Download the APK for the full offline experience on Android. Login required for download.',
        },
    ],
};

const HELP_KO: HelpContent = {
    panelTitle: '📖 WorldLinco 사용 방법',
    langSelectorLabel: '도움말 언어',
    closeLabel: '닫기',
    cards: [
        {
            icon: '🌐',
            title: '텍스트 번역',
            body: '원본·번역 언어를 선택하고, 텍스트를 입력한 뒤 "번역" 버튼(또는 Ctrl+Enter)을 누르세요. 결과가 바로 표시됩니다.',
        },
        {
            icon: '🎤',
            title: '음성 입력',
            body: '🎤 버튼을 탭하여 원본 언어로 말하면 음성이 자동으로 텍스트로 변환됩니다.',
        },
        {
            icon: '📡',
            title: 'GPS 언어 감지',
            body: '"GPS 언어 감지" 버튼을 누르면 현재 위치를 기반으로 번역 대상 언어가 자동 설정됩니다.',
        },
        {
            icon: '📞',
            title: '통역 통화 모드',
            body: '"통역 통화 시작"을 누르면 실시간 양방향 음성 통역이 시작됩니다. 서로 번갈아 말하면 번역 결과가 음성으로 출력됩니다.',
        },
        {
            icon: '📍',
            title: '주변 장소 검색',
            body: '위도·경도를 입력하거나 "현재 위치 사용"을 탭한 뒤, 카테고리와 반경을 선택하고 "주변 장소 찾기"를 누르세요.',
        },
        {
            icon: '🏨',
            title: '호텔 예약',
            body: '주변 검색 결과에서 예약 가능한 호텔을 선택하고, 날짜·인원을 입력한 뒤 "예약 요청 보내기"를 탭하세요. 예약 확인번호가 발급됩니다.',
        },
        {
            icon: '💳',
            title: '결제',
            body: '예약 확인 후 "결제 진행하기"를 누르면 안전한 결제 페이지로 이동합니다. 로그인이 필요합니다.',
        },
        {
            icon: '📱',
            title: '모바일 앱 설치',
            body: '안드로이드 기기에 APK를 설치하면 오프라인 환경에서도 사용 가능합니다. 다운로드는 로그인 후 이용 가능합니다.',
        },
    ],
};

const HELP_JA: HelpContent = {
    panelTitle: '📖 WorldLinco の使い方',
    langSelectorLabel: 'ヘルプ言語',
    closeLabel: '閉じる',
    cards: [
        {
            icon: '🌐',
            title: 'テキスト翻訳',
            body: '原文・翻訳言語を選択し、テキストを入力して「翻訳」ボタン（またはCtrl+Enter）をタップしてください。',
        },
        {
            icon: '🎤',
            title: '音声入力',
            body: '🎤 ボタンをタップして原文言語で話すと、音声が自動的にテキストに変換されます。',
        },
        {
            icon: '📡',
            title: 'GPS言語検出',
            body: '「GPS言語検出」ボタンをタップすると、現在地に基づいて翻訳先言語が自動設定されます。',
        },
        {
            icon: '📞',
            title: '通訳通話モード',
            body: '「通訳通話開始」をタップするとリアルタイム双方向音声通訳が始まります。交互に話すと翻訳結果が音声で流れます。',
        },
        {
            icon: '📍',
            title: '周辺施設検索',
            body: '緯度・経度を入力するか「現在地を使用」をタップし、カテゴリと半径を選んで「周辺を検索」をタップしてください。',
        },
        {
            icon: '🏨',
            title: 'ホテル予約',
            body: '検索結果から予約可能なホテルを選び、日程・人数を入力して「予約リクエスト送信」をタップしてください。',
        },
        {
            icon: '💳',
            title: '決済',
            body: '予約確認後、「決済を進める」をタップして安全な決済ページへ移動します。ログインが必要です。',
        },
        {
            icon: '📱',
            title: 'モバイルアプリのインストール',
            body: 'AndroidデバイスにAPKをインストールするとオフラインでも使用可能です。ダウンロードにはログインが必要です。',
        },
    ],
};

const HELP_ZH: HelpContent = {
    panelTitle: '📖 WorldLinco 使用指南',
    langSelectorLabel: '帮助语言',
    closeLabel: '关闭',
    cards: [
        {
            icon: '🌐',
            title: '文本翻译',
            body: '选择原文语言和目标语言，输入文本后点击"翻译"按钮（或按 Ctrl+Enter）即可获得翻译结果。',
        },
        {
            icon: '🎤',
            title: '语音输入',
            body: '点击 🎤 按钮，用原文语言说话，语音将自动转换为文本。',
        },
        {
            icon: '📡',
            title: 'GPS 语言检测',
            body: '点击"GPS 语言检测"按钮，系统将根据您的当前位置自动设置目标语言。',
        },
        {
            icon: '📞',
            title: '口译通话模式',
            body: '点击"开始口译通话"，启动实时双向语音口译。双方交替说话，翻译结果将以语音输出。',
        },
        {
            icon: '📍',
            title: '附近搜索',
            body: '输入经纬度或点击"使用当前位置"，选择类别和半径，点击"查找附近"即可搜索酒店、机场、餐厅和景点。',
        },
        {
            icon: '🏨',
            title: '酒店预订',
            body: '从搜索结果中选择可预订的酒店，填写日期和人数，点击"发送预订请求"即可获得预订确认号。',
        },
        {
            icon: '💳',
            title: '支付',
            body: '收到预订确认后，点击"进行支付"前往安全的支付页面。需要登录。',
        },
        {
            icon: '📱',
            title: '手机端安装',
            body: '在 Android 设备上安装 APK 后，即可在离线环境中使用。下载需要登录。',
        },
    ],
};

const HELP_ZH_TW: HelpContent = {
    panelTitle: '📖 WorldLinco 使用指南',
    langSelectorLabel: '說明語言',
    closeLabel: '關閉',
    cards: [
        {
            icon: '🌐',
            title: '文字翻譯',
            body: '選擇來源語言和目標語言，輸入文字後點擊「翻譯」按鈕（或按 Ctrl+Enter）即可取得翻譯結果。',
        },
        {
            icon: '🎤',
            title: '語音輸入',
            body: '點擊 🎤 按鈕，使用來源語言說話，語音將自動轉換為文字。',
        },
        {
            icon: '📡',
            title: 'GPS 語言偵測',
            body: '點擊「GPS 語言偵測」按鈕，系統將根據您目前的位置自動設定目標語言。',
        },
        {
            icon: '📞',
            title: '口譯通話模式',
            body: '點擊「開始口譯通話」，啟動即時雙向語音口譯。雙方輪流說話，翻譯結果將以語音輸出。',
        },
        {
            icon: '📍',
            title: '附近搜尋',
            body: '輸入經緯度或點擊「使用目前位置」，選擇類別和範圍，點擊「搜尋附近」即可查找飯店、機場、餐廳和景點。',
        },
        {
            icon: '🏨',
            title: '飯店預訂',
            body: '從搜尋結果中選擇可預訂的飯店，填寫日期和人數，點擊「發送預訂請求」即可取得預訂確認號。',
        },
        {
            icon: '💳',
            title: '付款',
            body: '收到預訂確認後，點擊「進行付款」前往安全付款頁面。需要登入。',
        },
        {
            icon: '📱',
            title: '手機端安裝',
            body: '在 Android 裝置上安裝 APK 後，可在離線環境中使用。下載需要登入。',
        },
    ],
};

const HELP_ES: HelpContent = {
    panelTitle: '📖 Cómo usar WorldLinco',
    langSelectorLabel: 'Idioma de ayuda',
    closeLabel: 'Cerrar',
    cards: [
        {
            icon: '🌐',
            title: 'Traducción de texto',
            body: 'Selecciona los idiomas de origen y destino, escribe el texto y pulsa "Traducir" (o Ctrl+Enter). El resultado aparece al instante.',
        },
        {
            icon: '🎤',
            title: 'Entrada de voz',
            body: 'Toca el botón 🎤 y habla en el idioma de origen para convertir tu voz en texto automáticamente.',
        },
        {
            icon: '📡',
            title: 'Detección de idioma por GPS',
            body: 'Pulsa "Detectar idioma GPS" para establecer automáticamente el idioma de destino según tu ubicación actual.',
        },
        {
            icon: '📞',
            title: 'Modo interpretación de llamada',
            body: 'Pulsa "Iniciar llamada de interpretación" para activar la interpretación de voz bidireccional en tiempo real.',
        },
        {
            icon: '📍',
            title: 'Búsqueda de lugares cercanos',
            body: 'Introduce tus coordenadas o pulsa "Usar ubicación actual", elige categoría y radio, luego pulsa "Buscar lugares cercanos".',
        },
        {
            icon: '🏨',
            title: 'Reserva de hotel',
            body: 'Selecciona un hotel disponible en los resultados cercanos, rellena las fechas y el número de personas, y pulsa "Enviar solicitud de reserva".',
        },
        {
            icon: '💳',
            title: 'Pago',
            body: 'Tras recibir la confirmación de reserva, pulsa "Proceder al pago" para ir a la página de pago segura. Se requiere inicio de sesión.',
        },
        {
            icon: '📱',
            title: 'Instalación de la app móvil',
            body: 'Descarga el APK para usarlo sin conexión en Android. Se requiere inicio de sesión para descargarlo.',
        },
    ],
};

const HELP_FR: HelpContent = {
    panelTitle: '📖 Comment utiliser WorldLinco',
    langSelectorLabel: "Langue de l'aide",
    closeLabel: 'Fermer',
    cards: [
        {
            icon: '🌐',
            title: 'Traduction de texte',
            body: "Sélectionnez les langues source et cible, saisissez le texte, puis appuyez sur « Traduire » (ou Ctrl+Entrée).",
        },
        {
            icon: '🎤',
            title: 'Entrée vocale',
            body: "Appuyez sur le bouton 🎤 et parlez dans la langue source pour transcrire automatiquement votre voix en texte.",
        },
        {
            icon: '📡',
            title: 'Détection de langue par GPS',
            body: "Appuyez sur « Détecter la langue GPS » pour définir automatiquement la langue cible en fonction de votre position actuelle.",
        },
        {
            icon: '📞',
            title: 'Mode appel interprète',
            body: "Appuyez sur « Démarrer l'appel interprète » pour activer l'interprétation vocale bidirectionnelle en temps réel.",
        },
        {
            icon: '📍',
            title: 'Recherche de lieux proches',
            body: "Saisissez vos coordonnées ou appuyez sur « Utiliser ma position », choisissez une catégorie et un rayon, puis appuyez sur « Rechercher à proximité ».",
        },
        {
            icon: '🏨',
            title: "Réservation d'hôtel",
            body: "Sélectionnez un hôtel réservable dans les résultats, renseignez les dates et le nombre de personnes, puis appuyez sur « Envoyer la demande de réservation ».",
        },
        {
            icon: '💳',
            title: 'Paiement',
            body: "Après confirmation de la réservation, appuyez sur « Procéder au paiement » pour accéder à la page de paiement sécurisée. Connexion requise.",
        },
        {
            icon: '📱',
            title: "Installation de l'application mobile",
            body: "Téléchargez l'APK pour une utilisation hors ligne sur Android. Connexion requise pour le téléchargement.",
        },
    ],
};

const HELP_DE: HelpContent = {
    panelTitle: '📖 So verwendest du WorldLinco',
    langSelectorLabel: 'Hilfesprache',
    closeLabel: 'Schließen',
    cards: [
        {
            icon: '🌐',
            title: 'Textübersetzung',
            body: 'Wähle Ausgangs- und Zielsprache, gib Text ein und klicke auf „Übersetzen" (oder Strg+Eingabe).',
        },
        {
            icon: '🎤',
            title: 'Spracheingabe',
            body: 'Tippe auf die Schaltfläche 🎤 und sprich in der Ausgangssprache – deine Stimme wird automatisch in Text umgewandelt.',
        },
        {
            icon: '📡',
            title: 'GPS-Spracherkennung',
            body: 'Tippe auf „GPS-Sprache erkennen", um die Zielsprache basierend auf deinem aktuellen Standort automatisch einzustellen.',
        },
        {
            icon: '📞',
            title: 'Dolmetsch-Anrufmodus',
            body: 'Tippe auf „Dolmetsch-Anruf starten" für eine bidirektionale Echtzeit-Sprachdolmetschung.',
        },
        {
            icon: '📍',
            title: 'Suche nach nahegelegenen Orten',
            body: 'Gib deine Koordinaten ein oder tippe auf „Aktuellen Standort verwenden", wähle eine Kategorie und einen Radius, dann tippe auf „In der Nähe suchen".',
        },
        {
            icon: '🏨',
            title: 'Hotelbuchung',
            body: 'Wähle ein buchbares Hotel aus den Ergebnissen, trage Datum und Personenzahl ein und tippe auf „Buchungsanfrage senden".',
        },
        {
            icon: '💳',
            title: 'Zahlung',
            body: 'Nach Erhalt der Buchungsbestätigung auf „Zur Zahlung" tippen, um zur sicheren Zahlungsseite zu gelangen. Anmeldung erforderlich.',
        },
        {
            icon: '📱',
            title: 'Mobile App installieren',
            body: 'Lade die APK herunter, um die App offline auf Android zu nutzen. Download erfordert Anmeldung.',
        },
    ],
};

const HELP_PT: HelpContent = {
    panelTitle: '📖 Como usar o WorldLinco',
    langSelectorLabel: 'Idioma da ajuda',
    closeLabel: 'Fechar',
    cards: [
        {
            icon: '🌐',
            title: 'Tradução de texto',
            body: 'Selecione os idiomas de origem e destino, digite o texto e toque em "Traduzir" (ou Ctrl+Enter).',
        },
        {
            icon: '🎤',
            title: 'Entrada de voz',
            body: 'Toque no botão 🎤 e fale no idioma de origem para converter sua voz em texto automaticamente.',
        },
        {
            icon: '📡',
            title: 'Detecção de idioma por GPS',
            body: 'Toque em "Detectar idioma GPS" para definir automaticamente o idioma de destino com base na sua localização.',
        },
        {
            icon: '📞',
            title: 'Modo chamada de intérprete',
            body: 'Toque em "Iniciar chamada de intérprete" para ativar a interpretação de voz bidirecional em tempo real.',
        },
        {
            icon: '📍',
            title: 'Pesquisa de locais próximos',
            body: 'Insira suas coordenadas ou toque em "Usar localização atual", escolha uma categoria e um raio, e toque em "Buscar locais próximos".',
        },
        {
            icon: '🏨',
            title: 'Reserva de hotel',
            body: 'Selecione um hotel disponível nos resultados, preencha as datas e o número de hóspedes, e toque em "Enviar solicitação de reserva".',
        },
        {
            icon: '💳',
            title: 'Pagamento',
            body: 'Após a confirmação da reserva, toque em "Prosseguir para pagamento" para ir à página de pagamento seguro. É necessário login.',
        },
        {
            icon: '📱',
            title: 'Instalação do aplicativo móvel',
            body: 'Baixe o APK para usar offline no Android. Login necessário para download.',
        },
    ],
};

const HELP_RU: HelpContent = {
    panelTitle: '📖 Как использовать WorldLinco',
    langSelectorLabel: 'Язык справки',
    closeLabel: 'Закрыть',
    cards: [
        {
            icon: '🌐',
            title: 'Перевод текста',
            body: 'Выберите язык оригинала и язык перевода, введите текст и нажмите «Перевести» (или Ctrl+Enter).',
        },
        {
            icon: '🎤',
            title: 'Голосовой ввод',
            body: 'Нажмите кнопку 🎤 и говорите на исходном языке — речь будет автоматически преобразована в текст.',
        },
        {
            icon: '📡',
            title: 'Определение языка по GPS',
            body: 'Нажмите «Определить язык по GPS», чтобы автоматически установить язык перевода по вашему текущему местоположению.',
        },
        {
            icon: '📞',
            title: 'Режим звонка с переводчиком',
            body: 'Нажмите «Начать звонок с переводчиком» для двустороннего перевода речи в реальном времени.',
        },
        {
            icon: '📍',
            title: 'Поиск ближайших мест',
            body: 'Введите координаты или нажмите «Использовать текущее местоположение», выберите категорию и радиус, затем нажмите «Найти рядом».',
        },
        {
            icon: '🏨',
            title: 'Бронирование отеля',
            body: 'Выберите отель из результатов поиска, укажите даты и количество гостей и нажмите «Отправить запрос на бронирование».',
        },
        {
            icon: '💳',
            title: 'Оплата',
            body: 'После подтверждения бронирования нажмите «Перейти к оплате», чтобы открыть страницу безопасной оплаты. Требуется вход в систему.',
        },
        {
            icon: '📱',
            title: 'Установка мобильного приложения',
            body: 'Скачайте APK для офлайн-использования на Android. Для скачивания требуется вход в систему.',
        },
    ],
};

const HELP_AR: HelpContent = {
    panelTitle: '📖 كيفية استخدام WorldLinco',
    langSelectorLabel: 'لغة المساعدة',
    closeLabel: 'إغلاق',
    cards: [
        {
            icon: '🌐',
            title: 'ترجمة النص',
            body: 'اختر لغة المصدر ولغة الهدف، أدخل النص، ثم انقر على "ترجمة" (أو Ctrl+Enter).',
        },
        {
            icon: '🎤',
            title: 'الإدخال الصوتي',
            body: 'انقر على زر 🎤 وتحدث باللغة المصدر ليتم تحويل صوتك إلى نص تلقائياً.',
        },
        {
            icon: '📡',
            title: 'الكشف عن اللغة عبر GPS',
            body: 'انقر على "كشف لغة GPS" لضبط لغة الهدف تلقائياً بناءً على موقعك الحالي.',
        },
        {
            icon: '📞',
            title: 'وضع المكالمة مع مترجم',
            body: 'انقر على "بدء مكالمة الترجمة" لتفعيل الترجمة الصوتية الثنائية الاتجاه في الوقت الفعلي.',
        },
        {
            icon: '📍',
            title: 'البحث عن الأماكن القريبة',
            body: 'أدخل إحداثياتك أو انقر على "استخدام الموقع الحالي"، اختر الفئة والنطاق، ثم انقر على "البحث بالقرب".',
        },
        {
            icon: '🏨',
            title: 'حجز الفندق',
            body: 'اختر فندقاً متاحاً من نتائج البحث، أدخل التواريخ وعدد الضيوف، ثم انقر على "إرسال طلب الحجز".',
        },
        {
            icon: '💳',
            title: 'الدفع',
            body: 'بعد تأكيد الحجز، انقر على "المتابعة للدفع" للانتقال إلى صفحة الدفع الآمنة. يلزم تسجيل الدخول.',
        },
        {
            icon: '📱',
            title: 'تثبيت التطبيق على الهاتف',
            body: 'حمّل ملف APK للاستخدام دون إنترنت على أجهزة Android. يلزم تسجيل الدخول للتنزيل.',
        },
    ],
};

const HELP_HI: HelpContent = {
    panelTitle: '📖 WorldLinco का उपयोग कैसे करें',
    langSelectorLabel: 'सहायता भाषा',
    closeLabel: 'बंद करें',
    cards: [
        {
            icon: '🌐',
            title: 'टेक्स्ट अनुवाद',
            body: 'स्रोत और लक्ष्य भाषाएँ चुनें, टेक्स्ट टाइप करें और "अनुवाद करें" (या Ctrl+Enter) दबाएँ।',
        },
        {
            icon: '🎤',
            title: 'वॉइस इनपुट',
            body: '🎤 बटन दबाएँ और स्रोत भाषा में बोलें — आपकी आवाज़ स्वतः टेक्स्ट में बदल जाएगी।',
        },
        {
            icon: '📡',
            title: 'GPS भाषा पहचान',
            body: '"GPS भाषा पहचान" दबाएँ और आपके वर्तमान स्थान के आधार पर लक्ष्य भाषा स्वतः सेट हो जाएगी।',
        },
        {
            icon: '📞',
            title: 'इंटरप्रेटर कॉल मोड',
            body: '"इंटरप्रेटर कॉल शुरू करें" दबाएँ और रियल-टाइम में दो-तरफ़ा वॉइस अनुवाद का उपयोग करें।',
        },
        {
            icon: '📍',
            title: 'नज़दीकी स्थान खोज',
            body: 'अक्षांश-देशांतर दर्ज करें या "वर्तमान स्थान उपयोग करें" दबाएँ, श्रेणी और दायरा चुनें, फिर "नज़दीकी खोज" दबाएँ।',
        },
        {
            icon: '🏨',
            title: 'होटल बुकिंग',
            body: 'खोज परिणामों से होटल चुनें, तारीखें और अतिथि संख्या भरें, फिर "बुकिंग अनुरोध भेजें" दबाएँ।',
        },
        {
            icon: '💳',
            title: 'भुगतान',
            body: 'बुकिंग पुष्टि के बाद "भुगतान जारी रखें" दबाएँ। लॉगिन आवश्यक है।',
        },
        {
            icon: '📱',
            title: 'मोबाइल ऐप इंस्टॉल',
            body: 'Android पर ऑफलाइन उपयोग के लिए APK डाउनलोड करें। डाउनलोड के लिए लॉगिन आवश्यक है।',
        },
    ],
};

const HELP_IT: HelpContent = {
    panelTitle: '📖 Come usare WorldLinco',
    langSelectorLabel: 'Lingua della guida',
    closeLabel: 'Chiudi',
    cards: [
        {
            icon: '🌐',
            title: 'Traduzione testo',
            body: 'Seleziona le lingue di origine e di destinazione, inserisci il testo e tocca "Traduci" (o Ctrl+Invio).',
        },
        {
            icon: '🎤',
            title: 'Inserimento vocale',
            body: 'Tocca il pulsante 🎤 e parla nella lingua di origine per convertire automaticamente la voce in testo.',
        },
        {
            icon: '📡',
            title: 'Rilevamento lingua GPS',
            body: 'Tocca "Rileva lingua GPS" per impostare automaticamente la lingua di destinazione in base alla tua posizione attuale.',
        },
        {
            icon: '📞',
            title: 'Modalità chiamata interprete',
            body: 'Tocca "Avvia chiamata interprete" per attivare l\'interpretazione vocale bidirezionale in tempo reale.',
        },
        {
            icon: '📍',
            title: 'Ricerca luoghi nelle vicinanze',
            body: 'Inserisci le coordinate o tocca "Usa posizione corrente", scegli una categoria e un raggio, poi tocca "Cerca vicino".',
        },
        {
            icon: '🏨',
            title: 'Prenotazione hotel',
            body: 'Seleziona un hotel prenotabile dai risultati, inserisci le date e il numero di ospiti, poi tocca "Invia richiesta di prenotazione".',
        },
        {
            icon: '💳',
            title: 'Pagamento',
            body: 'Dopo la conferma della prenotazione, tocca "Procedi al pagamento". È richiesto l\'accesso.',
        },
        {
            icon: '📱',
            title: 'Installazione app mobile',
            body: 'Scarica l\'APK per l\'uso offline su Android. È richiesto l\'accesso per il download.',
        },
    ],
};

const HELP_TR: HelpContent = {
    panelTitle: '📖 WorldLinco Nasıl Kullanılır',
    langSelectorLabel: 'Yardım dili',
    closeLabel: 'Kapat',
    cards: [
        {
            icon: '🌐',
            title: 'Metin Çevirisi',
            body: 'Kaynak ve hedef dilleri seçin, metin girin ve "Çevir" (veya Ctrl+Enter) düğmesine basın.',
        },
        {
            icon: '🎤',
            title: 'Sesli Giriş',
            body: '🎤 düğmesine dokunun ve kaynak dilde konuşun — sesiniz otomatik olarak metne dönüştürülür.',
        },
        {
            icon: '📡',
            title: 'GPS Dil Algılama',
            body: '"GPS Dil Algıla" düğmesine basın; mevcut konumunuza göre hedef dil otomatik ayarlanır.',
        },
        {
            icon: '📞',
            title: 'Tercüman Arama Modu',
            body: '"Tercüman Aramasını Başlat" düğmesine basın; gerçek zamanlı iki yönlü sesli tercüme başlar.',
        },
        {
            icon: '📍',
            title: 'Yakın Yer Arama',
            body: 'Koordinatlarınızı girin veya "Mevcut Konumu Kullan" düğmesine dokunun, kategori ve yarıçapı seçin, ardından "Yakın Yerleri Bul"a basın.',
        },
        {
            icon: '🏨',
            title: 'Otel Rezervasyonu',
            body: 'Arama sonuçlarından bir otel seçin, tarih ve misafir sayısını girin, ardından "Rezervasyon İsteği Gönder"e dokunun.',
        },
        {
            icon: '💳',
            title: 'Ödeme',
            body: 'Rezervasyon onayından sonra "Ödemeye Devam Et" düğmesine basın. Giriş gereklidir.',
        },
        {
            icon: '📱',
            title: 'Mobil Uygulama Yükleme',
            body: 'Android\'de çevrimdışı kullanım için APK indirin. İndirmek için giriş gereklidir.',
        },
    ],
};

const HELP_VI: HelpContent = {
    panelTitle: '📖 Cách sử dụng WorldLinco',
    langSelectorLabel: 'Ngôn ngữ trợ giúp',
    closeLabel: 'Đóng',
    cards: [
        {
            icon: '🌐',
            title: 'Dịch văn bản',
            body: 'Chọn ngôn ngữ nguồn và đích, nhập văn bản rồi nhấn "Dịch" (hoặc Ctrl+Enter).',
        },
        {
            icon: '🎤',
            title: 'Nhập bằng giọng nói',
            body: 'Nhấn nút 🎤 và nói bằng ngôn ngữ nguồn để chuyển giọng nói thành văn bản tự động.',
        },
        {
            icon: '📡',
            title: 'Phát hiện ngôn ngữ qua GPS',
            body: 'Nhấn "Phát hiện ngôn ngữ GPS" để tự động đặt ngôn ngữ đích dựa trên vị trí hiện tại của bạn.',
        },
        {
            icon: '📞',
            title: 'Chế độ gọi phiên dịch',
            body: 'Nhấn "Bắt đầu gọi phiên dịch" để kích hoạt phiên dịch giọng nói hai chiều theo thời gian thực.',
        },
        {
            icon: '📍',
            title: 'Tìm kiếm địa điểm gần đây',
            body: 'Nhập tọa độ hoặc nhấn "Dùng vị trí hiện tại", chọn danh mục và bán kính rồi nhấn "Tìm địa điểm gần đây".',
        },
        {
            icon: '🏨',
            title: 'Đặt phòng khách sạn',
            body: 'Chọn khách sạn từ kết quả tìm kiếm, điền ngày và số khách rồi nhấn "Gửi yêu cầu đặt phòng".',
        },
        {
            icon: '💳',
            title: 'Thanh toán',
            body: 'Sau khi nhận xác nhận đặt phòng, nhấn "Tiến hành thanh toán" để chuyển đến trang thanh toán an toàn. Cần đăng nhập.',
        },
        {
            icon: '📱',
            title: 'Cài đặt ứng dụng di động',
            body: 'Tải APK để dùng ngoại tuyến trên Android. Cần đăng nhập để tải xuống.',
        },
    ],
};

const HELP_TH: HelpContent = {
    panelTitle: '📖 วิธีใช้ WorldLinco',
    langSelectorLabel: 'ภาษาช่วยเหลือ',
    closeLabel: 'ปิด',
    cards: [
        {
            icon: '🌐',
            title: 'การแปลข้อความ',
            body: 'เลือกภาษาต้นทางและภาษาปลายทาง พิมพ์ข้อความ แล้วกด "แปล" (หรือ Ctrl+Enter)',
        },
        {
            icon: '🎤',
            title: 'การป้อนเสียง',
            body: 'แตะปุ่ม 🎤 แล้วพูดในภาษาต้นทาง เสียงของคุณจะถูกแปลงเป็นข้อความโดยอัตโนมัติ',
        },
        {
            icon: '📡',
            title: 'การตรวจจับภาษาด้วย GPS',
            body: 'แตะ "ตรวจจับภาษา GPS" เพื่อตั้งค่าภาษาปลายทางโดยอัตโนมัติตามตำแหน่งปัจจุบันของคุณ',
        },
        {
            icon: '📞',
            title: 'โหมดโทรล่าม',
            body: 'แตะ "เริ่มโทรล่าม" เพื่อเปิดใช้งานการแปลเสียงสองทิศทางแบบเรียลไทม์',
        },
        {
            icon: '📍',
            title: 'ค้นหาสถานที่ใกล้เคียง',
            body: 'ป้อนพิกัดหรือแตะ "ใช้ตำแหน่งปัจจุบัน" เลือกหมวดหมู่และรัศมี แล้วแตะ "ค้นหาสถานที่ใกล้เคียง"',
        },
        {
            icon: '🏨',
            title: 'จองโรงแรม',
            body: 'เลือกโรงแรมที่พร้อมจองจากผลการค้นหา กรอกวันที่และจำนวนผู้เข้าพัก แล้วแตะ "ส่งคำขอจอง"',
        },
        {
            icon: '💳',
            title: 'การชำระเงิน',
            body: 'หลังจากได้รับการยืนยันการจอง แตะ "ดำเนินการชำระเงิน" เพื่อไปยังหน้าชำระเงินที่ปลอดภัย ต้องเข้าสู่ระบบ',
        },
        {
            icon: '📱',
            title: 'ติดตั้งแอปมือถือ',
            body: 'ดาวน์โหลด APK เพื่อใช้งานออฟไลน์บน Android ต้องเข้าสู่ระบบเพื่อดาวน์โหลด',
        },
    ],
};

const HELP_ID: HelpContent = {
    panelTitle: '📖 Cara Menggunakan WorldLinco',
    langSelectorLabel: 'Bahasa bantuan',
    closeLabel: 'Tutup',
    cards: [
        {
            icon: '🌐',
            title: 'Terjemahan Teks',
            body: 'Pilih bahasa sumber dan tujuan, masukkan teks, lalu ketuk "Terjemahkan" (atau Ctrl+Enter).',
        },
        {
            icon: '🎤',
            title: 'Input Suara',
            body: 'Ketuk tombol 🎤 dan berbicara dalam bahasa sumber untuk mengubah suara menjadi teks secara otomatis.',
        },
        {
            icon: '📡',
            title: 'Deteksi Bahasa GPS',
            body: 'Ketuk "Deteksi Bahasa GPS" untuk mengatur bahasa tujuan secara otomatis berdasarkan lokasi Anda saat ini.',
        },
        {
            icon: '📞',
            title: 'Mode Panggilan Penerjemah',
            body: 'Ketuk "Mulai Panggilan Penerjemah" untuk mengaktifkan interpretasi suara dua arah secara real-time.',
        },
        {
            icon: '📍',
            title: 'Pencarian Tempat Terdekat',
            body: 'Masukkan koordinat atau ketuk "Gunakan Lokasi Saat Ini", pilih kategori dan radius, lalu ketuk "Cari Terdekat".',
        },
        {
            icon: '🏨',
            title: 'Pemesanan Hotel',
            body: 'Pilih hotel yang tersedia dari hasil pencarian, isi tanggal dan jumlah tamu, lalu ketuk "Kirim Permintaan Pemesanan".',
        },
        {
            icon: '💳',
            title: 'Pembayaran',
            body: 'Setelah konfirmasi pemesanan, ketuk "Lanjutkan Pembayaran" untuk membuka halaman pembayaran aman. Diperlukan login.',
        },
        {
            icon: '📱',
            title: 'Pemasangan Aplikasi Mobile',
            body: 'Unduh APK untuk penggunaan offline di Android. Diperlukan login untuk mengunduh.',
        },
    ],
};

/** Supported help language codes with pre-translated content */
const HELP_DICT: Record<string, HelpContent> = {
    ko: HELP_KO,
    en: HELP_EN,
    ja: HELP_JA,
    zh: HELP_ZH,
    'zh-tw': HELP_ZH_TW,
    es: HELP_ES,
    fr: HELP_FR,
    de: HELP_DE,
    pt: HELP_PT,
    ru: HELP_RU,
    ar: HELP_AR,
    hi: HELP_HI,
    it: HELP_IT,
    tr: HELP_TR,
    vi: HELP_VI,
    th: HELP_TH,
    id: HELP_ID,
};

/** Returns the help content for the given language code, falling back to English. */
export function getHelpContent(langCode: string): HelpContent {
    const normalized = langCode.toLowerCase();
    return HELP_DICT[normalized] ?? HELP_DICT['en'];
}

/** All language codes that have full pre-translated help content */
export const HELP_SUPPORTED_LANGS = Object.keys(HELP_DICT);
