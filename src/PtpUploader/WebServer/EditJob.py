from Job.JobStartMode import JobStartMode
from WebServer import app

from Authentication import requires_auth
from MyGlobals import MyGlobals
from Database import Database
from Ptp import Ptp
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import Module, render_template, request

def GetPtpOrImdbLink(releaseInfo):
	if releaseInfo.HasPtpId():
		return "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.PtpId
	elif releaseInfo.HasImdbId():
		if releaseInfo.IsZeroImdbId():
			return "0"
		else:
			return "http://www.imdb.com/title/tt%s/" % releaseInfo.ImdbId
	
	return ""

def GetYouTubeLink(releaseInfo):
	if len( releaseInfo.YouTubeId ) > 0:
		return "http://www.youtube.com/watch?v=%s" % releaseInfo.YouTubeId

	return ""

@app.route( '/job/<int:jobId>/', methods=[ 'GET', 'POST' ] )
@requires_auth
def EditJob(jobId):
	if request.method == 'POST':
		# TODO: copy values from the form
		releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
		MyGlobals.PtpUploader.AddToDatabaseQueue( releaseInfo.Id )
		return "OK"
	
	
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	job = {}
	
	# For PTP
	job[ "type" ] = releaseInfo.Type
	job[ "imdb" ] = GetPtpOrImdbLink( releaseInfo )
	job[ "artists[]" ] = releaseInfo.Directors
	job[ "title" ] = releaseInfo.Title
	job[ "year" ] = releaseInfo.Year
	job[ "tags" ] = releaseInfo.Tags
	job[ "album_desc" ] = releaseInfo.MovieDescription
	job[ "image" ] = releaseInfo.CoverArtUrl
	job[ "trailer" ] = GetYouTubeLink( releaseInfo )
	job[ "metacritic" ] = releaseInfo.MetacriticUrl
	job[ "tomatoes" ] = releaseInfo.RottenTomatoesUrl
	
	if releaseInfo.IsSceneRelease():
		job[ "scene" ] = "on"
	
	job[ "quality" ] = releaseInfo.Quality 
	job[ "codec" ] = releaseInfo.Codec
	job[ "other_codec" ] = releaseInfo.CodecOther
	job[ "container" ] = releaseInfo.Container
	job[ "other_container" ] = releaseInfo.ContainerOther
	job[ "resolution" ] = releaseInfo.ResolutionType 
	job[ "other_resolution" ] = releaseInfo.Resolution 
	job[ "source" ] = releaseInfo.Source
	job[ "other_source" ] = releaseInfo.SourceOther
	job[ "remaster_title" ] = releaseInfo.RemasterTitle
	job[ "remaster_year" ] = releaseInfo.RemasterYear
	
	# Other
	
	if releaseInfo.JobStartMode == JobStartMode.ManualForced:
		job[ "force_upload" ] = "on"

	if releaseInfo.ForceDirectorylessSingleFileTorrent:
		 job[ "ForceDirectorylessSingleFileTorrent" ] = "on"

	job[ "ReleaseNotes" ] = releaseInfo.ReleaseNotes
		
	return render_template( "edit_job.html", job = job )