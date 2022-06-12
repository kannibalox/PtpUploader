# Three letter codes: ISO 639-2/B
# Two letter codes: ISO 639-1
# http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
from typing import Optional


subtitle_ids = {
    3: ["english", "eng", "en", "english (cc)", "english - sdh"],
    4: ["spanish", "spa", "es"],
    5: ["french", "fre", "fr"],
    6: ["german", "ger", "de"],
    7: ["russian", "rus", "ru"],
    8: ["japanese", "jpn", "ja"],
    9: ["dutch", "dut", "nl"],
    10: ["danish", "dan", "da"],
    11: ["swedish", "swe", "sv"],
    12: ["norwegian", "nor", "no"],
    13: ["romanian", "rum", "ro"],
    14: ["chinese", "chi", "zh", "chinese (simplified)", "chinese (traditional)"],
    15: ["finnish", "fin", "fi"],
    16: ["italian", "ita", "it"],
    17: ["polish", "pol", "pl"],
    18: ["turkish", "tur", "tr"],
    19: ["korean", "kor", "ko"],
    20: ["thai", "tha", "th"],
    21: ["portuguese", "por", "pt"],
    22: ["arabic", "ara", "ar"],
    23: ["croatian", "hrv", "hr", "scr"],
    24: ["hungarian", "hun", "hu"],
    25: ["vietnamese", "vie", "vi"],
    26: ["greek", "gre", "el"],
    28: ["icelandic", "ice", "is"],
    29: ["bulgarian", "bul", "bg"],
    30: ["czech", "cze", "cz", "cs"],
    31: ["serbian", "srp", "sr", "scc"],
    34: ["ukrainian", "ukr", "uk"],
    37: ["latvian", "lav", "lv"],
    38: ["estonian", "est", "et"],
    39: ["lithuanian", "lit", "lt"],
    40: ["hebrew", "heb", "he"],
    41: ["hindihin", "hi"],
    42: ["slovak", "slo", "sk"],
    43: ["slovenian", "slv", "sl"],
    44: ["no subtitles"],
    47: ["indonesian", "ind", "id"],
    49: ["brazilian portuguese", "brazilian", "portuguese-br"],
    50: ["english - forced", "english (forced)"],
    51: ["english intertitles", "english (intertitles)", "english - intertitles"],
    52: ["persian", "fa", "far"],
}


def get_id(lang: str) -> Optional[int]:
    lang = lang.lower()
    for sub_id, names in subtitle_ids.items():
        if lang in names:
            return sub_id
    return None
