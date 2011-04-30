from PtpUploaderException import PtpUploaderException

import simplejson as json

import hashlib
import hmac
import time
import urllib
import urllib2
import uuid

# Uses the undocumented iPhone IMDb API.
# See:
# - imdbmobile: http://code.google.com/p/imdbmobile/
# - IMDb-Python-API: https://github.com/dbr/IMDb-Python-API

class ImdbInfo:
	def __init__(self):
		self.Title = ""
		self.Year = ""
		self.PosterUrl = ""
		self.Plot = ""
		self.IsSeries = False

class Imdb:
	@staticmethod
	def __GetInfoInternal(imdbId):
		# timestamp is needed
		# device is needed but can be anything
		# appid is needed but can be anything
		# sig must be "and2" and it must be the last parameter
		timeStamp = int( time.time() )
		device = uuid.uuid1()
		url = "http://app.imdb.com/title/maindetails?tconst=tt%s&timestamp=%s&device=%s&locale=en_US&appid=android2&sig=and2" % ( imdbId, timeStamp, device )

		# Sign the URL.
		# "eRnAYqbvj2JWXyPcu62yCA" comes from the disassembled "IMDb Movies & TV" Android application by IMDb. 
		url += "-%s" % hmac.HMAC( "eRnAYqbvj2JWXyPcu62yCA", url, hashlib.sha1 ).hexdigest()
		
		request = urllib2.Request( url )
		result = urllib2.urlopen( request )
		response = result.read()

		imdbInfo = ImdbInfo()
		
		jsonLoad = json.loads( response )
		data = jsonLoad[ "data" ]
		imdbInfo.Title = data[ "title" ]
		imdbInfo.Year = data[ "year" ]

		image = data.get( "image" )
		if image:
			imdbInfo.PosterUrl = image[ "url" ]

			# Some posters are huge on IMDb but can be easily scaled to arbitrary size by changing the URL.			
			height = image.get( "height" )
			if ( height is not None ) and height > 768:
				imdbInfo.PosterUrl = imdbInfo.PosterUrl.replace( "._V1_.jpg", "._V1_SY768_.jpg" )
			
		plot = data.get( "plot" )
		if plot:
			imdbInfo.Plot = plot[ "outline" ]

		seasons = data.get( "seasons" )
		if seasons:
			imdbInfo.IsSeries = True

		series = data.get( "series" )
		if series:
			imdbInfo.IsSeries = True

		return imdbInfo
		
	@staticmethod
	def GetInfo(logger, imdbId):
		logger.info( "Getting IMDb info for IMDb id '%s'." % imdbId );
		
		# We don't care if this fails. It gives only extra information.
		try:
			imdbInfo = Imdb.__GetInfoInternal( imdbId )
			return imdbInfo
		except Exception:
			logger.exception( "Got exception while trying to get IMDb info by IMDb id '%s'." % imdbId );

		return ImdbInfo()