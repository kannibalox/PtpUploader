from pyrocore.util import bencode

import re

# Supported formats: "100 GB", "100 MB", "100 bytes". (Space is optional.)
# Returns with an integer. 
# Returns with 0 if size can't be found. 
def GetSizeFromText(text):
	text = text.replace( " ", "" )
	text = text.replace( ",", "" ) # For sizes like this: 1,471,981,530bytes
	
	matches = re.match( "(.+)GB", text )
	if matches is not None:
		size = float( matches.group( 1 ) )
		return int( size * 1024 * 1024 * 1024 ) 

	matches = re.match( "(.+)MB", text )
	if matches is not None:
		size = float( matches.group( 1 ) )
		return int( size * 1024 * 1024 )

	matches = re.match( "(.+)bytes", text )
	if matches is not None:
		return int( matches.group( 1 ) )

	return 0

def SizeToText(size):
	if size < 1024 * 1024 * 1024:
		return "%.2f MB" % ( float( size ) / ( 1024 * 1024 ) )
	else:
		return "%.2f GB" % ( float( size ) / ( 1024 * 1024 * 1024 ) )

# Nice...
try:
	from urlparse import parse_qs
except ImportError:
	from cgi import parse_qs
	
def ParseQueryString(query):
	return parse_qs( query )

# Always uses / as path separator.
def GetFileListFromTorrent(torrentPath):
	data = bencode.bread( torrentPath )
	name = data[ "info" ].get( "name", None )
	files = data[ "info" ].get( "files", None )

	if files is None:
		return [ name ]
	else:
		fileList = []
		for fileInfo in files:
			path = "/".join( fileInfo[ "path" ] )
			fileList.append( path )

		return fileList