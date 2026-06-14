from .fa import STRINGS as FA
from .en import STRINGS as EN
from .zh import STRINGS as ZH

LANGUAGES = {
    "fa": {"strings": FA, "flag": "🇮🇷", "name": "فارسی"},
    "en": {"strings": EN, "flag": "🇬🇧", "name": "English"},
    "zh": {"strings": ZH, "flag": "🇨🇳", "name": "中文"},
}

DEFAULT_LANG = "fa"


def t(lang: str, key: str, **kwargs) -> str:
    """ترجمه یک کلید با پارامترهای اختیاری"""
    strings = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG])["strings"]
    text = strings.get(key, LANGUAGES[DEFAULT_LANG]["strings"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text
