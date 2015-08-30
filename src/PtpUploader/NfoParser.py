from Helper import GetFileListFromTorrent
from PtpUploaderException import PtpUploaderException

import fnmatch 
import os
import re

class NfoParser:
	# Return with the IMDb id.
	# Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
	@staticmethod
	def GetImdbId(nfoText):
		matches = re.search( "imdb.com/title/tt(\d+)", nfoText )
		if not matches:
			matches = re.search( "imdb.com/Title\?(\d+)", nfoText )
		
		if matches:
			return matches.group( 1 )
		else:
			return ""

	# Reads an NFO file and converts it to Unicode.
	@staticmethod
	def ReadNfoFileToUnicode(path):
		# Read as binary.
		nfoFile = open( path, "rb" )
		nfo = nfoFile.read()
		nfoFile.close()

		# NFOs use codepage 437.
		# http://en.wikipedia.org/wiki/.nfo
		nfo = nfo.decode( "cp437", "ignore" )
		return nfo

	# If there are multiple NFOs, it returns with empty string.
	@staticmethod
	def FindAndReadNfoFileToUnicode( directoryPath ):
		nfoPath = None
		nfoFound = False

		entries = os.listdir( directoryPath )
		for entry in entries:
			entryPath = os.path.join( directoryPath, entry );
			entryLower = entry.lower()
			if os.path.isfile( entryPath ) and fnmatch.fnmatch( entryLower, "*.nfo" ):
				if nfoFound:
					nfoPath = None
				else:
					nfoPath = entryPath
					nfoFound = True

		if nfoPath is None:
			return u""
		else:
			return NfoParser.ReadNfoFileToUnicode( nfoPath )

	@staticmethod
	def IsTorrentContainsMultipleNfos(torrentPath):
		files = GetFileListFromTorrent( torrentPath )
		nfoCount = 0
		for file in files:
			file = file.lower();

			# Only check in the root folder.
			if file.find( "/" ) != -1 or file.find( "\\" ) != -1:
				continue

			if file.endswith( ".nfo" ):
				nfoCount += 1
				if nfoCount > 1:
					return True

		return False