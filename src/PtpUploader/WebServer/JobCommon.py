from Helper import ParseQueryString
from Job.JobStartMode import JobStartMode
from NfoParser import NfoParser

import urlparse

class JobCommon:
	# Needed because urlparse return with empty netloc if protocol is not set.
	@staticmethod 
	def __AddHttpToUrl(url):
		if url.startswith( "http://" ) or url.startswith( "https://" ):
			return url
		else:
			return "http://" + url
	
	@staticmethod
	def __GetYouTubeId(text):
		url = urlparse.urlparse( JobCommon.__AddHttpToUrl( text ) )
		if url.netloc == "youtube.com" or url.netloc == "www.youtube.com":
			params = ParseQueryString( url.query )
			youTubeIdList = params.get( "v" )
			if youTubeIdList is not None:
				return youTubeIdList[ 0 ]
	
		return ""
	
	@staticmethod
	def __GetPtpOrImdbId(releaseInfo, text):
		imdbId = NfoParser.GetImdbId( text )
		if len( imdbId ) > 0:
			releaseInfo.ImdbId = imdbId
		elif text == "0" or text == "-":
			releaseInfo.SetZeroImdbId()
		else:
			# Using urlparse because of torrent permalinks:
			# https://passthepopcorn.me/torrents.php?id=9730&torrentid=72322
			url = urlparse.urlparse( JobCommon.__AddHttpToUrl( text ) )
			if url.netloc == "passthepopcorn.me" or url.netloc == "www.passthepopcorn.me":
				params = ParseQueryString( url.query )
				ptpIdList = params.get( "id" )
				if ptpIdList is not None:
					releaseInfo.PtpId = ptpIdList[ 0 ]
	
	@staticmethod
	def FillReleaseInfoFromRequestData(releaseInfo, request):
		# For PTP
		
		releaseInfo.Type = request.values[ "type" ]
		JobCommon.__GetPtpOrImdbId( releaseInfo, request.values[ "imdb" ] )
		releaseInfo.Directors = request.values[ "artists[]" ]
		releaseInfo.Title = request.values[ "title" ]
		releaseInfo.Year = request.values[ "year" ]
		releaseInfo.Tags = request.values[ "tags" ]
		releaseInfo.MovieDescription = request.values[ "album_desc" ]
		releaseInfo.CoverArtUrl = request.values[ "image" ]
		releaseInfo.YouTubeId = JobCommon.__GetYouTubeId( request.values[ "trailer" ] )
		releaseInfo.MetacriticUrl = request.values[ "metacritic" ]
		releaseInfo.RottenTomatoesUrl = request.values[ "tomatoes" ]
		
		if request.values.get( "scene" ) is not None:
			releaseInfo.SetSceneRelease()
		
		if request.values.get( "special" ) is not None:
			releaseInfo.SetSpecialRelease()
	
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
		
		releaseInfo.RemasterTitle = request.values[ "remaster_title" ]
		releaseInfo.RemasterYear = request.values[ "remaster_year" ]
		
		# Other
		
		if request.values.get( "force_upload" ) is None:
			releaseInfo.JobStartMode = JobStartMode.Manual
		else:
			releaseInfo.JobStartMode = JobStartMode.ManualForced
	
		if request.values.get( "ForceDirectorylessSingleFileTorrent" ) is not None:
			releaseInfo.SetForceDirectorylessSingleFileTorrent()

		if request.values.get( "StartImmediately" ) is not None:
			releaseInfo.SetStartImmediately()
	
		releaseInfo.ReleaseNotes = request.values[ "ReleaseNotes" ]

	@staticmethod
	def __GetPtpOrImdbLink(releaseInfo):
		if releaseInfo.HasPtpId():
			return "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.PtpId
		elif releaseInfo.HasImdbId():
			if releaseInfo.IsZeroImdbId():
				return "0"
			else:
				return "http://www.imdb.com/title/tt%s/" % releaseInfo.ImdbId
		
		return ""
	
	@staticmethod
	def __GetYouTubeLink(releaseInfo):
		if len( releaseInfo.YouTubeId ) > 0:
			return "http://www.youtube.com/watch?v=%s" % releaseInfo.YouTubeId
	
		return ""

	@staticmethod
	def FillDictionaryFromReleaseInfo(job, releaseInfo):
		# For PTP
		job[ "type" ] = releaseInfo.Type
		job[ "imdb" ] = JobCommon.__GetPtpOrImdbLink( releaseInfo )
		job[ "artists[]" ] = releaseInfo.Directors
		job[ "title" ] = releaseInfo.Title
		job[ "year" ] = releaseInfo.Year
		job[ "tags" ] = releaseInfo.Tags
		job[ "album_desc" ] = releaseInfo.MovieDescription
		job[ "image" ] = releaseInfo.CoverArtUrl
		job[ "trailer" ] = JobCommon.__GetYouTubeLink( releaseInfo )
		job[ "metacritic" ] = releaseInfo.MetacriticUrl
		job[ "tomatoes" ] = releaseInfo.RottenTomatoesUrl
		
		if releaseInfo.IsSceneRelease():
			job[ "scene" ] = "on"
		
		if releaseInfo.IsSpecialRelease():
			job[ "special" ] = "on"
		
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
	
		if releaseInfo.IsForceDirectorylessSingleFileTorrent():
			 job[ "ForceDirectorylessSingleFileTorrent" ] = "on"

		if releaseInfo.IsStartImmediately():
			 job[ "StartImmediately" ] = "on"
	
		job[ "ReleaseNotes" ] = releaseInfo.ReleaseNotes