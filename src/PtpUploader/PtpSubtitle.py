NoSubtitle = 44

Subtitles = {
        3: ["English", "eng", "en", "English (CC)", "English - SDH"],
        4: ["Spanish", "spa", "es"],
        5: ["French", "fre", "fr"],
        6: ["German", "ger", "de"],
        7: ["Russian", "rus", "ru"],
        8: ["Japanese", "jpn", "ja"],
        9: ["Dutch", "dut", "nl"],
        10: ["Danish", "dan", "da"],
        11: ["Swedish", "swe", "sv"],
        12: ["Norwegian", "nor", "no"],
        13: ["Romanian", "rum", "ro"],
        14: ["Chinese", "chi", "zh", "Chinese (Simplified)", "Chinese (Traditional)"],
        15: ["Finnish", "fin", "fi"],
        16: ["Italian" , "ita", "it"],
        17: ["Polish", "pol", "pl"],
        18: ["Turkish", "tur", "tr"],
        19: ["Korean", "kor", "ko"],
        20: ["Thai", "tha", "th"],
        21: ["Portuguese", "por", "pt"],
        22: ["Arabic", "ara", "ar"],
        23: ["Croatian", "hrv", "hr", "scr"],
        24: ["Hungarian", "hun", "hu"],
        25: ["Vietnamese", "vie", "vi"],
        26: ["Greek", "gre", "el"],
        28: ["Icelandic", "ice", "is"],
        29: ["Bulgarian", "bul", "bg"],
        30: ["Czech", "cze", "cz", "cs"],
        31: ["Serbian", "srp", "sr", "scc"],
        34: ["Ukrainian", "ukr", "uk"],
        37: ["Latvian", "lav", "lv"],
        38: ["Estonian", "est", "et"],
        39: ["Lithuanian", "lit", "lt"],
        40: ["Hebrew", "heb", "he"],
        41: ["Hindi" "hin", "hi"],
        42: ["Slovak", "slo", "sk"],
        43: ["Slovenian", "slv", "sl"],
        47: ["Indonesian", "ind", "id"],
        49: ["Brazilian Portuguese", "Brazilian", "Portuguese-BR"],
        50: ["English - Forced"],
        51: ["English Intertitles"],
        52: ["Persian", "fa", "fas", "per"]
}

def GetId(languageName):
    for subId, langs in Subtitles.items():
        if languageName in langs:
            return subId
    return None

def GetSubs():
    return sort([i[0] for i in Subtitles.values()])

if __name__ == '__main__':
    seen = set()
    uniq = set()
    for sub in Subtitles.values():
        for s in sub:
            if s not in seen:
                seen.add(s)
            else:
                uniq.add(s)
    if len(uniq) >= 1:
        print("Found duplicate subtitles IDs!")
        print(uniq)
