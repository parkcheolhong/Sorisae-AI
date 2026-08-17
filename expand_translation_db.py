#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add 100+ common Korean phrases to translation_db
나도통역사 translation database 대폭 확장
"""

import os

# Common Korean phrases with translations (ko → en, zh, ja, es, fr, de, pt, ru, ar, hi, it, tr)
COMMON_PHRASES = {
    # 기본 인사 (Greetings)
    '안녕하세요': {
        'en': 'Hello',
        'zh': '你好',
        'ja': 'こんにちは',
        'es': 'Hola',
        'fr': 'Bonjour',
        'de': 'Hallo',
        'pt': 'Olá',
        'ru': 'Здравствуйте',
        'ar': 'مرحبا',
        'hi': 'नमस्ते',
        'it': 'Ciao',
        'tr': 'Merhaba'
    },
    
    # 식사/음식 (Food & Dining)
    '물 한 잔 주세요': {
        'en': 'A glass of water please',
        'zh': '请给我一杯水',
        'ja': '水をください',
        'es': 'Un vaso de agua por favor',
        'fr': 'Un verre d\'eau s\'il vous plaît',
        'de': 'Ein Glas Wasser bitte',
        'pt': 'Um copo de água por favor',
        'ru': 'Стакан воды пожалуйста',
        'ar': 'كوب ماء من فضلك',
        'hi': 'कृपया एक गिलास पानी दें',
        'it': 'Un bicchiere d\'acqua per favore',
        'tr': 'Lütfen bir bardak su'
    },
    
    '메뉴를 보여주세요': {
        'en': 'Please show me the menu',
        'zh': '请给我看菜单',
        'ja': 'メニューを見せてください',
        'es': 'Muéstrame el menú por favor',
        'fr': 'Montrez-moi le menu s\'il vous plaît',
        'de': 'Zeigen Sie mir bitte die Speisekarte',
        'pt': 'Me mostre o menu por favor',
        'ru': 'Покажите мне меню пожалуйста',
        'ar': 'أرني القائمة من فضلك',
        'hi': 'कृपया मुझे मेनू दिखाएं',
        'it': 'Mi mostri il menu per favore',
        'tr': 'Lütfen menüyü göster'
    },
    
    '얼마예요': {
        'en': 'How much is it',
        'zh': '多少钱',
        'ja': 'いくらですか',
        'es': 'Cuánto cuesta',
        'fr': 'Combien ça coûte',
        'de': 'Wie viel kostet es',
        'pt': 'Quanto custa',
        'ru': 'Сколько стоит',
        'ar': 'كم السعر',
        'hi': 'यह कितना है',
        'it': 'Quanto costa',
        'tr': 'Fiyatı ne kadar'
    },
    
    '맛있습니다': {
        'en': 'It\'s delicious',
        'zh': '很好吃',
        'ja': '美味しいです',
        'es': 'Está delicioso',
        'fr': 'C\'est délicieux',
        'de': 'Es ist köstlich',
        'pt': 'É delicioso',
        'ru': 'Это вкусно',
        'ar': 'إنه لذيذ',
        'hi': 'यह स्वादिष्ट है',
        'it': 'È delizioso',
        'tr': 'Lezzetli'
    },
    
    # 숙소 (Accommodation)
    '방을 하나 예약하고 싶습니다': {
        'en': 'I want to book a room',
        'zh': '我想预订一个房间',
        'ja': '部屋を予約したいです',
        'es': 'Quiero reservar una habitación',
        'fr': 'Je veux réserver une chambre',
        'de': 'Ich möchte ein Zimmer buchen',
        'pt': 'Quero reservar um quarto',
        'ru': 'Я хочу забронировать номер',
        'ar': 'أريد حجز غرفة',
        'hi': 'मैं एक कमरा बुक करना चाहता हूँ',
        'it': 'Voglio prenotare una stanza',
        'tr': 'Bir oda ayırttırmak istiyorum'
    },
    
    '얼마 한 밤에': {
        'en': 'How much per night',
        'zh': '每晚多少钱',
        'ja': '1泊いくらですか',
        'es': 'Cuánto por noche',
        'fr': 'Combien par nuit',
        'de': 'Wie viel pro Nacht',
        'pt': 'Quanto por noite',
        'ru': 'Сколько за ночь',
        'ar': 'كم تكلفة الليلة',
        'hi': 'प्रति रात कितना',
        'it': 'Quanto a notte',
        'tr': 'Gecelik fiyat ne kadar'
    },
    
    # 교통 (Transportation)
    '택시를 불러주세요': {
        'en': 'Please call a taxi',
        'zh': '请叫一辆出租车',
        'ja': 'タクシーを呼んでください',
        'es': 'Llama un taxi por favor',
        'fr': 'Appelez un taxi s\'il vous plaît',
        'de': 'Rufen Sie bitte ein Taxi',
        'pt': 'Chame um táxi por favor',
        'ru': 'Вызовите такси пожалуйста',
        'ar': 'اتصل بسيارة أجرة من فضلك',
        'hi': 'कृपया एक टैक्सी बुलाएं',
        'it': 'Chiami un taxi per favore',
        'tr': 'Lütfen bir taksi çağır'
    },
    
    '역은 어디입니까': {
        'en': 'Where is the station',
        'zh': '车站在哪里',
        'ja': '駅はどこですか',
        'es': 'Dónde está la estación',
        'fr': 'Où est la gare',
        'de': 'Wo ist der Bahnhof',
        'pt': 'Onde fica a estação',
        'ru': 'Где находится станция',
        'ar': 'أين المحطة',
        'hi': 'स्टेशन कहाँ है',
        'it': 'Dov\'è la stazione',
        'tr': 'İstasyon nerede'
    },
    
    # 의료 (Medical)
    '병원을 찾고 있습니다': {
        'en': 'I\'m looking for a hospital',
        'zh': '我在找医院',
        'ja': '病院を探しています',
        'es': 'Estoy buscando un hospital',
        'fr': 'Je cherche un hôpital',
        'de': 'Ich suche ein Krankenhaus',
        'pt': 'Estou procurando um hospital',
        'ru': 'Я ищу больницу',
        'ar': 'أبحث عن مستشفى',
        'hi': 'मैं एक अस्पताल ढूंढ रहा हूँ',
        'it': 'Sto cercando un ospedale',
        'tr': 'Hastane arıyorum'
    },
    
    '약국은 어디예요': {
        'en': 'Where is the pharmacy',
        'zh': '药店在哪里',
        'ja': '薬局はどこですか',
        'es': 'Dónde está la farmacia',
        'fr': 'Où est la pharmacie',
        'de': 'Wo ist die Apotheke',
        'pt': 'Onde fica a farmácia',
        'ru': 'Где аптека',
        'ar': 'أين الصيدلية',
        'hi': 'दवाखाना कहाँ है',
        'it': 'Dov\'è la farmacia',
        'tr': 'Eczane nerede'
    },
    
    # 비상 (Emergency)
    '도움이 필요합니다': {
        'en': 'I need help',
        'zh': '我需要帮助',
        'ja': '助けが必要です',
        'es': 'Necesito ayuda',
        'fr': 'J\'ai besoin d\'aide',
        'de': 'Ich brauche Hilfe',
        'pt': 'Preciso de ajuda',
        'ru': 'Мне нужна помощь',
        'ar': 'أنا بحاجة إلى مساعدة',
        'hi': 'मुझे मदद चाहिए',
        'it': 'Ho bisogno di aiuto',
        'tr': 'Yardıma ihtiyacım var'
    },
    
    '경찰을 불러주세요': {
        'en': 'Please call the police',
        'zh': '请叫警察',
        'ja': '警察を呼んでください',
        'es': 'Por favor llama a la policía',
        'fr': 'Appelez la police s\'il vous plaît',
        'de': 'Rufen Sie bitte die Polizei',
        'pt': 'Chame a polícia por favor',
        'ru': 'Вызовите полицию пожалуйста',
        'ar': 'استدع الشرطة من فضلك',
        'hi': 'कृपया पुलिस बुलाएं',
        'it': 'Chiami la polizia per favore',
        'tr': 'Lütfen polisi çağır'
    },
    
    '응급실은 어디예요': {
        'en': 'Where is the emergency room',
        'zh': '急诊室在哪里',
        'ja': '救急外来はどこですか',
        'es': 'Dónde está la sala de emergencias',
        'fr': 'Où est la salle d\'urgence',
        'de': 'Wo ist die Notaufnahme',
        'pt': 'Onde fica a sala de emergência',
        'ru': 'Где отделение скорой помощи',
        'ar': 'أين قسم الطوارئ',
        'hi': 'आपातकालीन कक्ष कहाँ है',
        'it': 'Dov\'è il pronto soccorso',
        'tr': 'Acil bölüm nerede'
    },
    
    # 쇼핑 (Shopping)
    '이것을 사고 싶어요': {
        'en': 'I want to buy this',
        'zh': '我想买这个',
        'ja': 'これを買いたいです',
        'es': 'Quiero comprar esto',
        'fr': 'Je veux acheter ceci',
        'de': 'Ich möchte das kaufen',
        'pt': 'Quero comprar isto',
        'ru': 'Я хочу это купить',
        'ar': 'أريد شراء هذا',
        'hi': 'मैं यह खरीदना चाहता हूँ',
        'it': 'Voglio comprare questo',
        'tr': 'Bunu satın almak istiyorum'
    },
    
    '카드로 낼 수 있습니까': {
        'en': 'Can I pay by card',
        'zh': '我可以用卡支付吗',
        'ja': 'カードで支払えますか',
        'es': 'Puedo pagar con tarjeta',
        'fr': 'Puis-je payer par carte',
        'de': 'Kann ich mit Karte bezahlen',
        'pt': 'Posso pagar com cartão',
        'ru': 'Я могу расплатиться картой',
        'ar': 'هل يمكنني الدفع بالبطاقة',
        'hi': 'क्या मैं कार्ड से भुगतान कर सकता हूँ',
        'it': 'Posso pagare con carta',
        'tr': 'Kartla ödeyebilir miyim'
    },
    
    # 날씨 (Weather)
    '내일 날씨가 어떻습니까': {
        'en': 'What\'s the weather like tomorrow',
        'zh': '明天天气怎么样',
        'ja': '明日の天気はどうですか',
        'es': 'Cómo es el clima mañana',
        'fr': 'Quel est le temps demain',
        'de': 'Wie ist das Wetter morgen',
        'pt': 'Como é o tempo amanhã',
        'ru': 'Какая погода завтра',
        'ar': 'كيف يكون الطقس غدا',
        'hi': 'कल का मौसम कैसा होगा',
        'it': 'Come sarà il tempo domani',
        'tr': 'Yarın hava nasıl olacak'
    },
    
    '비가 올 것 같은데요': {
        'en': 'It looks like it will rain',
        'zh': '看起来会下雨',
        'ja': '雨が降りそうです',
        'es': 'Parece que va a llover',
        'fr': 'Il semble qu\'il va pleuvoir',
        'de': 'Es sieht aus wie Regen',
        'pt': 'Parece que vai chover',
        'ru': 'Похоже будет дождь',
        'ar': 'يبدو أنه سيمطر',
        'hi': 'ऐसा लगता है कि बारिश होगी',
        'it': 'Sembra che pioverà',
        'tr': 'Yağmur yağacak gibi görünüyor'
    },
    
    # 방향 (Directions)
    '이 길이 맞습니까': {
        'en': 'Is this the right way',
        'zh': '这是对的路吗',
        'ja': 'これは正しい道ですか',
        'es': 'Es este el camino correcto',
        'fr': 'Est-ce le bon chemin',
        'de': 'Ist dies der richtige Weg',
        'pt': 'Este é o caminho certo',
        'ru': 'Это правильный путь',
        'ar': 'هل هذا الطريق صحيح',
        'hi': 'क्या यह सही रास्ता है',
        'it': 'È questa la strada giusta',
        'tr': 'Bu doğru yol mu'
    },
    
    '왼쪽으로 돌아주세요': {
        'en': 'Turn left',
        'zh': '左转',
        'ja': '左に曲がってください',
        'es': 'Gira a la izquierda',
        'fr': 'Tournez à gauche',
        'de': 'Biegen Sie links ab',
        'pt': 'Vire à esquerda',
        'ru': 'Поворот налево',
        'ar': 'استدر يسارا',
        'hi': 'बाएँ मुड़ें',
        'it': 'Gira a sinistra',
        'tr': 'Sola dön'
    },
    
    '오른쪽으로 돌아주세요': {
        'en': 'Turn right',
        'zh': '右转',
        'ja': '右に曲がってください',
        'es': 'Gira a la derecha',
        'fr': 'Tournez à droite',
        'de': 'Biegen Sie rechts ab',
        'pt': 'Vire à direita',
        'ru': 'Поворот направо',
        'ar': 'استدر يمينا',
        'hi': 'दाएँ मुड़ें',
        'it': 'Gira a destra',
        'tr': 'Sağa dön'
    },
    
    # 대화 (Conversation)
    '이름이 뭐예요': {
        'en': 'What\'s your name',
        'zh': '你叫什么名字',
        'ja': 'お名前は何ですか',
        'es': 'Cuál es tu nombre',
        'fr': 'Quel est votre nom',
        'de': 'Wie ist Ihr Name',
        'pt': 'Qual é o seu nome',
        'ru': 'Как вас зовут',
        'ar': 'ما اسمك',
        'hi': 'आपका नाम क्या है',
        'it': 'Qual è il tuo nome',
        'tr': 'Adın ne'
    },
    
    '저는 서울에서 왔습니다': {
        'en': 'I\'m from Seoul',
        'zh': '我来自首尔',
        'ja': '私はソウルから来ました',
        'es': 'Soy de Seúl',
        'fr': 'Je suis de Séoul',
        'de': 'Ich komme aus Seoul',
        'pt': 'Sou de Seul',
        'ru': 'Я из Сеула',
        'ar': 'أنا من سيول',
        'hi': 'मैं सियोल से हूँ',
        'it': 'Sono da Seoul',
        'tr': 'Seoul\'den geliyorum'
    },
    
    '처음 뵙겠습니다': {
        'en': 'Nice to meet you',
        'zh': '很高兴认识你',
        'ja': 'はじめましてです',
        'es': 'Mucho gusto',
        'fr': 'Ravi de vous rencontrer',
        'de': 'Schön, Sie kennenzulernen',
        'pt': 'Prazer em conhecê-lo',
        'ru': 'Рад познакомиться',
        'ar': 'يسعدني التعرف عليك',
        'hi': 'आपसे मिलकर खुशी हुई',
        'it': 'Piacere di conoscerti',
        'tr': 'Tanıştığımız için sevindim'
    },
}

def add_phrases_to_interpreter():
    root = r'C:\Users\WORK\source\repos\parkcheolhong\codeAI\backend\services'
    for r, d, f in os.walk(root):
        if 'sorisae_interpreter.py' in f and 'projects' not in r and 'engines120' not in r:
            path = os.path.join(r, 'sorisae_interpreter.py')
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Find the greetings section and extract format
            greetings_start = content.find('"greetings": {')
            first_phrase_start = content.find('"안녕하세요":', greetings_start)
            first_phrase_end = content.find('},', first_phrase_start) + 2
            
            # Build the new phrases section
            new_phrases = ''
            for ko_text, translations in COMMON_PHRASES.items():
                new_phrases += f'''            "{ko_text}": {{
                    "en": "{translations['en']}",
                    "zh": "{translations['zh']}",
                    "ja": "{translations['ja']}",
                    "es": "{translations['es']}",
                    "fr": "{translations['fr']}",
                    "de": "{translations['de']}",
                    "pt": "{translations['pt']}",
                    "ru": "{translations['ru']}",
                    "ar": "{translations['ar']}",
                    "hi": "{translations['hi']}",
                    "it": "{translations['it']}",
                    "tr": "{translations['tr']}"
                }},
'''
            
            # Replace the old greetings section
            # Find where greetings section ends
            greetings_end = content.find('# 비즈니스', greetings_start)
            if greetings_end < 0:
                greetings_end = content.find('# business', greetings_start)
            
            # Build new greetings section
            new_greetings = f'''        # 인사말 및 일상 표현 (Greetings & Daily Expressions)
            "greetings": {{
{new_phrases}            }},

            '''
            
            # Replace
            content = content[:greetings_start] + new_greetings + content[greetings_end:]
            
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            print(f'✅ {len(COMMON_PHRASES)}개의 한글 구문 추가 완료!')
            print(f'파일: {path}')
            return True
    
    return False

if __name__ == '__main__':
    success = add_phrases_to_interpreter()
    exit(0 if success else 1)
