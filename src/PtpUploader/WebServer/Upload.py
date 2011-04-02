from WebServer import app
from WebServer.JobCommon import JobCommon

from Authentication import requires_auth
from MyGlobals import MyGlobals
from Database import Database
from PtpUploaderMessage import *
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import render_template, request
from werkzeug import secure_filename

import os
import re

def IsFileAllowed(filename):
	root, extension = os.path.splitext( filename )
	return extension == ".torrent"

def UploadTorrentFile(releaseInfo, request):
	file = request.files.get( "file_input" )
	# file is is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.) 
	if ( not file ) or ( not IsFileAllowed( file.filename ) ):
		return False
		
	filename = secure_filename( file.filename )
	releaseInfo.SourceTorrentFilePath = os.path.join( Settings.GetTemporaryPath(), filename )
	file.save( releaseInfo.SourceTorrentFilePath )

	releaseInfo.AnnouncementSourceName = "torrent"
	releaseInfo.ReleaseName = file.filename.replace( ".torrent", "" ) # TODO
	return True 

def UploadTorrentSiteLink(releaseInfo, request):
	torrentPageLink = request.values[ "torrent_site_link" ]
	if len( torrentPageLink ) <= 0:
		return False
		
	source, id = MyGlobals.SourceFactory.GetSourceAndIdByUrl( torrentPageLink )
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
	#return False

	# TODO: support if path is a file
	if os.path.isdir( path ):
		releaseInfo.AnnouncementSourceName = "file"
		releaseInfo.ReleaseDownloadPath = path

		# Make sure that path doesn't ends with a trailing slash or else os.path.split would return with wrong values.
		path = path.rstrip( "\\/" )
	
		# Release name will be the directory's name. Eg. it will be "anything" for "/something/anything"
		basePath, releaseInfo.ReleaseName = os.path.split( path )
	
		return True
	else:
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

		JobCommon.FillReleaseInfoFromRequestData( releaseInfo, request )
		
		# TODO: todo multiline torrent site link field
		
		Database.DbSession.add( releaseInfo )
		Database.DbSession.commit()
		
		MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageStartJob( releaseInfo.Id ) )
	
	# job parameter is needed because it uses the same template as edit job 
	return render_template( "upload.html", job = {} )