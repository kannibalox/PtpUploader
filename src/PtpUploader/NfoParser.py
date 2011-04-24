from Helper import GetFileListFromTorrent
from PtpUploaderException import PtpUploaderException

import fnmatch 
import os
import re
import textwrap

class NfoParser:
	# Read the NFO file from the specified directory.
	@staticmethod
	def GetNfoFile(directoryPath):
		entries = os.listdir( directoryPath )
		for entry in entries:
			entryPath = os.path.join( directoryPath, entry )
			if os.path.isfile( entryPath ) and fnmatch.fnmatch( entry.lower(), "*.nfo" ):
				return NfoParser.ReadNfoFileToUnicode( entryPath )

		raise ""
	
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
	
	@staticmethod
	def __StripNonAscii(string):
		stripped = ( c for c in string if 0 < ord( c ) < 127 )
		return "".join( stripped )

	@staticmethod
	def __IsLineContainsAnyUsefulCharacter(line):
		for c in line:
			if ( c >= '0' and c <= '9' ) or ( c >= 'a' and c <= 'z' ) or ( c >= 'A' and c <= 'Z' ):
				return True
		return False
	
	@staticmethod
	def __IsUsefulLine(line):
		# If a line doesn't contain any useful characters (digit or letter) then we throw the whole line away. 
		if len( line ) <= 0 or ( not NfoParser.__IsLineContainsAnyUsefulCharacter( line ) ):
			return False

		# If the line doesn't contain spaces or a periods than it most likely doesn't contain any text, just drawing by text. (See an NFO of a Japhson release for example.)
		# (Period is checked because some NFOs are padded by them instead of spaces.)
		for c in line:
			if c == ' ' or c == '.':
				return True
			
		return False

	# Reads an NFO file and converts it to Unicode.
	@staticmethod
	def ReadNfoFileToUnicodeWithoutAltering(path):
		# Read as binary.
		nfoFile = open( path, "rb" )
		nfo = nfoFile.read()
		nfoFile.close()

		# NFOs use codepage 437.
		# http://en.wikipedia.org/wiki/.nfo
		nfo = nfo.decode( "cp437", "ignore" )
		return nfo

	@staticmethod
	def __ReadNfoProcessWrappedLines(wrappedLines):
		nfo = u""
		for wrappedLine in wrappedLines:
			line = NfoParser.__StripNonAscii( wrappedLine )
			line = line.strip()
			if NfoParser.__IsUsefulLine( line ):
				nfo += line + "\n"

		return nfo

	# Reads an NFO file and converts it to Unicode.
	# Removes the graphics from NFO.
	# Breaks too long lines (more than 100 character) to separate lines. 
	@staticmethod
	def ReadNfoFileToUnicode(path):
		nfo = NfoParser.ReadNfoFileToUnicodeWithoutAltering( path )
		
		lines = nfo.split( "\n" )
		nfo = u""
		textWrapper = textwrap.TextWrapper( width = 100 )
		previousLineWasEmpty = True
		
		for line in lines:
			wrappedLines = textWrapper.wrap( line )
			nfoLine = NfoParser.__ReadNfoProcessWrappedLines( wrappedLines )
			if len( nfoLine ) > 0:
				nfo += nfoLine
				previousLineWasEmpty = False
			elif not previousLineWasEmpty:
				nfo += "\n"
				previousLineWasEmpty = True

		return nfo

	# If there are multiple NFOs it returns with empty string.
	@staticmethod
	def FindAndReadNfoFileToUnicode(directoryPath):
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
		for file in files:
			file = file.lower();  
			if file.endswith( ".nfo" ):
				nfoCount += 1
				if nfoCount > 1:
					return True

		return False