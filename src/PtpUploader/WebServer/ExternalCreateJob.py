from WebServer import app

from Helper import GetSuggestedReleaseNameAndSizeFromTorrentFile
from MyGlobals import MyGlobals
from Database import Database
from NfoParser import NfoParser
from PtpUploaderMessage import *
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import jsonify, make_response, request
from werkzeug import secure_filename

import os
import uuid

@app.route( "/ajaxexternalcreatejob/", methods = [ "POST" ] )
def ajaxExternalCreateJob():
	if ( "Password" not in request.values ) or request.values[ "Password" ] != Settings.GreasemonkeySendToScriptPassword:
		response = make_response( jsonify( result = "Error", message = "Invalid Greasemonkey Send to Script password!" ) )
		response.headers[ 'Access-Control-Allow-Origin' ] = '*' # Enable cross-origin resource sharing.
		return response

	file = request.files.get( "Torrent" )
	# file is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.) 
	if not file:
		response = make_response( jsonify( result = "Error", message = "Got no torrent file!" ) )
		response.headers[ 'Access-Control-Allow-Origin' ] = '*' # Enable cross-origin resource sharing.
		return response

	filename = "external job." + str( uuid.uuid1() ) + ".torrent"
	sourceTorrentFilePath = os.path.join( Settings.GetTemporaryPath(), filename )
	file.save( sourceTorrentFilePath )

	releaseName, torrentContentSize = GetSuggestedReleaseNameAndSizeFromTorrentFile( sourceTorrentFilePath )

	releaseInfo = ReleaseInfo()
	releaseInfo.SourceTorrentFilePath = sourceTorrentFilePath
	releaseInfo.AnnouncementSourceName = "torrent"
	releaseInfo.ReleaseName = releaseName
	releaseInfo.Size = torrentContentSize

	if "StopBeforeUploading" in request.values and request.values[ "StopBeforeUploading" ] == "1":
		releaseInfo.SetStopBeforeUploading( True )

	imdbId = ""
	if "ImdbUrl" in request.values:
		imdbId = NfoParser.GetImdbId( request.values[ "ImdbUrl" ] )
		if len( imdbId ) > 0:
			releaseInfo.ImdbId = imdbId

	Database.DbSession.add( releaseInfo )
	Database.DbSession.commit()

	MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageStartJob( releaseInfo.Id ) )

	response = make_response( jsonify( result = "OK" ) )
	response.headers[ 'Access-Control-Allow-Origin' ] = '*' # Enable cross-origin resource sharing.
	return response