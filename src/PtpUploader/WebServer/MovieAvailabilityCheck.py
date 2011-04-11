from WebServer import app

from Authentication import requires_auth
from MyGlobals import MyGlobals
from Ptp import Ptp
from ReleaseInfo import ReleaseInfo

from flask import render_template, request

import re

@app.route( "/movieAvailabilityCheck/", methods = [ "GET", "POST" ] )
@requires_auth
def movieAvailabilityCheck():
	if request.method == 'POST':
		Ptp.Login()

		releaseInfo = ReleaseInfo()

		format = request.values[ "format" ]
		if format == "SD XviD":
			releaseInfo.Quality = "Standard Definition"
			releaseInfo.Codec = "XviD"
			releaseInfo.Container = "AVI"
			releaseInfo.ResolutionType = "Other"
			releaseInfo.Source = "DVD"
		elif format == "SD x264":
			releaseInfo.Quality = "Standard Definition"
			releaseInfo.Codec = "x264"
			releaseInfo.Container = "MKV"
			releaseInfo.ResolutionType = "Other"
			releaseInfo.Source = "DVD"
		elif format == "720p":
			releaseInfo.Quality = "High Definition"
			releaseInfo.Codec = "x264"
			releaseInfo.Container = "MKV"
			releaseInfo.ResolutionType = "720p"
			releaseInfo.Source = "Blu-ray"
		elif format == "1080p":
			releaseInfo.Quality = "High Definition"
			releaseInfo.Codec = "x264"
			releaseInfo.Container = "MKV"
			releaseInfo.ResolutionType = "1080p"
			releaseInfo.Source = "Blu-ray"
		else:
			return "Unknown format!"

		imdbIds = request.values[ "imdb" ]
		
		resultHtml = ""

		matches = re.findall( r"imdb.com/title/tt(\d+)", imdbIds )
		for match in matches:
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( MyGlobals.Logger, match )
			existingRelease = movieOnPtpResult.IsReleaseExists( releaseInfo )
			if existingRelease is None: 
				resultHtml += """<a href="http://www.imdb.com/title/tt%s">%s</a> - NOT ON PTP</br>""" % ( match, match )
			else:
				resultHtml += """<a href="http://www.imdb.com/title/tt%s">%s</a> - <a href="https://passthepopcorn.me/torrents.php?id=%s">PTP</a></br>""" % ( match, match, movieOnPtpResult.PtpId )
			
		return resultHtml

	return render_template( "movieAvailabilityCheck.html" )