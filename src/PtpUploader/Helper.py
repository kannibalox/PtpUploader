from Tool.PyrocoreBencode import bencode

from MyGlobals import MyGlobals
from PtpUploaderException import *

from datetime import datetime
import os
import re
import time
import urllib2

# Supported formats: "100 GB", "100 MB", "100 bytes". (Space is optional.)
# Returns with an integer. 
# Returns with 0 if size can't be found. 
def GetSizeFromText(text):
	text = text.replace( " ", "" )
	text = text.replace( ",", "" ) # For sizes like this: 1,471,981,530bytes
	text = text.replace( "GiB", "GB" )
	text = text.replace( "MiB", "MB" )
	
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

# timeDifference must be datetime.timedelta.
def TimeDifferenceToText( timeDifference, levels = 2, agoText = " ago", noDifferenceText = "Just now" ):
	timeDifference = ( timeDifference.microseconds / 1000000 ) + timeDifference.seconds + ( timeDifference.days * 24 * 3600 )

	years = timeDifference / 31556926 # 31556926 seconds = 1 year
	timeDifference %= 31556926

	months = timeDifference / 2629744 # 2629744 seconds = ~1 month (The mean month length of the Gregorian calendar is 30.436875 days.)
	timeDifference %= 2629744;

	days = timeDifference / 86400 # 86400 seconds = 1 day
	timeDifference %= 86400

	hours = timeDifference / 3600
	timeDifference %= 3600

	minutes = timeDifference / 60
	timeDifference %= 60

	seconds = timeDifference

	text = ""
	if years > 0:
		text += str( years ) + "y"
		levels -= 1

	if months > 0 and levels > 0:
		text += str( months ) + "mo";
		levels -= 1

	if days > 0 and levels > 0:
		text += str( days ) + "d"
		levels -= 1

	if hours > 0 and levels > 0:
		text += str( hours ) + "h"
		levels -= 1

	if minutes > 0 and levels > 0:
		text += str( minutes ) + "m"
		levels -= 1

	if seconds > 0 and levels > 0:
		text += str( seconds ) + "s"

	if len( text ) > 0:
		return text + agoText
	else:
		return noDifferenceText

# Nice...
try:
	from urlparse import parse_qs
except ImportError:
	from cgi import parse_qs
	
def ParseQueryString(query):
	return parse_qs( query )

def MakeRetryingHttpRequest( url, maximumTries = 3, delayBetweenRetriesInSec = 10 ):
	while True:
		try:
			opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
			request = urllib2.Request( url )
			result = opener.open( request )
			response = result.read()
			return response
		except urllib2.HTTPError, e:
			if maximumTries > 1:
				maximumTries -= 1
				time.sleep( delayBetweenRetriesInSec )
			else:
				raise

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

def GetSuggestedReleaseNameAndSizeFromTorrentFile( torrentPath ):
	data = bencode.bread( torrentPath )
	name = data[ "info" ].get( "name", None )
	files = data[ "info" ].get( "files", None )
	if files is None:
		# It is a single file torrent, remove the extension.
		name, extension = os.path.splitext( name )
		size = data[ "info" ][ "length" ]
		return name, size
	else:
		size = 0
		for file in files:
			size += file[ "length" ]

		return name, size
