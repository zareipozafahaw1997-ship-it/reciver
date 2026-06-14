"""دیکشنری کشورها و پرچم‌هاشون"""

# کدهای کشوری تلفن (Phone country codes)
PHONE_COUNTRY_CODES = {
    '98': 'IR',    # ایران
    '1': 'US',     # آمریکا/کانادا
    '44': 'GB',    # انگلستان
    '49': 'DE',    # آلمان
    '33': 'FR',    # فرانسه
    '39': 'IT',    # ایتالیا
    '34': 'ES',    # اسپانیا
    '31': 'NL',    # هلند
    '90': 'TR',    # ترکیه
    '971': 'AE',   # امارات
    '966': 'SA',   # عربستان
    '7': 'RU',     # روسیه
    '380': 'UA',   # اوکراین
    '48': 'PL',    # لهستان
    '91': 'IN',    # هند
    '92': 'PK',    # پاکستان
    '880': 'BD',   # بنگلادش
    '62': 'ID',    # اندونزی
    '60': 'MY',    # مالزی
    '66': 'TH',    # تایلند
    '84': 'VN',    # ویتنام
    '63': 'PH',    # فیلیپین
    '86': 'CN',    # چین
    '81': 'JP',    # ژاپن
    '82': 'KR',    # کره جنوبی
    '61': 'AU',    # استرالیا
    '55': 'BR',    # برزیل
    '54': 'AR',    # آرژانتین
    '52': 'MX',    # مکزیک
    '20': 'EG',    # مصر
    '27': 'ZA',    # آفریقای جنوبی
    '234': 'NG',   # نیجریه
    '254': 'KE',   # کنیا
    '964': 'IQ',   # عراق
    '963': 'SY',   # سوریه
    '961': 'LB',   # لبنان
    '962': 'JO',   # اردن
    '965': 'KW',   # کویت
    '974': 'QA',   # قطر
    '968': 'OM',   # عمان
    '973': 'BH',   # بحرین
    '93': 'AF',    # افغانستان
    '994': 'AZ',   # آذربایجان
    '374': 'AM',   # ارمنستان
    '995': 'GE',   # گرجستان
    '7': 'KZ',     # قزاقستان (همون کد روسیه)
    '998': 'UZ',   # ازبکستان
    '993': 'TM',   # ترکمنستان
    '992': 'TJ',   # تاجیکستان
    '996': 'KG',   # قرقیزستان
}

COUNTRIES = {
    'IR': {'name': 'ایران', 'flag': '🇮🇷'},
    'US': {'name': 'آمریکا', 'flag': '🇺🇸'},
    'GB': {'name': 'انگلستان', 'flag': '🇬🇧'},
    'DE': {'name': 'آلمان', 'flag': '🇩🇪'},
    'FR': {'name': 'فرانسه', 'flag': '🇫🇷'},
    'IT': {'name': 'ایتالیا', 'flag': '🇮🇹'},
    'ES': {'name': 'اسپانیا', 'flag': '🇪🇸'},
    'NL': {'name': 'هلند', 'flag': '🇳🇱'},
    'TR': {'name': 'ترکیه', 'flag': '🇹🇷'},
    'AE': {'name': 'امارات', 'flag': '🇦🇪'},
    'SA': {'name': 'عربستان', 'flag': '🇸🇦'},
    'RU': {'name': 'روسیه', 'flag': '🇷🇺'},
    'UA': {'name': 'اوکراین', 'flag': '🇺🇦'},
    'PL': {'name': 'لهستان', 'flag': '🇵🇱'},
    'IN': {'name': 'هند', 'flag': '🇮🇳'},
    'PK': {'name': 'پاکستان', 'flag': '🇵🇰'},
    'BD': {'name': 'بنگلادش', 'flag': '🇧🇩'},
    'ID': {'name': 'اندونزی', 'flag': '🇮🇩'},
    'MY': {'name': 'مالزی', 'flag': '🇲🇾'},
    'TH': {'name': 'تایلند', 'flag': '🇹🇭'},
    'VN': {'name': 'ویتنام', 'flag': '🇻🇳'},
    'PH': {'name': 'فیلیپین', 'flag': '🇵🇭'},
    'CN': {'name': 'چین', 'flag': '🇨🇳'},
    'JP': {'name': 'ژاپن', 'flag': '🇯🇵'},
    'KR': {'name': 'کره جنوبی', 'flag': '🇰🇷'},
    'AU': {'name': 'استرالیا', 'flag': '🇦🇺'},
    'CA': {'name': 'کانادا', 'flag': '🇨🇦'},
    'BR': {'name': 'برزیل', 'flag': '🇧🇷'},
    'AR': {'name': 'آرژانتین', 'flag': '🇦🇷'},
    'MX': {'name': 'مکزیک', 'flag': '🇲🇽'},
    'EG': {'name': 'مصر', 'flag': '🇪🇬'},
    'ZA': {'name': 'آفریقای جنوبی', 'flag': '🇿🇦'},
    'NG': {'name': 'نیجریه', 'flag': '🇳🇬'},
    'KE': {'name': 'کنیا', 'flag': '🇰🇪'},
    'IQ': {'name': 'عراق', 'flag': '🇮🇶'},
    'SY': {'name': 'سوریه', 'flag': '🇸🇾'},
    'LB': {'name': 'لبنان', 'flag': '🇱🇧'},
    'JO': {'name': 'اردن', 'flag': '🇯🇴'},
    'KW': {'name': 'کویت', 'flag': '🇰🇼'},
    'QA': {'name': 'قطر', 'flag': '🇶🇦'},
    'OM': {'name': 'عمان', 'flag': '🇴🇲'},
    'BH': {'name': 'بحرین', 'flag': '🇧🇭'},
    'AF': {'name': 'افغانستان', 'flag': '🇦🇫'},
    'AZ': {'name': 'آذربایجان', 'flag': '🇦🇿'},
    'AM': {'name': 'ارمنستان', 'flag': '🇦🇲'},
    'GE': {'name': 'گرجستان', 'flag': '🇬🇪'},
    'KZ': {'name': 'قزاقستان', 'flag': '🇰🇿'},
    'UZ': {'name': 'ازبکستان', 'flag': '🇺🇿'},
    'TM': {'name': 'ترکمنستان', 'flag': '🇹🇲'},
    'TJ': {'name': 'تاجیکستان', 'flag': '🇹🇯'},
    'KG': {'name': 'قرقیزستان', 'flag': '🇰🇬'},
}

def detect_country_from_phone(phone: str) -> str:
    """تشخیص کد کشور از روی شماره تلفن"""
    # حذف + و فاصله‌ها
    phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    
    # چک کردن کدهای مختلف (از طولانی‌ترین شروع می‌کنیم)
    for length in [4, 3, 2, 1]:
        code = phone[:length]
        if code in PHONE_COUNTRY_CODES:
            return PHONE_COUNTRY_CODES[code]
    
    return 'UNKNOWN'

def get_country_name(country_code: str) -> str:
    """دریافت نام کشور از کد"""
    if country_code in COUNTRIES:
        return f"{COUNTRIES[country_code]['flag']} {COUNTRIES[country_code]['name']}"
    return f"🌍 {country_code}"

def get_country_flag(country_code: str) -> str:
    """دریافت پرچم کشور"""
    if country_code in COUNTRIES:
        return COUNTRIES[country_code]['flag']
    return "🌍"
