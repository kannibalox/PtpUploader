'''

jQuery File Tree
http://abeautifulsite.net/blog/2008/03/jquery-file-tree/

jQuery File Upload
https://github.com/blueimp/jQuery-File-Upload/

'''

from Job.JobStartMode import JobStartMode
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
	return "Hello World!"

@app.route( '/jobs/' )
@requires_auth
def jobs():
	text = ""
	for releaseInfo in Database.DbSession.query( ReleaseInfo ):#.order_by( DbRelease.id ):
		text += "Id: %s, Title: %s<br/>" % ( releaseInfo.Id, releaseInfo.ReleaseName )
		
	return text

@app.route( '/job/<int:jobId>/' )
@requires_auth
def job(jobId):
	text = ""
	
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	
	text += "Id: %s<br/>IMDb id: %s" % ( releaseInfo.Id, releaseInfo.ImdbId )
		
	return text

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