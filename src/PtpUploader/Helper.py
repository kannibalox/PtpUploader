from Tool.PyrocoreBencode import bencode

from PtpUploaderException import *

import os
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

# Path can be a file or a directory. (Obviously.)
def GetPathSize(path):
	if os.path.isfile( path ):
		return os.path.getsize( path )
	
	totalSize = 0
	for ( dirPath, dirNames, fileNames ) in os.walk( path ):
		for file in fileNames:
			filePath = os.path.join( dirPath, file )
			totalSize += os.path.getsize( filePath )

	return totalSize

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
			path = path.decode( "utf-8", "ignore" )
			fileList.append( path )

		return fileList
	
def RemoveDisallowedCharactersFromPath(text):
	newText = text

	# These characters can't be in filenames on Windows.
	forbiddenCharacters = r"""\/:*?"<>|"""
	for c in forbiddenCharacters:
		newText = newText.replace( c, "" )

	newText = newText.strip()

	if len( newText ) > 0:
		return newText
	else:
		raise PtpUploaderException( "New name for '%s' resulted in empty string." % text )

def ValidateTorrentFile(torrentPath):
	try:
		torrentData = bencode.bread( torrentPath )
	except Exception:
		raise PtpUploaderException( "File '%s' is not a valid torrent." % torrentPath )

# os.listdir()
# "On Windows NT/2k/XP and Unix, if path is a Unicode object, the result will be a list of Unicode objects. Undecodable filenames will still be returned as string objects."
#
# For example calling os.listdir for a Unicode path returned with this, which is legit UTF-8, yet it forgot to decode...
# [ 'Jo\xc3\xabl.S\xc3\xa9ria.Interview.x264-judas-cg.mkv' ]
def TryToCorrectUndecodableListDirFileName(path):
	if isinstance( path, unicode ):
		return path
	else:
		# This will throw an exception if something goes wrong.
		return path.decode( "utf-8" )
