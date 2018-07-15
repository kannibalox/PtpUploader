from MyGlobals import MyGlobals
from PtpUploaderException import PtpUploaderException

import simplejson as json
from imdb import IMDb

import hashlib
import hmac
import time
import uuid

class ImdbInfo:
	def __init__(self):
		self.Title = ""
		self.Year = ""
		self.PosterUrl = ""
		self.Plot = ""
		self.IsSeries = False
		self.ImdbRating = ""
		self.ImdbVoteCount = ""

class Imdb:
	@staticmethod
	def __GetInfoInternal(imdbId):
		ia = IMDb()
		movie = ia.get_movie( imdbId )
		imdbInfo = ImdbInfo()

		imdbInfo.Title = movie[ "title" ].strip()
		imdbInfo.Year = movie[ "year" ]
		imdbInfo.ImdbRating = str( movie.get( "rating", "" ) )
		imdbInfo.ImdbVoteCount = str( movie.get( "num_votes", "" ) )
		if 'cover' in movie:
			imdbInfo.PosterUrl = re.sub( r"\._V1_.*\.jpg", "._V1_SY768_.jpg", movie[ "cover" ] )
		if 'episode of' in movie:
			imdbInfo.IsSeries = True
		if 'plot outline' in movie:
			imdbInfo.Plot = movie[ "plot outline" ]
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
