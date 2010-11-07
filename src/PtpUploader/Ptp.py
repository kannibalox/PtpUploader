from Globals import Globals;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import poster;
import simplejson as json;

import mimetypes;
import os;
import re;
import time;
import urllib;
import urllib2;

class Ptp:
	class MovieOnPtpResult:
		def __init__(self):
			self.PtpId = None;
			self.Xvid_DVDrip_OnSite = False;
			self.Xvid_BDrip_OnSite = False;
			self.X264_720p_OnSite = False;
			self.X264_1080p_OnSite = False;
			
		def IsReleaseExists(self, releaseInfo):
			if self.PtpId is None:
				return False;

			if releaseInfo.PtpUploadInfo.Quality == "High Definition":
				if releaseInfo.PtpUploadInfo.Codec == "x264" and releaseInfo.ResolutionType == "720p":
					return self.X264_720p_OnSite;
				elif releaseInfo.PtpUploadInfo.Codec == "x264" and releaseInfo.ResolutionType == "1080p":
					return self.X264_1080p_OnSite;
			elif releaseInfo.PtpUploadInfo.Quality == "Standard Definition":
				if releaseInfo.PtpUploadInfo.Source == "DVD":
					return self.Xvid_DVDrip_OnSite or self.Xvid_BDrip_OnSite; # BD rip trumps DVD rip.
				elif releaseInfo.PtpUploadInfo.Source == "Blu-Ray":
					return self.Xvid_BDrip_OnSite;
				
			# This can't possible.			
			raise PtpUploaderException( "MovieOnPtpResult got unsupported release type from ReleaseInfo for release '%s'." % releaseInfo.Announcement.ReleaseName ); 

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
	# returns with MovieOnPtpResult
	@staticmethod
	def GetMoviePageOnPtp(imdbId):
		Globals.Logger.info( "Trying to find movie with IMDb id '%s' on PTP." % imdbId );
		
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
		request = urllib2.Request( "http://passthepopcorn.me/torrents.php?imdb=%s" % imdbId );
		result = opener.open( request );
		response = result.read();
		Ptp.CheckIfLoggedInFromResponse( response );

		movieResult = Ptp.MovieOnPtpResult();

		# If there is a movie: result.url = http://passthepopcorn.me/torrents.php?id=28577
		# If there is no movie: result.url = http://passthepopcorn.me/torrents.php?imdb=1535492
		match = re.match( r"http://passthepopcorn.me/torrents.php\?id=(\d+)", result.url );
		if match is None:
			movieResult.PtpId = None;
			Globals.Logger.info( "Movie with IMDb id '%s' doesn't exists on PTP." % imdbId );
		elif response.find( "<h2>Error 404</h2>" ) != -1: # For some deleted movies PTP return with this error.
			movieResult.PtpId = None;
			Globals.Logger.info( "Movie with IMDb id '%s' doesn't exists on PTP. (Got error 404.)" % imdbId );
		else:
			movieResult.PtpId = match.group( 1 );
			Globals.Logger.info( "Movie with IMDb id '%s' exists on PTP at '%s'." % ( imdbId, result.url ) );
		
			movieResult.Xvid_DVDrip_OnSite = response.find( "XviD / AVI / DVD" ) != -1;
			movieResult.Xvid_BDrip_OnSite  = response.find( "XviD / AVI / Blu-Ray" ) != -1;

			if response.find( "x264 / MKV / Blu-Ray / 720p" ) != -1 or response.find( "x264 / MKV / HD-DVD / 720p" ) != -1:
				movieResult.X264_720p_OnSite = True;

			if response.find( "x264 / MKV / Blu-Ray / 1080p" ) != -1 or response.find( "x264 / MKV / HD-DVD / 1080p" ) != -1:
				movieResult.X264_1080p_OnSite = True;

		return movieResult;
		
	# imdbId: IMDb id. Eg.: 0137363 for http://www.imdb.com/title/tt0137363/
	@staticmethod
	def FillImdbInfo(ptpUploadInfo):
		Globals.Logger.info( "Downloading movie info from PTP for IMDb id '%s'." % ptpUploadInfo.ImdbId );
		
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
			raise PtpUploaderException( "Bad PTP movie info JSON response: array length is not one." );
	
		movie = jsonResult[ 0 ];
		ptpUploadInfo.Title = movie[ "title" ];
		if ( ptpUploadInfo.Title is None ) or len( ptpUploadInfo.Title ) == 0: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: title is empty." );

		ptpUploadInfo.Year = movie[ "year" ];
		if ( ptpUploadInfo.Year is None ) or len( ptpUploadInfo.Year ) == 0: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: year is empty." );

		ptpUploadInfo.MovieDescription = movie[ "plot" ];
		if ptpUploadInfo.MovieDescription is None:
			ptpUploadInfo.MovieDescription = ""; 

		ptpUploadInfo.Tags = movie[ "tags" ];
		if ptpUploadInfo.Tags is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: tags key doesn't exists." );

		ptpUploadInfo.CoverArtUrl = movie[ "art" ];
		if ptpUploadInfo.CoverArtUrl is None: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: art key doesn't exists." );
	
		# It may be false... Eg.: "art": false
		if not ptpUploadInfo.CoverArtUrl:
			ptpUploadInfo.CoverArtUrl = "";

		jsonDirectors = movie[ "director" ];
		if ( jsonDirectors is None ) or len( jsonDirectors ) < 1: 
			raise PtpUploaderException( "Bad PTP movie info JSON response: no directors." );

		for jsonDirector in jsonDirectors:
			directorName = jsonDirector[ "name" ];
			if ( directorName is None ) or len( directorName ) == 0: 
				raise PtpUploaderException( "Bad PTP movie info JSON response: director name is empty." );
			ptpUploadInfo.Directors.append( directorName );

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
	def UploadMovie(ptpUploadInfo, torrentPath, ptpId):
		url = "";
		paramList = Ptp.__UploadMovieGetParamsCommon( ptpUploadInfo );
		
		if ptpId is None:
			Globals.Logger.info( "Uploading torrent '%s' to PTP as a new movie." % torrentPath );
			url = "http://passthepopcorn.me/upload.php";
			paramList.extend( Ptp.__UploadMovieGetParamsForNewMovie( ptpUploadInfo ) );
		else:
			Globals.Logger.info( "Uploading torrent '%s' to PTP as a new format for 'http://passthepopcorn.me/torrents.php?id=%s'." % ( torrentPath, ptpId ) );
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
		Ptp.TryRefreshMoviePage( ptpId, response );
		
		return ptpId;

	# ptpId: movie page id. For example: ptpId is 28622 for the movie with url: http://passthepopcorn.me/torrents.php?id=28622 	
	# page: the html contents of the movie page.
	@staticmethod
	def TryRefreshMoviePage(ptpId, page):
		Globals.Logger.info( "Trying to refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'." % ptpId );

		# We don't care if this fails. This should be built-in on server side. Our upload is complete anyway. :) 
		try:
			# Searching for: <a href="torrents.php?action=imdb&amp;groupid=3704&amp;auth=...">[Refresh Data]</a>
			matches = re.search( r'<a href="torrents.php\?action=imdb&amp;groupid=\d+&amp;auth=(.+)">\[Refresh Data\]</a>', page );
			if not matches:
				Globals.Logger.info( "Couldn't refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'. Authorization key couldn't be found." % ptpId );
				return;
		
			auth = matches.group( 1 );
		
			opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( Globals.CookieJar ) );
			request = urllib2.Request( "http://passthepopcorn.me/torrents.php?action=imdb&groupid=%s&auth=%s" % ( ptpId, auth ) );
			result = opener.open( request );
			response = result.read();
		except Exception:
			Globals.Logger.exception( "Couldn't refresh data for 'http://passthepopcorn.me/torrents.php?id=%s'. Got exception." % ptpId );
			pass;			