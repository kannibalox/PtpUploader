from PtpUploaderException import *

class PtpSubtitleId:
	NoSubtitle = 44
	Arabic     = 22
	Bulgarian  = 29
	Chinese    = 14
	Croatian   = 23
	Czech      = 30
	Danish     = 10
	Dutch      = 9
	English    = 3
	Estonian   = 38
	Finnish    = 15
	French     = 5
	German     = 6
	Greek      = 26
	Hebrew     = 40
	Hindi      = 41
	Hungarian  = 24
	Icelandic  = 28
	Indonesian = 47
	Italian    = 16
	Japanese   = 8
	Korean     = 19
	Latvian    = 37
	Lithuanian = 39
	Norwegian  = 12
	Polish     = 17
	Portuguese = 21
	Romanian   = 13
	Russian    = 7
	Serbian    = 31
	Slovak     = 42
	Slovenian  = 43
	Spanish    = 4
	Swedish    = 11
	Thai       = 20
	Turkish    = 18
	Ukrainian  = 34
	Vietnamese = 25

class PtpSubtitle:
	def __init__(self):
		self.List = {}

		# Three letter codes: ISO 639-2/B
		# Two letter codes: ISO 639-1
		# http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
		self.__Add( PtpSubtitleId.Arabic,     "Arabic",     "ara", "ar" )
		self.__Add( PtpSubtitleId.Bulgarian,  "Bulgarian",  "bul", "bg" )
		self.__Add( PtpSubtitleId.Chinese,    "Chinese",    "chi", "zh" )
		self.__Add( PtpSubtitleId.Croatian,   "Croatian",   "hrv", "hr", "scr" )
		self.__Add( PtpSubtitleId.Czech,      "Czech",      "cze", "cz" )
		self.__Add( PtpSubtitleId.Danish,     "Danish",     "dan", "da" )
		self.__Add( PtpSubtitleId.Dutch,      "Dutch",      "dut", "nl" )
		self.__Add( PtpSubtitleId.English,    "English",    "eng", "en" )
		self.__Add( PtpSubtitleId.Estonian,   "Estonian",   "est", "et" )
		self.__Add( PtpSubtitleId.Finnish,    "Finnish",    "fin", "fi" )
		self.__Add( PtpSubtitleId.French,     "French",     "fre", "fr" )
		self.__Add( PtpSubtitleId.German,     "German",     "ger", "de" )
		self.__Add( PtpSubtitleId.Greek,      "Greek",      "gre", "el" )
		self.__Add( PtpSubtitleId.Hebrew,     "Hebrew",     "heb", "he" )
		self.__Add( PtpSubtitleId.Hindi,      "Hindi"       "hin", "hi" )
		self.__Add( PtpSubtitleId.Hungarian,  "Hungarian",  "hun", "hu" )
		self.__Add( PtpSubtitleId.Icelandic,  "Icelandic",  "ice", "is" )
		self.__Add( PtpSubtitleId.Indonesian, "Indonesian", "ind", "id" )
		self.__Add( PtpSubtitleId.Italian,    "Italian" ,   "ita", "it" )
		self.__Add( PtpSubtitleId.Japanese,   "Japanese",   "jpn", "ja" )
		self.__Add( PtpSubtitleId.Korean,     "Korean",     "kor", "ko" )
		self.__Add( PtpSubtitleId.Latvian,    "Latvian",    "lav", "lv" )
		self.__Add( PtpSubtitleId.Lithuanian, "Lithuanian", "lit", "lt" )
		self.__Add( PtpSubtitleId.Norwegian,  "Norwegian",  "nor", "no" )
		self.__Add( PtpSubtitleId.Polish,     "Polish",     "pol", "pl" )
		self.__Add( PtpSubtitleId.Portuguese, "Portuguese", "por", "pt" )
		self.__Add( PtpSubtitleId.Romanian,   "Romanian",   "rum", "ro" )
		self.__Add( PtpSubtitleId.Russian,    "Russian",    "rus", "ru" )
		self.__Add( PtpSubtitleId.Serbian,    "Serbian",    "srp", "sr", "scc" )
		self.__Add( PtpSubtitleId.Slovak,     "Slovak",     "slo", "sk" )
		self.__Add( PtpSubtitleId.Slovenian,  "Slovenian",  "slv", "sl" )
		self.__Add( PtpSubtitleId.Spanish,    "Spanish",    "spa", "es" )
		self.__Add( PtpSubtitleId.Swedish,    "Swedish",    "swe", "sv" )
		self.__Add( PtpSubtitleId.Thai,       "Thai",       "tha", "th" )
		self.__Add( PtpSubtitleId.Turkish,    "Turkish",    "tur", "tr" )
		self.__Add( PtpSubtitleId.Ukrainian,  "Ukrainian",  "ukr", "uk" )
		self.__Add( PtpSubtitleId.Vietnamese, "Vietnamese", "vie", "vi" )

	def __AddOne(self, ptpSubtitleId, languageName):
		languageName = languageName.lower()
		if self.List.get( languageName ) is None:
			self.List[ languageName ] = ptpSubtitleId
		else:
			raise PtpUploaderException( "Text '%s' is not unique!" % languageName )

	def __Add(self, ptpSubtitleId, *args):
		for arg in args:
			self.__AddOne( ptpSubtitleId, arg )

	def GetId(self, languageName):
		languageName = languageName.lower()
		return self.List.get( languageName )