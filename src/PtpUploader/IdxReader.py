import re

class IdxReader:
	@staticmethod
	def GetSubtitleLanguages(path):
		languages = []

		# id: en, index: 0
		languageRe = re.compile( r"id: ([a-z][a-z]), index: \d+$", re.IGNORECASE )

		for line in open( path, "r" ):
			match = languageRe.match( line )
			if match is not None:
				languages.append( match.group( 1 ) )
	
		return languages