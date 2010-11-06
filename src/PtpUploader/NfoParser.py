from PtpUploaderException import PtpUploaderException;

import fnmatch; 
import os;
import re;

class NfoParser:
	# Read the NFO file from the specified directory.
	@staticmethod
	def GetNfoFile(directoryPath):
		entries = os.listdir( directoryPath );
		for entry in entries:
			entryPath = os.path.join( directoryPath, entry );
			if os.path.isfile( entryPath ) and fnmatch.fnmatch( entry.lower(), "*.nfo" ):
				return NfoParser.ReadNfoFileToUnicode( entryPath );
		
		raise PtpUploaderException( "Can't find NFO in directory '%s'." % directoryPath );
	
	# Return with the IMDb id.
	# Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
	@staticmethod
	def GetImdbId(nfoText):
		matches = re.search( "imdb.com/title/tt(\d+)", nfoText )
		if matches:
			return matches.group( 1 );
		else:
			return None;
	
	@staticmethod
	def __StripNonAscii(string):
		stripped = ( c for c in string if 0 < ord( c ) < 127 )
		return "".join( stripped )

	@staticmethod
	def __IsLineContainsAnyUsefulCharacter(line):
		for c in line:
			if ( c >= '0' and c <= '9' ) or ( c >= 'a' and c <= 'z' ) or ( c >= 'A' and c <= 'Z' ):
				return True;
		return False;

	# Reads an NFO file and convert it to Unicode.
	@staticmethod
	def ReadNfoFileToUnicode(path):
		# Read as binary.
		nfoFile = open( path, "rb" );
		nfo = nfoFile.read();
		nfoFile.close();

		# NFOs use codepage 437.
		# http://en.wikipedia.org/wiki/.nfo
		nfo = nfo.decode( "cp437", "ignore" );

		# Remove "graphics" from the NFO.
		lines = nfo.split( "\n" );
		nfo = u"";
		previousLineWasEmpty = True;
		for line in lines:
			line = NfoParser.__StripNonAscii( line );
			line = line.strip();
			# If a line doesn't contains any useful characters (digit or letter) then we throw the whole line away. 
			if len( line ) > 0 and NfoParser.__IsLineContainsAnyUsefulCharacter( line ):
				previousLineWasEmpty = False;
				nfo += line + "\n";
			elif not previousLineWasEmpty:
				previousLineWasEmpty = True;
				nfo += "\n";

		return nfo;