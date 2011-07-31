from Tool.PyrocoreBencode import bencode
from WebServer import app
from WebServer.JobCommon import JobCommon
from WebServer.UploadFile import UploadFile

from Authentication import requires_auth
from Helper import SizeToText
from MyGlobals import MyGlobals
from Database import Database
from PtpUploaderMessage import *
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import jsonify, render_template, request
from werkzeug import secure_filename

import os
import re
import uuid

def IsFileAllowed(filename):
	root, extension = os.path.splitext( filename )
	return extension == ".torrent"

def GetSuggestedReleaseNameAndSizeFromTorrent(torrentPath):
	data = bencode.bread( torrentPath )
	name = data[ "info" ].get( "name", None )
	files = data[ "info" ].get( "files", None )
	if files is None:
		# It is a single file torrent, remove the extension.
		name, extension = os.path.splitext( name )
		size = data[ "info" ][ "length" ]
		return name, size
	else:
		size = 0
		for file in files:
			size += file[ "length" ]
		
		return name, size

@app.route( "/ajaxuploadtorrentfile/", methods = [ "POST" ] )
@requires_auth
def ajaxUploadTorrentFile():
	file = request.files.get( "file_input" )
	# file is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.) 
	if ( not file ) or ( not IsFileAllowed( file.filename ) ):
		return jsonify( result = "ERROR" )
		
	filename = secure_filename( file.filename )
	
	# We add an UUID to the filename to make sure it is unique in the temporary folder.
	filename, extension = os.path.splitext( filename )
	filename += "." + str( uuid.uuid1() ) + extension

	sourceTorrentFilePath = os.path.join( Settings.GetTemporaryPath(), filename )
	file.save( sourceTorrentFilePath )
	
	releaseName, size = GetSuggestedReleaseNameAndSizeFromTorrent( sourceTorrentFilePath )
	sizeText = SizeToText( size )

	return jsonify( result = "OK", torrentFilename = filename, releaseName = releaseName, torrentContentSize = size, torrentContentSizeText = sizeText )

def UploadTorrentFile(releaseInfo, request):
	torrentFilename = request.values[ "uploaded_torrentfilename" ]
	if not IsFileAllowed( torrentFilename ):
		return False

	torrentContentSize = request.values[ "uploaded_torrentcontentsize" ]
	if len( torrentContentSize ) <= 0: # Length of the string.
		return False
		
	torrentFilename = secure_filename( torrentFilename )
	torrentFilename = os.path.join( Settings.GetTemporaryPath(), torrentFilename )
	if not os.path.isfile( torrentFilename ):
		return False
	
	releaseInfo.SourceTorrentFilePath = torrentFilename
	releaseInfo.AnnouncementSourceName = "torrent"
	releaseInfo.Size = int( torrentContentSize )
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

		releaseInfo.ReleaseName = request.values[ "release_name" ]

		JobCommon.FillReleaseInfoFromRequestData( releaseInfo, request )
		
		# TODO: todo multiline torrent site link field
		
		Database.DbSession.add( releaseInfo )
		Database.DbSession.commit()
		
		MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageStartJob( releaseInfo.Id ) )
	
	# job parameter is needed because it uses the same template as edit job
	job = {}
	job[ "Subtitles" ] = [] 
	return render_template( "upload.html", job = job )