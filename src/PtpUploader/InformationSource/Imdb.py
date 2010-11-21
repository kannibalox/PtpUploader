from Globals import Globals
from PtpUploaderException import PtpUploaderException

import simplejson as json

import urllib
import urllib2

# Uses the undocumented iPhone IMDb API.
# See:
# - imdbmobile: http://code.google.com/p/imdbmobile/
# - IMDb-Python-API: https://github.com/dbr/IMDb-Python-API

class ImdbInfo:
	def __init__(self):
		self.Title = ""
		self.Directors = [] # This can be empty. For example: "Band of Brothers" -- http://www.imdb.com/title/tt0185906/
		self.PosterUrl = ""
		self.Plot = ""
		self.IsSeries = False

class Imdb:
	@staticmethod
	def __GetInfoInternal(imdbId):
		url = "http://app.imdb.com/title/maindetails?api=v1&appid=iphone1&locale=en_US&tconst=tt%s" % imdbId 
		request = urllib2.Request( url )
		result = urllib2.urlopen( request )
		response = result.read()

		imdbInfo = ImdbInfo()
		
		jsonLoad = json.loads( response )
		data = jsonLoad[ "data" ]
		imdbInfo.Title = data[ "title" ]

		image = data.get( "image" )
		if image:
			imdbInfo.PosterUrl = image[ "url" ]
			
		plot = data.get( "plot" )
		if plot:
			imdbInfo.Plot = plot[ "outline" ]

		seasons = data.get( "seasons" )
		if seasons:
			imdbInfo.IsSeries = True
		
		directors = data.get( "directors_summary" )
		if directors:
			for director in directors:
				directorNameInfo = director[ "name" ]
				directorName = directorNameInfo[ "name" ]
				imdbInfo.Directors.append( directorName )
				
		return imdbInfo
		
	@staticmethod
	def GetInfo(imdbId):
		Globals.Logger.info( "Getting IMDb info for IMDb id '%s'." % imdbId );
		
		# We don't care if this fails. It gives only extra information.
		try:
			imdbInfo = Imdb.__GetInfoInternal( imdbId )
			return imdbInfo
		except Exception:
			Globals.Logger.exception( "Got exception while trying to get IMDb info by IMDb id '%s'." % imdbId );
			
		return None