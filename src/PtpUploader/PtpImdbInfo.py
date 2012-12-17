from MyGlobals import MyGlobals
from Ptp import Ptp
from PtpUploaderException import *

import poster
import simplejson as json

import HTMLParser # For HTML entity reference decoding...
import re
import urllib2

class PtpImdbInfo:
	def __init__(self, imdbId):
		self.ImdbId = imdbId
		self.JsonResponse = ""
		self.JsonMovie = None
		self.HtmlParser = None
	
	def __LoadmdbInfo(self):
		# Already loaded
		if self.JsonMovie is not None:
			return
		
		# PTP doesn't decodes the HTML entity references (like "&#x26;" to "&") in the JSON response, so we have to.
		# We are using an internal function of HTMLParser. 
		# See this: http://fredericiana.com/2010/10/08/decoding-html-entities-to-text-in-python/
		self.HtmlParser = HTMLParser.HTMLParser()
 
		# Get IMDb info through PTP's ajax API used by the site when the user presses the auto fill button.
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( "http://passthepopcorn.me/ajax.php?action=torrent_info&imdb=%s" % Ptp.NormalizeImdbIdForPtp( self.ImdbId ) )
		result = opener.open( request )
		self.JsonResponse = result.read()
		Ptp.CheckIfLoggedInFromResponse( result, self.JsonResponse )

		# The response is JSON.
		# [{"title":"Devil's Playground","plot":"As the world succumbs to a zombie apocalypse, Cole a hardened mercenary, is chasing the one person who can provide a cure. Not only to the plague but to Cole's own incumbent destiny. DEVIL'S PLAYGROUND is a cutting edge British horror film that features zombies portrayed by free runners for a terrifyingly authentic representation of the undead","art":false,"year":"2010","director":[{"imdb":"1654324","name":"Mark McQueen","role":null}],"tags":"action, horror","writers":[{"imdb":"1057010","name":"Bart Ruspoli","role":" screenplay"}]}]

		jsonResult = json.loads( self.JsonResponse )
		if len( jsonResult ) != 1:
			raise PtpUploaderException( "Bad PTP movie info JSON response: array length is not one.\nFull response:\n%s" % self.JsonResponse )
	
		self.JsonMovie = jsonResult[ 0 ]

	def GetTitle(self):
		self.__LoadmdbInfo()
		title = self.JsonMovie[ "title" ]
		if ( title is None ) or len( title ) == 0:
			raise PtpUploaderException( "Bad PTP movie info JSON response: title is empty.\nFull response:\n%s" % self.JsonResponse )
		return self.HtmlParser.unescape( title ).strip() # PTP doesn't decodes properly the text.

	def GetYear(self):
		self.__LoadmdbInfo()
		year = self.JsonMovie[ "year" ]
		if ( year is None ) or len( year ) == 0:
			raise PtpUploaderException( "Bad PTP movie info JSON response: year is empty.\nFull response:\n%s" % self.JsonResponse )
		return year

	def GetMovieDescription(self):
		self.__LoadmdbInfo()
		movieDescription = self.JsonMovie[ "plot" ]
		if movieDescription is None:
			return ""
		else:
			return movieDescription

	def GetTags(self):
		self.__LoadmdbInfo()
		tags = self.JsonMovie[ "tags" ]
		if tags is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: tags key doesn't exists.\nFull response:\n%s" % self.JsonResponse )
		return tags

	def GetCoverArtUrl(self):
		self.__LoadmdbInfo()
		coverArtUrl = self.JsonMovie[ "art" ]
		if coverArtUrl is None:
			raise PtpUploaderException( "Bad PTP movie info JSON response: art key doesn't exists.\nFull response:\n%s" % self.JsonResponse )

		# It may be false... Eg.: "art": false
		if isinstance( coverArtUrl, basestring ):
			# Force height to 480 pixels.
			# Example links:
			# http://ia.media-imdb.com/images/M/MV5BMTM2MjE0NTcwNl5BMl5BanBnXkFtZTcwOTM0MDQ1NA@@._V1._SY317_CR1,0,214,317_.jpg
			# http://ia.media-imdb.com/images/M/MV5BMjEwNjQ5NDU4OF5BMl5BanBnXkFtZTYwOTI2NzA5._V1._SY317_CR1,0,214,317_.jpg
			match = re.match( r"""(.+?\._V1\.)(.*)\.jpg""", coverArtUrl )
			if match is None:
				return coverArtUrl
			else:
				return match.group( 1 ) + "_SY480.jpg"
		else:
			return ""

	def GetDirectors(self):
		# Director's name may not be present. For example: http://www.imdb.com/title/tt0864336/
		self.__LoadmdbInfo()
		jsonArtists = self.JsonMovie[ "artists" ]
		if ( jsonArtists is not None ) and len( jsonArtists ) > 0:
			jsonDirectors = jsonArtists[ 0 ]
			if len( jsonDirectors ) > 0:
				directorNames = []
				for jsonDirector in jsonDirectors:
					directorName = jsonDirector[ "name" ]
					if ( directorName is None ) or len( directorName ) == 0: 
						raise PtpUploaderException( "Bad PTP movie info JSON response: director name is empty.\nFull response:\n%s" % self.JsonResponse )
		
					directorName = self.HtmlParser.unescape( directorName ) # PTP doesn't decodes properly the text.
					directorNames.append( directorName )
		
				return directorNames

		return [ "None Listed" ]

class PtpZeroImdbInfo:
	def __init__(self):
		pass
	
	def GetTitle(self):
		return ""

	def GetYear(self):
		return ""

	def GetMovieDescription(self):
		return ""

	def GetTags(self):
		return ""

	def GetCoverArtUrl(self):
		return ""

	def GetDirectors(self):
		return []
		