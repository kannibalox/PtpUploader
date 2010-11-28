from Globals import Globals
from PtpMovieSearchResult import PtpMovieSearchResult
from PtpUploaderException import PtpUploaderException
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
		maximumRetries = 2;
		
		while True:
			try:
				Ptp.__LoginInternal();
				return;
			except Exception:
				if maximumRetries > 0:
					maximumRetries -= 1;
					time.sleep( 30 ); # Wait 30 seconds and retry.
				else:
					raise;
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( 'action="login.php"' ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to PTP. Probably due to the bad session key in settings." )
				
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
		match = re.match( r"http://passthepopcorn.me/torrents.php\?id=(\d+)", result.url );
		if match is None:
			logger.info( "Movie with IMDb id '%s' doesn't exists on PTP." % imdbId );
			return PtpMovieSearchResult( ptpId = None, moviePageHtml = None );
		elif response.find( "<h2>Error 404</h2>" ) != -1: # For some deleted movies PTP return with this error.
			logger.info( "Movie with IMDb id '%s' doesn't exists on PTP. (Got error 404.)" % imdbId );
			return PtpMovieSearchResult( ptpId = None, moviePageHtml = None );
		else:
			ptpId = match.group( 1 );
			logger.info( "Movie with IMDb id '%s' exists on PTP at '%s'." % ( imdbId, result.url ) );
			return PtpMovieSearchResult( ptpId, response );

	@staticmethod
	def FillImdbInfo(logger, ptpUploadInfo):
		logger.info( "Downloading movie info from PTP for IMDb id '%s'." % ptpUploadInfo.ImdbId );

		# PTP doesn't decodes the HTML entity references (like "&#x26;" to "&") in the JSON response, so we have to.
		# We are using an internal function of HTMLParser. 
		# See this: http://fredericiana.com/2010/10/08/decoding-html-entities-to-text-in-python/
		htmlParser = HTMLParser.HTMLParser()
 
		# Get IMDb info through PTP's ajax API used by the site when the user presses the auto fill button.
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( "http://passthepopcorn.me/ajax.php?action=torrent_info&imdb=%s" % ptpUploadInfo.ImdbId );
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( response );
		
		# The response is JSON.
		# [{"title":"Devil's Playground","plot":"As the world succumbs to a zombie apocalypse, Cole a hardened mercenary, is chasing the one person who can provide a cure. Not only to the plague but to Cole's own incumbent destiny. DEVIL'S PLAYGROUND is a cutting edge British horror film that features zombies portrayed by free runners for a terrifyingly authentic representation of the undead","art":false,"year":"2010","director":[{"imdb":"1654324","name":"Mark McQueen","role":null}],"tags":"action, horror","writers":[{"imdb":"1057010","name":"Bart Ruspoli","role":" screenplay"}]}]

		jsonResult = json.loads( response );
		if len( jsonResult ) != 1:
			raise PtpUploaderException( "Bad PTP movie info JSON response: array length is not one.\nResponse:\n%s" % response );
	
		movie = jsonResult[ 0 ];
		ptpUploadInfo.Title = movie[ "title" ];
		if ( ptpUploadInfo.Title is None ) or len( ptpUploadInfo.Title ) == 0: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: title is empty.\nResponse:\n%s" % response );
		ptpUploadInfo.Title = htmlParser.unescape( ptpUploadInfo.Title ) # PTP doesn't decodes properly the text.

		ptpUploadInfo.Year = movie[ "year" ];
		if ( ptpUploadInfo.Year is None ) or len( ptpUploadInfo.Year ) == 0: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: year is empty.\nReponse:\n%s" % response );

		ptpUploadInfo.MovieDescription = movie[ "plot" ];
		if ptpUploadInfo.MovieDescription is None:
			ptpUploadInfo.MovieDescription = ""; 

		ptpUploadInfo.Tags = movie[ "tags" ];
		if ptpUploadInfo.Tags is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: tags key doesn't exists.\nReponse:\n%s" % response );

		# PTP's upload page doesn't allows movies without tags. 
		if len( ptpUploadInfo.Tags ) <= 0:
			raise PtpUploaderException( "PTP movie info returned without any tags." );

		ptpUploadInfo.CoverArtUrl = movie[ "art" ];
		if ptpUploadInfo.CoverArtUrl is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: art key doesn't exists.\nReponse:\n%s" % response );
	
		# It may be false... Eg.: "art": false
		if not ptpUploadInfo.CoverArtUrl:
			ptpUploadInfo.CoverArtUrl = "";

		# Director's name may not be present. For example: http://www.imdb.com/title/tt0864336/
		jsonDirectors = movie[ "director" ];
		if ( jsonDirectors is None ) or len( jsonDirectors ) < 1: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: no directors.\nReponse:\n%s" % response );

		for jsonDirector in jsonDirectors:
			directorName = jsonDirector[ "name" ];
			if ( directorName is None ) or len( directorName ) == 0: 
				raise PtpUploaderException( "Bad PTP movie info JSON response: director name is empty.\nReponse:\n%s" % response );

			directorName = htmlParser.unescape( directorName ) # PTP doesn't decodes properly the text.
			ptpUploadInfo.Directors.append( directorName )

	@staticmethod
	def __UploadMovieGetParamsCommon(ptpUploadInfo):
		commonParams = {
				"submit": "true",
				"type": ptpUploadInfo.Type,
				"remaster_year": "",
				"remaster_title": "",
				"quality": ptpUploadInfo.Quality,
				"codec": ptpUploadInfo.Codec,
				"other_codec": "",
				"container": ptpUploadInfo.Container,
				"other_container": "",
				"resolution": ptpUploadInfo.ResolutionType,
				"other_resolution": ptpUploadInfo.Resolution,
				"source": ptpUploadInfo.Source,
				"other_source": "",
				"release_desc": ptpUploadInfo.ReleaseDescription
				};

		paramList = commonParams.items()

		# scene only needed if it is specified
		if len( ptpUploadInfo.Scene ) > 0:
			paramList.append( poster.encode.MultipartParam( "scene", "on" ) )

		return paramList;
	
	@staticmethod
	def __UploadMovieGetParamsForAddFormat(ptpId):
		groupId = ( "groupid", ptpId ); 
		return [ groupId ]; 

	@staticmethod
	def __UploadMovieGetParamsForNewMovie(ptpUploadInfo):
		params = {
			"imdb": ptpUploadInfo.ImdbId,
			"tomatoes": "",
			"metacritic": "",
			"title": ptpUploadInfo.Title,
			"year": ptpUploadInfo.Year,
			"image": ptpUploadInfo.CoverArtUrl,
			"genre_tags": "---",
			"tags": ptpUploadInfo.Tags,
			"album_desc": ptpUploadInfo.MovieDescription,
			"trailer": "",
			};
			
		paramList = params.items();

		# Add the directors.
		# These needs to be added in order because of the "importance" field follows them.
		for i in range( len( ptpUploadInfo.Directors ) ):
			multipartParam = poster.encode.MultipartParam( "artists[]", ptpUploadInfo.Directors[ i ] );
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
	def UploadMovie(logger, ptpUploadInfo, torrentPath, ptpId):
		url = "";
		paramList = Ptp.__UploadMovieGetParamsCommon( ptpUploadInfo );
		
		if ptpId is None:
			logger.info( "Uploading torrent '%s' to PTP as a new movie." % torrentPath );
			url = "http://passthepopcorn.me/upload.php";
			paramList.extend( Ptp.__UploadMovieGetParamsForNewMovie( ptpUploadInfo ) );
		else:
			logger.info( "Uploading torrent '%s' to PTP as a new format for 'http://passthepopcorn.me/torrents.php?id=%s'." % ( torrentPath, ptpId ) );
			url = "http://passthepopcorn.me/upload.php?groupid=%s" % ptpId;
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
		match = re.match( r"http://passthepopcorn.me/torrents.php\?id=(\d+)", result.url );
		if match is None:
			raise PtpUploaderException( "Torrent upload to PTP failed: result url '%s' is not the expected one." % result.url )			

		# Return with PTP id of the movie.
		ptpId = match.group( 1 )
		
		# response contains the movie page of the uploaded movie.
		Ptp.TryRefreshMoviePage( logger, ptpId, response );
		
		return ptpId;

	# ptpId: movie page id. For example: ptpId is 28622 for the movie with url: http://passthepopcorn.me/torrents.php?id=28622 	
	# page: the html contents of the movie page.
	@staticmethod
	def TryRefreshMoviePage(logger, ptpId, page):
		logger.info( "Trying to refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'." % ptpId );

		# We don't care if this fails. This should be built-in on server side. Our upload is complete anyway. :) 
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