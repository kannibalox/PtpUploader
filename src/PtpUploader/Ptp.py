from MyGlobals import MyGlobals
from PtpMovieSearchResult import PtpMovieSearchResult
from PtpUploaderException import *
from Settings import Settings

import poster

import mimetypes
import os
import re
import time
import traceback
import urllib
import urllib2

class Ptp:
	# It doesn't work with the default Python User-Agent...
	RequiredHttpHeader = { "User-Agent": "Wget/1.13.4" }

	@staticmethod
	def __LoginInternal():
		if len( Settings.PtpUserName ) <= 0:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your user name is not specified.." )

		if len( Settings.PtpPassword ) <= 0:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your password is not specified.." )

		MyGlobals.Logger.info( "Logging in to PTP." );
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		postData = urllib.urlencode( { "username": Settings.PtpUserName, "password": Settings.PtpPassword, "keeplogged": "1" } )
		request = urllib2.Request( "http://passthepopcorn.me/login.php", postData, Ptp.RequiredHttpHeader );
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( result, response );

	@staticmethod
	def Login():
		maximumTries = 3

		while True:
			try:
				Ptp.__LoginInternal()
				return
			except PtpUploaderInvalidLoginException:
				raise
			except Exception:
				if maximumTries > 1:
					maximumTries -= 1
					time.sleep( 30 ) # Wait 30 seconds and retry.
				else:
					raise

	@staticmethod
	def __CheckIfLoggedInFromResponseLogResponse(result, responseBody):
		MyGlobals.Logger.info( "MSG: %s" % result.msg  )
		MyGlobals.Logger.info( "CODE: %s" % result.code  )
		MyGlobals.Logger.info( "URL: %s" % result.url )
		MyGlobals.Logger.info( "HEADERS: %s" % result.headers )
		MyGlobals.Logger.info( "STACK: %s" % traceback.format_stack() ) 
		MyGlobals.Logger.info( "RESPONSE BODY: %s" % responseBody ) 

	@staticmethod
	def CheckIfLoggedInFromResponse(result, responseBody):
		if responseBody.find( """<a href="login.php?act=recover">""" ) != -1:
			Ptp.__CheckIfLoggedInFromResponseLogResponse( result, responseBody )
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Probably due to the bad user name or password." )
		
		if responseBody.find( """<p>Your IP has been banned.</p>""" ) != -1:
			Ptp.__CheckIfLoggedInFromResponseLogResponse( result, responseBody )
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your IP has been banned." )
		
		if responseBody.find( 'action="login.php"' ) != -1:
			Ptp.__CheckIfLoggedInFromResponseLogResponse( result, responseBody )
			raise PtpUploaderException( "Looks like you are not logged in to PTP. Probably due to the bad user name or password." )
	
	# PTP expects 7 character long IMDb IDs.
	# E.g.: it can't find movie with IMDb ID 59675, only with 0059675. (IMDb redirects to the latter.)
	@staticmethod
	def NormalizeImdbIdForPtp(imdbId):
		if len( imdbId ) < 7:
			return imdbId.rjust( 7, '0' )
		elif len( imdbId ) > 7:
			raise PtpUploaderException( "IMDb ID '%s' is longer than seven characters." % imdbId )
		else:
			return imdbId
	
	# ptpId must be a valid id		
	# returns with PtpMovieSearchResult
	@staticmethod
	def GetMoviePageOnPtp(logger, ptpId):
		logger.info( "Getting movie page for PTP id '%s'." % ptpId )
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( "http://passthepopcorn.me/torrents.php?id=%s&json=1" % ptpId )
		result = opener.open( request )
		response = result.read()
		Ptp.CheckIfLoggedInFromResponse( result, response )

		if response.find( "<h2>Error 404</h2>" ) != -1:
			raise PtpUploaderException( "Movie with PTP id '%s' doesn't exists." % ptpId )

		return PtpMovieSearchResult( ptpId, response )

	# imdbId: IMDb id. Eg.: 0137363 for http://www.imdb.com/title/tt0137363/
	# returns with PtpMovieSearchResult
	@staticmethod
	def GetMoviePageOnPtpByImdbId(logger, imdbId):
		logger.info( "Trying to find movie with IMDb id '%s' on PTP." % imdbId );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		request = urllib2.Request( "http://passthepopcorn.me/torrents.php?imdb=%s&json=1" % Ptp.NormalizeImdbIdForPtp( imdbId ) )
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( result, response );

		# If there is a movie: result.url = http://passthepopcorn.me/torrents.php?id=28577
		# If there is no movie: result.url = http://passthepopcorn.me/torrents.php?imdb=1535492
		match = re.match( r".*?passthepopcorn\.me/torrents\.php\?id=(\d+)", result.url );
		if match is not None:
			ptpId = match.group( 1 );
			url = result.url
			url = url.replace( "&json=1", "" )
			logger.info( "Movie with IMDb id '%s' exists on PTP at '%s'." % ( imdbId, url ) );
			return PtpMovieSearchResult( ptpId, response );
		elif response.find( "<h2>Error 404</h2>" ) != -1: # For some deleted movies PTP return with this error.
			logger.info( "Movie with IMDb id '%s' doesn't exists on PTP. (Got error 404.)" % imdbId );
			return PtpMovieSearchResult( ptpId = "", moviePageJsonText = None );
		elif response.find( "<h2>Your search did not match anything.</h2>" ) != -1: 
			logger.info( "Movie with IMDb id '%s' doesn't exists on PTP." % imdbId );
			return PtpMovieSearchResult( ptpId = "", moviePageJsonText = None );
		else: # Multiple movies with the same IMDb id.
			raise PtpUploaderException( "There are multiple movies on PTP with IMDb id '%s'." % imdbId )

	@staticmethod
	def __UploadMovieGetParamsCommon( releaseInfo, releaseDescription ):
		commonParams = {
				"submit": "true",
				"type": releaseInfo.Type,
				"remaster_year": releaseInfo.RemasterYear,
				"remaster_title": releaseInfo.RemasterTitle,
				"codec": releaseInfo.Codec,
				"other_codec": releaseInfo.CodecOther,
				"container": releaseInfo.Container,
				"other_container": releaseInfo.ContainerOther,
				"resolution": releaseInfo.ResolutionType,
				"other_resolution": releaseInfo.Resolution,
				"source": releaseInfo.Source,
				"other_source": releaseInfo.SourceOther,
				"release_desc": releaseDescription,
				"nfo_text": releaseInfo.Nfo
				};

		paramList = commonParams.items()

		# scene only needed if it is specified
		if releaseInfo.IsSceneRelease():
			paramList.append( poster.encode.MultipartParam( "scene", "on" ) )

		# other category is only needed if it is specified
		if releaseInfo.IsSpecialRelease():
			paramList.append( poster.encode.MultipartParam( "special", "on" ) )

		# remaster is only needed if it is specified
		if len( releaseInfo.RemasterYear ) > 0 or len( releaseInfo.RemasterTitle ) > 0:
			paramList.append( poster.encode.MultipartParam( "remaster", "on" ) )

		subtitles = releaseInfo.GetSubtitles()
		for subtitle in subtitles:
			multipartParam = poster.encode.MultipartParam( "subtitles[]", subtitle )
			multipartParam.name = "subtitles[]" # MultipartParam escapes the square brackets to "%5B%5D". Change it back. :)
			paramList.append( multipartParam )

		return paramList;
	
	@staticmethod
	def __UploadMovieGetParamsForAddFormat(ptpId):
		groupId = ( "groupid", ptpId ); 
		return [ groupId ]; 

	@staticmethod
	def __UploadMovieGetParamsForNewMovie(releaseInfo):
		params = {
			"title": releaseInfo.Title,
			"year": releaseInfo.Year,
			"image": releaseInfo.CoverArtUrl,
			"tags": releaseInfo.Tags,
			"album_desc": releaseInfo.MovieDescription,
			"trailer": releaseInfo.YouTubeId,
			};
			
		paramList = params.items();

		# Add the IMDb ID.
		if releaseInfo.IsZeroImdbId():
			paramList.append( poster.encode.MultipartParam( "imdb", "" ) )
		else:
			paramList.append( poster.encode.MultipartParam( "imdb", Ptp.NormalizeImdbIdForPtp( releaseInfo.GetImdbId() ) ) )

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
	
	# Returns with the auth key.
	@staticmethod
	def UploadMovie(logger, releaseInfo, torrentPath, releaseDescription):
		url = "";
		paramList = Ptp.__UploadMovieGetParamsCommon( releaseInfo, releaseDescription );
		
		# We always use HTTPS for uploading because if "Force HTTPS" is enabled in the profile then the HTTP upload is not working.
		if releaseInfo.HasPtpId():
			logger.info( "Uploading torrent '%s' to PTP as a new format for 'http://passthepopcorn.me/torrents.php?id=%s'." % ( torrentPath, releaseInfo.PtpId ) );
			url = "https://tls.passthepopcorn.me/upload.php?groupid=%s" % releaseInfo.PtpId;
			paramList.extend( Ptp.__UploadMovieGetParamsForAddFormat( releaseInfo.PtpId ) ); 	
		else:
			logger.info( "Uploading torrent '%s' to PTP as a new movie." % torrentPath );
			url = "https://tls.passthepopcorn.me/upload.php";
			paramList.extend( Ptp.__UploadMovieGetParamsForNewMovie( releaseInfo ) );
		
		# Add the torrent file.
		torrentFilename = os.path.basename( torrentPath ); # Filename without path.
		mimeType = mimetypes.guess_type( torrentFilename )[ 0 ] or 'application/x-bittorrent';
		multipartParam = poster.encode.MultipartParam( name = "file_input", filename = torrentFilename, filetype = mimeType, fileobj = open( torrentPath, "rb" ) );
		paramList.append( multipartParam );

		opener = poster.streaminghttp.register_openers()
		opener.add_handler( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		datagen, headers = poster.encode.multipart_encode( paramList )
		request = urllib2.Request( url, datagen, headers )
		result = opener.open( request )
		response = result.read();
		response = response.decode( "utf-8", "ignore" )
		Ptp.CheckIfLoggedInFromResponse( result, response );
		
		# If the repsonse contains our announce url then we are on the upload page and the upload wasn't successful.
		if response.find( Settings.PtpAnnounceUrl ) != -1:
			# Get the error message.
			# Possible formats:
			# <p style="color: red; text-align: center;">No torrent file uploaded, or file is empty.</p>
			# <p style="color: red;text-align:center;">Please enter at least one director</p>
			errorMessage = ""
			match = re.search( r"""<p style="color: ?red; ?text-align: ?center;">(.+?)</p>""", response )
			if match is not None:
				errorMessage = match.group( 1 )

			raise PtpUploaderException( "Upload to PTP failed: '%s'. (We are still on the upload page.)" % errorMessage )

		# URL format in case of successful upload: http://passthepopcorn.me/torrents.php?id=9329&torrentid=91868 
		match = re.match( r".*?passthepopcorn\.me/torrents\.php\?id=(\d+)&torrentid=(\d+)", result.url )
		if match is None:
			raise PtpUploaderException( "Upload to PTP failed: result URL '%s' is not the expected one." % result.url )
		
		ptpId = match.group( 1 )
		releaseInfo.PtpTorrentId = match.group( 2 )

		# We store the the auth key becaues it will be needed for adding the subtitles.
		match = re.search( r"""var authkey = "(.+?)";""", response )
		if match is None:
			raise PtpUploaderException( "Authentication key can't be found in the response." )
		authKey = match.group( 1 )

		if not releaseInfo.HasPtpId():
			releaseInfo.PtpId = ptpId

		return authKey

	@staticmethod
	def SendPrivateMessage(userId, subject, message):
		MyGlobals.Logger.info( "Sending private message on PTP." );

		# We need to load the send message page for the authentication key.
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		request = urllib2.Request( "http://passthepopcorn.me/inbox.php?action=compose&to=%s" % userId )
		result = opener.open( request )
		response = result.read()
		Ptp.CheckIfLoggedInFromResponse( result, response )

		matches = re.search( r"""<input type="hidden" name="auth" value="(.+)" />""", response )
		if not matches:
			MyGlobals.Logger.info( "Authorization key couldn't be found." )
			return

		auth = matches.group( 1 )

		# Send the message.
		# We always use HTTPS for sending message because if "Force HTTPS" is enabled in the profile then the HTTP message sending is not working.
		postData = urllib.urlencode( { "toid": userId, "subject": subject, "body": message, "auth": auth, "action": "takecompose" } )
		request = urllib2.Request( "https://tls.passthepopcorn.me/inbox.php", postData )
		result = opener.open( request )
		response = result.read()
		Ptp.CheckIfLoggedInFromResponse( result, response )
		
	# languageId: see the source of the Subtitle manager page on PTP 
	@staticmethod
	def AddSubtitle(authKey, torrentId, languageId):
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "action": "takesubtitle", "auth": authKey, "torrentid": torrentId, "languageid": languageId, "included": "1" } )
		request = urllib2.Request( "https://tls.passthepopcorn.me/torrents.php", postData )
		result = opener.open( request )
		response = result.read()
		Ptp.CheckIfLoggedInFromResponse( result, response )
