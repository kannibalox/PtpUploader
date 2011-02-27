from Globals import Globals
from PtpMovieSearchResult import PtpMovieSearchResult
from PtpUploaderException import *
from Settings import Settings

import poster
import simplejson as json

import HTMLParser # For HTML entity reference decoding...
import mimetypes
import os
import re
import time
import urllib
import urllib2

class Ptp:
	@staticmethod
	def __LoginInternal():
		Globals.Logger.info( "Loggin in to PTP." );
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		postData = urllib.urlencode( { "username": Settings.PtpUserName, "password": Settings.PtpPassword } )
		request = urllib2.Request( "http://passthepopcorn.me/login.php", postData );
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( response );

	@staticmethod
	def Login():
		maximumRetries = 2

		while True:
			try:
				Ptp.__LoginInternal()
				return
			except PtpUploaderInvalidLoginException:
				raise
			except Exception:
				if maximumRetries > 0:
					maximumRetries -= 1
					time.sleep( 30 ) # Wait 30 seconds and retry.
				else:
					raise
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( """<a href="login.php?act=recover">""" ) != -1:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Probably due to the bad user name or password." )
		
		if response.find( """<p>Your IP has been banned.</p>""" ) != -1:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your IP has been banned." )
		
		if response.find( 'action="login.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to PTP. Probably due to the bad user name or password." )
				
	# imdbId: IMDb id. Eg.: 0137363 for http://www.imdb.com/title/tt0137363/
	# returns with PtpMovieSearchResult
	@staticmethod
	def GetMoviePageOnPtp(logger, imdbId):
		logger.info( "Trying to find movie with IMDb id '%s' on PTP." % imdbId );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( "http://passthepopcorn.me/torrents.php?imdb=%s" % imdbId );
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( response );

		# If there is a movie: result.url = http://passthepopcorn.me/torrents.php?id=28577
		# If there is no movie: result.url = http://passthepopcorn.me/torrents.php?imdb=1535492
		match = re.match( r"https?://passthepopcorn\.me/torrents\.php\?id=(\d+)", result.url );
		if match is not None:
			ptpId = match.group( 1 );
			logger.info( "Movie with IMDb id '%s' exists on PTP at '%s'." % ( imdbId, result.url ) );
			return PtpMovieSearchResult( ptpId, response );
		elif response.find( "<h2>Error 404</h2>" ) != -1: # For some deleted movies PTP return with this error.
			logger.info( "Movie with IMDb id '%s' doesn't exists on PTP. (Got error 404.)" % imdbId );
			return PtpMovieSearchResult( ptpId = None, moviePageHtml = None );
		elif response.find( "<h2>Your search did not match anything.</h2>" ) == -1: # Multiple movies with the same IMDb id. 
			raise PtpUploaderException( "There are multiple movies on PTP with IMDb id '%s'." % imdbId )
		else:
			logger.info( "Movie with IMDb id '%s' doesn't exists on PTP." % imdbId );
			return PtpMovieSearchResult( ptpId = None, moviePageHtml = None );

	@staticmethod
	def FillImdbInfo(logger, releaseInfo):
		logger.info( "Downloading movie info from PTP for IMDb id '%s'." % releaseInfo.ImdbId );

		# PTP doesn't decodes the HTML entity references (like "&#x26;" to "&") in the JSON response, so we have to.
		# We are using an internal function of HTMLParser. 
		# See this: http://fredericiana.com/2010/10/08/decoding-html-entities-to-text-in-python/
		htmlParser = HTMLParser.HTMLParser()
 
		# Get IMDb info through PTP's ajax API used by the site when the user presses the auto fill button.
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( "http://passthepopcorn.me/ajax.php?action=torrent_info&imdb=%s" % releaseInfo.ImdbId );
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( response );
		
		# The response is JSON.
		# [{"title":"Devil's Playground","plot":"As the world succumbs to a zombie apocalypse, Cole a hardened mercenary, is chasing the one person who can provide a cure. Not only to the plague but to Cole's own incumbent destiny. DEVIL'S PLAYGROUND is a cutting edge British horror film that features zombies portrayed by free runners for a terrifyingly authentic representation of the undead","art":false,"year":"2010","director":[{"imdb":"1654324","name":"Mark McQueen","role":null}],"tags":"action, horror","writers":[{"imdb":"1057010","name":"Bart Ruspoli","role":" screenplay"}]}]

		jsonResult = json.loads( response );
		if len( jsonResult ) != 1:
			raise PtpUploaderException( "Bad PTP movie info JSON response: array length is not one.\nResponse:\n%s" % response );
	
		movie = jsonResult[ 0 ];
		releaseInfo.Title = movie[ "title" ];
		if ( releaseInfo.Title is None ) or len( releaseInfo.Title ) == 0: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: title is empty.\nResponse:\n%s" % response );
		releaseInfo.Title = htmlParser.unescape( releaseInfo.Title ) # PTP doesn't decodes properly the text.

		releaseInfo.Year = movie[ "year" ];
		if ( releaseInfo.Year is None ) or len( releaseInfo.Year ) == 0: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: year is empty.\nReponse:\n%s" % response );

		releaseInfo.MovieDescription = movie[ "plot" ];
		if releaseInfo.MovieDescription is None:
			releaseInfo.MovieDescription = ""; 

		releaseInfo.Tags = movie[ "tags" ];
		if releaseInfo.Tags is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: tags key doesn't exists.\nReponse:\n%s" % response );

		# PTP's upload page doesn't allows movies without tags. 
		if len( releaseInfo.Tags ) <= 0:
			raise PtpUploaderException( "PTP movie info returned without any tags." );

		releaseInfo.CoverArtUrl = movie[ "art" ];
		if releaseInfo.CoverArtUrl is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: art key doesn't exists.\nReponse:\n%s" % response );
	
		# It may be false... Eg.: "art": false
		if not releaseInfo.CoverArtUrl:
			releaseInfo.CoverArtUrl = "";

		# Director's name may not be present. For example: http://www.imdb.com/title/tt0864336/
		jsonDirectors = movie[ "director" ];
		if ( jsonDirectors is None ) or len( jsonDirectors ) < 1:
			releaseInfo.Directors = "None Listed"
		else:
			directorNames = []

			for jsonDirector in jsonDirectors:
				directorName = jsonDirector[ "name" ];
				if ( directorName is None ) or len( directorName ) == 0: 
					raise PtpUploaderException( "Bad PTP movie info JSON response: director name is empty.\nReponse:\n%s" % response );

				directorName = htmlParser.unescape( directorName ) # PTP doesn't decodes properly the text.
				directorNames.append( directorName )

			releaseInfo.SetDirectors( directorNames )

	@staticmethod
	def __UploadMovieGetParamsCommon(releaseInfo):
		commonParams = {
				"submit": "true",
				"type": releaseInfo.Type,
				"remaster_year": "",
				"remaster_title": "",
				"quality": releaseInfo.Quality,
				"codec": releaseInfo.Codec,
				"other_codec": "",
				"container": releaseInfo.Container,
				"other_container": "",
				"resolution": releaseInfo.ResolutionType,
				"other_resolution": releaseInfo.Resolution,
				"source": releaseInfo.Source,
				"other_source": "",
				"release_desc": releaseInfo.ReleaseDescription
				};

		paramList = commonParams.items()

		# scene only needed if it is specified
		if len( releaseInfo.Scene ) > 0:
			paramList.append( poster.encode.MultipartParam( "scene", "on" ) )

		return paramList;
	
	@staticmethod
	def __UploadMovieGetParamsForAddFormat(ptpId):
		groupId = ( "groupid", ptpId ); 
		return [ groupId ]; 

	@staticmethod
	def __UploadMovieGetParamsForNewMovie(releaseInfo):
		params = {
			"imdb": releaseInfo.ImdbId,
			"tomatoes": "",
			"metacritic": "",
			"title": releaseInfo.Title,
			"year": releaseInfo.Year,
			"image": releaseInfo.CoverArtUrl,
			"genre_tags": "---",
			"tags": releaseInfo.Tags,
			"album_desc": releaseInfo.MovieDescription,
			"trailer": "",
			};
			
		paramList = params.items();

		# Add the directors.
		# These needs to be added in order because of the "importance" field follows them.
		directors = releaseInfo.GetDirectors()
		for i in range( len( directors ) ):
			multipartParam = poster.encode.MultipartParam( "artists[]", directors[ i ] );
			multipartParam.name = "artists[]"; # MultipartParam escapes the square brackets to "artists%5B%5D". Change it back. :)
			paramList.append( multipartParam );

			# First director doesn't needs "importance".
			if i != 0:
				multipartParam = poster.encode.MultipartParam( "importance[]", "1" );
				multipartParam.name = "importance[]"; # MultipartParam escapes the square brackets to "importance%5B%5D". Change it back. :)
				paramList.append( multipartParam );
			
		return paramList;
	
	# If ptpId is None then it will added as a new movie.
	# If it is not None then it will be added as a new format to an existing movie.
	@staticmethod
	def UploadMovie(logger, releaseInfo, torrentPath, ptpId):
		url = "";
		paramList = Ptp.__UploadMovieGetParamsCommon( releaseInfo );
		
		# We always use HTTPS for uploading because if "Force HTTPS" is enabled in the profile then the HTTP upload is not working.
		if ptpId is None:
			logger.info( "Uploading torrent '%s' to PTP as a new movie." % torrentPath );
			url = "https://passthepopcorn.me/upload.php";
			paramList.extend( Ptp.__UploadMovieGetParamsForNewMovie( releaseInfo ) );
		else:
			logger.info( "Uploading torrent '%s' to PTP as a new format for 'http://passthepopcorn.me/torrents.php?id=%s'." % ( torrentPath, ptpId ) );
			url = "https://passthepopcorn.me/upload.php?groupid=%s" % ptpId;
			paramList.extend( Ptp.__UploadMovieGetParamsForAddFormat( ptpId ) ); 	
		
		# Add the torrent file.
		torrentFilename = os.path.basename( torrentPath ); # Filename without path.
		mimeType = mimetypes.guess_type( torrentFilename )[ 0 ] or 'application/x-bittorrent';
		multipartParam = poster.encode.MultipartParam( name = "file_input", filename = torrentFilename, filetype = mimeType, fileobj = open( torrentPath, "rb" ) );
		paramList.append( multipartParam );

		opener = poster.streaminghttp.register_openers()
		opener.add_handler( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		datagen, headers = poster.encode.multipart_encode( paramList )
		request = urllib2.Request( url, datagen, headers )
		result = opener.open( request )
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( response );
		
		# If the repsonse contains our announce url then we are on the upload page and the upload wasn't successful.
		if response.find( Settings.PtpAnnounceUrl ) != -1:
			raise PtpUploaderException( "Torrent upload to PTP failed: we are still at the upload page." )
		
		# Response format in case of success: http://passthepopcorn.me/torrents.php?id=28622
		match = re.match( r"https?://passthepopcorn\.me/torrents\.php\?id=(\d+)", result.url );
		if match is None:
			raise PtpUploaderException( "Torrent upload to PTP failed: result url '%s' is not the expected one." % result.url )			

		# Refresh data is not needed for new movies because PTP does this automatically.
		# So we only do a refresh when adding as a new format.
		if ptpId is None:
			ptpId = match.group( 1 )
		else:
			# response contains the movie page of the uploaded movie.
			Ptp.TryRefreshMoviePage( logger, ptpId, response );

		return ptpId;

	# ptpId: movie page id. For example: ptpId is 28622 for the movie with url: http://passthepopcorn.me/torrents.php?id=28622 	
	# page: the html contents of the movie page.
	@staticmethod
	def TryRefreshMoviePage(logger, ptpId, page):
		logger.info( "Trying to refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'." % ptpId );

		# We don't care if this fails. Our upload is complete anyway. :) 
		try:
			# Searching for: <a href="torrents.php?action=imdb&amp;groupid=3704&amp;auth=...">[Refresh Data]</a>
			matches = re.search( r'<a href="torrents.php\?action=imdb&amp;groupid=\d+&amp;auth=(.+)">\[Refresh Data\]</a>', page );
			if not matches:
				logger.info( "Couldn't refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'. Authorization key couldn't be found." % ptpId );
				return;
		
			auth = matches.group( 1 );
		
			opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
			request = urllib2.Request( "http://passthepopcorn.me/torrents.php?action=imdb&groupid=%s&auth=%s" % ( ptpId, auth ) );
			result = opener.open( request );
			response = result.read();
		except Exception:
			logger.exception( "Couldn't refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'. Got exception." % ptpId );

	@staticmethod
	def SendPrivateMessage(userId, subject, message):
		Globals.Logger.info( "Sending private message on PTP." );

		# We need to load the send message page for the authentication key.
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) )
		request = urllib2.Request( "http://passthepopcorn.me/inbox.php?action=compose&to=%s" % userId )
		result = opener.open( request )
		response = result.read()
		Ptp.CheckIfLoggedInFromResponse( response )

		matches = re.search( r"""<input type="hidden" name="auth" value="(.+)" />""", response )
		if not matches:
			Globals.Logger.info( "Authorization key couldn't be found." )
			return

		auth = matches.group( 1 )

		# Send the message.
		# We always use HTTPS for sending message because if "Force HTTPS" is enabled in the profile then the HTTP message sending is not working.
		postData = urllib.urlencode( { "toid": userId, "subject": subject, "body": message, "auth": auth, "action": "takecompose" } )
		request = urllib2.Request( "https://passthepopcorn.me/inbox.php", postData )
		result = opener.open( request )
		response = result.read()
		Ptp.CheckIfLoggedInFromResponse( response )