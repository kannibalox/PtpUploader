'''

jQuery File Tree
http://abeautifulsite.net/blog/2008/03/jquery-file-tree/

jQuery File Upload
https://github.com/blueimp/jQuery-File-Upload/

'''

from Job.JobStartMode import JobStartMode
from Job.JobRunningState import JobRunningState
from WebServer import app

from Authentication import requires_auth
from Database import Database
from MyGlobals import MyGlobals
from NfoParser import NfoParser
from Ptp import Ptp
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import jsonify, Module, render_template, request, redirect, url_for
from werkzeug import secure_filename

import os
import re
import urlparse

@app.route( '/' )
@requires_auth
def index():
	entries = []
	for releaseInfo in Database.DbSession.query( ReleaseInfo ):#.order_by( DbRelease.id ):
		entry = {}
		entry[ "Id" ] = releaseInfo.Id
		entry[ "ReleaseName" ] = releaseInfo.ReleaseName
		entry[ "State" ] = JobRunningState.ToText( releaseInfo.JobRunningState )
		
		if len( releaseInfo.ErrorMessage ) > 0:
			entry[ "ErrorMessage" ] = releaseInfo.ErrorMessage

		if releaseInfo.HasPtpId():
			entry[ "PtpUrl" ] = "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.GetPtpId()
		elif releaseInfo.HasImdbId() and ( not releaseInfo.IsZeroImdbId() ):
			entry[ "PtpUrl" ] = "http://passthepopcorn.me/torrents.php?imdb=%s" % releaseInfo.GetImdbId()

		entry[ "LogPageUrl" ] = url_for( "log", jobId = releaseInfo.Id )
		entry[ "EditPageUrl" ] = url_for( "EditJob", jobId = releaseInfo.Id )
		
		entries.append( entry )

	return render_template( "jobs.html", entries = entries )

@app.route( '/job/<int:jobId>/log/' )
@requires_auth
def log(jobId):
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	
	logFilePath = releaseInfo.GetLogFilePath()
	log = ""
	
	if os.path.isfile( logFilePath ):
		file = open( logFilePath )
		log = file.read()
		file.close()
	else:
		log = "Log file '%s' doesn't exists!" % logFilePath

	log = log.replace( "\n", r"<br>" )

	return log

# TODO: make it more simple: preset for: SD, 720p, 1080p
@app.route( "/checkifexists/", methods=[ "GET", "POST" ] )
@requires_auth
def checkIfExists():
	if request.method == 'POST':
		Ptp.Login()
		
		releaseInfo = ReleaseInfo()		
		releaseInfo.Codec = request.values[ "codec" ]
		releaseInfo.Container = request.values[ "container" ]
		releaseInfo.ResolutionType = request.values[ "resolution" ]
		releaseInfo.Source = request.values[ "source" ]
		
		if releaseInfo.ResolutionType == "720p" or releaseInfo.ResolutionType == "1080p":
			releaseInfo.Quality = "High Definition"
		else:
			releaseInfo.Quality = "Standard Definition"
		
		imdbIds = request.values[ "imdb" ]
		
		resultHtml = ""

		matches = re.findall( r"imdb.com/title/tt(\d+)", imdbIds )
		for match in matches:
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( MyGlobals.Logger, match )
			existingRelease = movieOnPtpResult.IsReleaseExists( releaseInfo )
			if existingRelease is None: 
				resultHtml += """<a href="http://www.imdb.com/title/tt%s">%s</a> - NOT ON PTP</br>""" % ( match, match )
			else:
				resultHtml += """<a href="http://www.imdb.com/title/tt%s">%s</a> - <a href="http://passthepopcorn.me/torrents.php?id=%s">PTP</a></br>""" % ( match, match, movieOnPtpResult.PtpId )
			
		return resultHtml

	return render_template( "checkifexists.html" )

@app.route( "/quit" )
@requires_auth
def quit():
	MyGlobals.PtpUploader.RequestStop()
	return "Quitting."