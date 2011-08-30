from Job.JobStartMode import JobStartMode
from WebServer import app
from WebServer.Authentication import requires_auth

from Database import Database
from Helper import ParseQueryString
from IncludedFileList import IncludedFileList
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import jsonify, request
from werkzeug import secure_filename

import os
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
			if url.netloc == "passthepopcorn.me" or url.netloc == "www.passthepopcorn.me" or url.netloc == "tls.passthepopcorn.me":
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
		releaseInfo.SetSubtitles( request.form.getlist( "subtitle[]" ) )
		releaseInfo.IncludedFiles = request.values[ "IncludedFilesCustomizedList" ]

	@staticmethod
	def __GetPtpOrImdbLink(releaseInfo):
		if releaseInfo.HasPtpId():
			return "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.GetPtpId()
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
		job[ "JobId" ] = releaseInfo.Id
		
		if releaseInfo.JobStartMode == JobStartMode.ManualForced:
			job[ "force_upload" ] = "on"
	
		if releaseInfo.IsForceDirectorylessSingleFileTorrent():
			 job[ "ForceDirectorylessSingleFileTorrent" ] = "on"

		if releaseInfo.IsStartImmediately():
			 job[ "StartImmediately" ] = "on"
	
		job[ "ReleaseNotes" ] = releaseInfo.ReleaseNotes
		
		job[ "Subtitles" ] = releaseInfo.GetSubtitles()
		job[ "IncludedFilesCustomizedList" ] = releaseInfo.IncludedFiles

def MakeIncludedFilesTreeJson(includedFileList):
	class TreeFile:
		def __init__(self, name, includedFileItem):
			self.Name = name
			self.IncludedFileItem = includedFileItem
	
	class TreeDirectory:
		def __init__(self, name):
			self.Name = name
			self.Directories = [] # Contains TreeDirectory.
			self.Files = [] # Contains TreeFiles.
			
		# Adds directory if it not exists yet. Maintains sort order.
		def __AddDirectoryInternal(self, name):
			nameLower = name.lower()
			for i in range( len( self.Directories ) ):
				currentNameLower = self.Directories[ i ].Name.lower()
				if currentNameLower == nameLower:
					return self.Directories[ i ]
				elif currentNameLower > nameLower:
					newDirectory = TreeDirectory( name )
					self.Directories.insert( i, newDirectory )
					return newDirectory
						
			newDirectory = TreeDirectory( name )
			self.Directories.append( newDirectory )
			return newDirectory

		# Adds file. Maintains sort order.
		def __AddFileInternal(self, name, includedFileItem):
			nameLower = name.lower()
			for i in range( len( self.Files ) ):
				currentNameLower = self.Files[ i ].Name.lower()
				if currentNameLower > nameLower:
					self.Files.insert( i, TreeFile( name, includedFileItem ) )
					return
						
			self.Files.append( TreeFile( name, includedFileItem ) )

		def AddFile(self, includedFileItem):
			pathComponents = includedFileItem.Name.split( "/" )
			parent = self
			for i in range( len( pathComponents ) ):
				pathComponent = pathComponents[ i ]
				
				# Last component is the file.
				if i == ( len( pathComponents ) - 1 ):
					parent.__AddFileInternal( pathComponent, includedFileItem )
				else:
					parent = parent.__AddDirectoryInternal( pathComponent )
					
		def GetListForJson(self, parentList):
			for directory in self.Directories:
				entry = { "title": directory.Name, "isFolder": True }
				childList = []
				directory.GetListForJson( childList )
				if len( childList ) > 0:
					entry[ "children" ] = childList
				
				parentList.append( entry )

			for file in self.Files:
				# OriginallySelected and IncludePath are custom properties.
				# http://stackoverflow.com/questions/6012734/dynatree-where-can-i-store-additional-info-in-each-node
				entry = {}
				entry[ "title" ] = file.Name
				entry[ "select" ] = file.IncludedFileItem.IsIncluded()
				entry[ "OriginallySelected" ] = file.IncludedFileItem.IsDefaultIncluded()
				entry[ "IncludePath" ] = file.IncludedFileItem.Name
				parentList.append( entry )

	root = TreeDirectory( u"" )

	for entry in includedFileList.Files:
		root.AddFile( entry )
				
	list = []
	root.GetListForJson( list )
	return list

@app.route( "/ajaxgetincludedfilelist/", methods = [ "POST" ] )
@requires_auth
def ajaxGetIncludedFileList():
	includedFileList = IncludedFileList()
	jobId = request.values.get( "JobId" )
	sourceTorrentFilename = request.values.get( "SourceTorrentFilename" )
	releaseDownloadPath = request.values.get( "ReleaseDownloadPath" )
	includedFilesCustomizedList = request.values.get( "IncludedFilesCustomizedList" )
	
	if jobId:
		jobId = int( jobId )
		releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
		announcementSource = MyGlobals.SourceFactory.GetSource( releaseInfo.AnnouncementSourceName )
		if announcementSource:
			includedFileList = announcementSource.GetIncludedFileList( releaseInfo )
	elif sourceTorrentFilename:
		sourceTorrentFilename = secure_filename( sourceTorrentFilename )
		sourceTorrentFilename = os.path.join( Settings.GetTemporaryPath(), sourceTorrentFilename )
		includedFileList.FromTorrent( sourceTorrentFilename )
	elif releaseDownloadPath:
		includedFileList.FromDirectory( releaseDownloadPath )
	else:
		return jsonify( result = "ERROR" )

	includedFileList.ApplyCustomizationFromJson( includedFilesCustomizedList )

	return jsonify( result = "OK", files = MakeIncludedFilesTreeJson( includedFileList ) )