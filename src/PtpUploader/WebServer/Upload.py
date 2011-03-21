from Job.JobStartMode import JobStartMode
from WebServer import app

from Authentication import requires_auth
from MyGlobals import MyGlobals
from Database import Database
from NfoParser import NfoParser
from Ptp import Ptp
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import Module, render_template, request
from werkzeug import secure_filename

import os
import re
import urlparse

def IsFileAllowed(filename):
	root, extension = os.path.splitext( filename )
	return extension == ".torrent"

# Needed because urlparse return with empty netloc if protocol is not set. 
def AddHttpToUrl(url):
	if url.startswith( "http://" ) or url.startswith( "https://" ):
		return url
	else:
		return "http://" + url

def GetYouTubeId(text):
	url = urlparse.urlparse( AddHttpToUrl( text ) )
	if url.netloc == "youtube.com" or url.netloc == "www.youtube.com":
		params = urlparse.parse_qs( url.query )
		youTubeIdList = params.get( "v" )
		if youTubeIdList is not None:
			return youTubeIdList[ 0 ]

	return ""

def GetPtpOrImdbId(releaseInfo, text):
	imdbId = NfoParser.GetImdbId( text )
	if len( imdbId ) > 0:
		releaseInfo.ImdbId = imdbId 
	else:
		# Using urlparse because of torrent permalinks:
		# https://passthepopcorn.me/torrents.php?id=9730&torrentid=72322
		url = urlparse.urlparse( AddHttpToUrl( text ) )
		if url.netloc == "passthepopcorn.me" or url.netloc == "www.passthepopcorn.me":
			params = urlparse.parse_qs( url.query )
			ptpIdList = params.get( "id" )
			if ptpIdList is not None:
				releaseInfo.PtpId = ptpIdList[ 0 ]

def UploadTorrentFile(releaseInfo, request):
	file = request.files.get( "file_input" )
	# file is is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.) 
	if ( not file ) or ( not IsFileAllowed( file.filename ) ):
		return False
		
	filename = secure_filename( file.filename )
	releaseInfo.SourceTorrentPath = os.path.join( Settings.GetTemporaryPath(), filename )
	file.save( releaseInfo.SourceTorrentPath )

	releaseInfo.AnnouncementSourceName = "torrent"
	releaseInfo.ReleaseName = file.filename.replace( ".torrent", "" ) # TODO
	return True 

def UploadTorrentSiteLink(releaseInfo, request):
	torrentPageLink = request.values[ "torrent_site_link" ]
	if len( torrentPageLink ) <= 0:
		return False
		
	source, id = MyGlobals.PtpUploader.TheJobManager.SourceFactory.GetSourceAndIdByUrl( torrentPageLink )
	if source is None:
		return False
		
	releaseInfo.AnnouncementSourceName = source.Name
	releaseInfo.AnnouncementId = id
	return True 

def UploadFile(releaseInfo, request):
	path = request.values[ "existingfile_input" ]
	if len( path ) <= 0:
		return False

	# TODO: implement me
	#releaseInfo.AnnouncementSourceName = "file"
	#releaseInfo.ReleaseName
	#return True
	return False 

@app.route( '/upload/', methods=[ 'GET', 'POST' ] )
@requires_auth
def upload():
	if request.method == 'POST':
		releaseInfo = ReleaseInfo()
	
		# Announcement
		
		if UploadTorrentFile( releaseInfo, request ):
			pass
		elif UploadFile( releaseInfo, request ):
			pass
		elif UploadTorrentSiteLink( releaseInfo, request ):
			pass
		else:
			return "Select something to upload!"

		# For PTP
		
		releaseInfo.Type = request.values[ "type" ]
		GetPtpOrImdbId( releaseInfo, request.values[ "imdb" ] )
		releaseInfo.Directors = request.values[ "artists[]" ]
		releaseInfo.Title = request.values[ "title" ]
		releaseInfo.Year = request.values[ "year" ]
		releaseInfo.Tags = request.values[ "tags" ]
		releaseInfo.MovieDescription = request.values[ "album_desc" ]
		releaseInfo.CoverArtUrl = request.values[ "image" ]
		releaseInfo.YouTubeId = GetYouTubeId( request.values[ "trailer" ] )
		releaseInfo.MetacriticUrl = request.values[ "metacritic" ]
		releaseInfo.RottenTomatoesUrl = request.values[ "tomatoes" ]
		
		scene = request.values.get( "scene" )
		if scene is not None:
			releaseInfo.Scene = "on"
		
		quality = request.values[ "quality" ]
		if quality != "---":
			releaseInfo.Quality = quality

		codec = request.values[ "codec" ]
		if codec != "---":
			releaseInfo.Codec = codec
			 
		releaseInfo.CodecOther = request.values[ "other_codec" ]

		container = request.values[ "container" ]
		if container != "---": 
			releaseInfo.Container = container
		
		releaseInfo.ContainerOther = request.values[ "other_container" ]
		
		resolutionType = request.values[ "resolution" ]
		if resolutionType != "---": 
			releaseInfo.ResolutionType = resolutionType
		
		releaseInfo.Resolution = request.values[ "other_resolution" ] 
		
		source = request.values[ "source" ]
		if source != "---":
			releaseInfo.Source = source
			
		releaseInfo.SourceOther = request.values[ "other_source" ]
		
		releaseInfo.ReleaseDescription = request.values[ "release_desc" ]
		releaseInfo.RemasterTitle = request.values[ "remaster_title" ]
		releaseInfo.RemasterYear = request.values[ "remaster_year" ]
		
		# Other
		
		forceUpload = request.values.get( "force_upload" )
		if forceUpload is None:
			releaseInfo.JobStartMode = JobStartMode.Manual
		else:
			releaseInfo.JobStartMode = JobStartMode.ManualForced
		
		#releaseInfo.InternationalTitle = "" # International title of the movie. Eg.: The Secret in Their Eyes. Needed for renaming releases coming from Cinemageddon.
		#releaseInfo.Nfo = u""
		#releaseInfo.SourceTorrentInfoHash = ""
		#releaseInfo.ReleaseUploadPath = "" # Empty if using the default path. See GetReleaseUploadPath.
		
		# TODO: error if no ptp and imdb id presents
		
		Database.DbSession.add( releaseInfo )
		Database.DbSession.commit()
		
		MyGlobals.PtpUploader.AddToDatabaseQueue( releaseInfo.Id )
	
	return render_template('index.html')