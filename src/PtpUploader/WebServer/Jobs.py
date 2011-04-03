from Job.JobRunningState import JobRunningState
from WebServer import app
from WebServer.Authentication import requires_auth
from WebServer.Pagination import Pagination

from Database import Database
from MyGlobals import MyGlobals
from ReleaseInfo import ReleaseInfo

from flask import render_template, request, url_for
from sqlalchemy import desc

def GetStateIcon(state):
	if state == JobRunningState.Finished: 
		return "success.png"
	elif state == JobRunningState.Failed: 
		return "error.png"
	elif state == JobRunningState.Ignored or state == JobRunningState.Ignored_AlreadyExists or state == JobRunningState.Ignored_Forbidden or state == JobRunningState.Ignored_MissingInfo or state == JobRunningState.Ignored_NotSupported:
		return "warning.png"

	return ""

def ReleaseInfoToJobsPageData(releaseInfo, entry):
	entry[ "Id" ] = releaseInfo.Id
	entry[ "ReleaseName" ] = releaseInfo.ReleaseName
	entry[ "State" ] = JobRunningState.ToText( releaseInfo.JobRunningState )
	
	stateIcon = GetStateIcon( releaseInfo.JobRunningState )
	if len( stateIcon ) > 0: 
		entry[ "StateIcon" ] = url_for( "static", filename = stateIcon )
	
	if len( releaseInfo.ErrorMessage ) > 0:
		entry[ "ErrorMessage" ] = releaseInfo.ErrorMessage

	if releaseInfo.HasPtpId():
		entry[ "PtpUrl" ] = "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.GetPtpId()
	elif releaseInfo.HasImdbId() and ( not releaseInfo.IsZeroImdbId() ):
		entry[ "PtpUrl" ] = "http://passthepopcorn.me/torrents.php?imdb=%s" % releaseInfo.GetImdbId()

	entry[ "LogPageUrl" ] = url_for( "log", jobId = releaseInfo.Id )

	if releaseInfo.CanEdited():
		entry[ "EditPageUrl" ] = url_for( "EditJob", jobId = releaseInfo.Id )

	source = MyGlobals.SourceFactory.GetSource( releaseInfo.AnnouncementSourceName )
	if source is not None:
		filename = "source_icon/%s.ico" % releaseInfo.AnnouncementSourceName
		entry[ "SourceIcon" ] = url_for( "static", filename = filename )
		entry[ "SourceUrl" ] = source.GetUrlFromId( releaseInfo.AnnouncementId )

@app.route( "/jobs/", defaults = { "page": 1 } )
@app.route( "/jobs/page/<int:page>" )
@requires_auth
def jobs(page):
	jobsPerPage = 50

	if page < 1:
		page = 1
	
	totalJobs =  Database.DbSession.query( ReleaseInfo ).count()
	offset = ( page - 1 ) * jobsPerPage
	query = Database.DbSession.query( ReleaseInfo ).order_by( desc( ReleaseInfo.LastModificationTime ) ).limit( jobsPerPage ).offset( offset )

	pagination = Pagination( page, jobsPerPage, totalJobs )
	
	entries = []
	for releaseInfo in query:
		entry = {}
		ReleaseInfoToJobsPageData( releaseInfo, entry )
		entries.append( entry )

	return render_template( "jobs.html", entries = entries, pagination = pagination )