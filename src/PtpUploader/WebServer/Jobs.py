from Job.JobRunningState import JobRunningState
from Job.JobStartMode import JobStartMode
from WebServer import app
from WebServer.Authentication import requires_auth
from WebServer.Pagination import Pagination

from Database import Database
from Helper import SizeToText, TimeDifferenceToText
from MyGlobals import MyGlobals
from PtpUploaderMessage import *
from ReleaseInfo import ReleaseInfo
from Settings import Settings

from flask import render_template, request, url_for
from sqlalchemy import asc, desc
from sqlalchemy.sql import and_, or_

import datetime

def GetStateIcon(state):
	if state == JobRunningState.Finished:
		return "success.png"
	elif state == JobRunningState.Failed:
		return "error.png"
	elif state == JobRunningState.Ignored or state == JobRunningState.Ignored_AlreadyExists or state == JobRunningState.Ignored_Forbidden or state == JobRunningState.Ignored_MissingInfo or state == JobRunningState.Ignored_NotSupported:
		return "warning.png"
	elif state == JobRunningState.WaitingForStart:
		return "hourglass.png"
	elif state == JobRunningState.InProgress:
		return "throbber.gif"
	elif state == JobRunningState.Paused:
		return "pause.png"
	elif state == JobRunningState.Scheduled:
		return "scheduled.png"
	elif state == JobRunningState.DownloadedAlreadyExists:
		return "sad.png"

	# This is not possible.
	return "error.png"

def ReleaseInfoToJobsPageData(releaseInfo, entry):
	entry[ "Id" ] = releaseInfo.Id
	entry[ "ReleaseName" ] = releaseInfo.ReleaseName

	stateMessage = JobRunningState.ToText( releaseInfo.JobRunningState )
	if releaseInfo.JobRunningState == JobRunningState.Scheduled:
		differenceText = TimeDifferenceToText( releaseInfo.ScheduleTimeUtc - datetime.datetime.utcnow(), 2, " to go", "" )
		if len( differenceText ) > 0:
			stateMessage += " (%s)" % differenceText

	entry[ "State" ] = stateMessage + ". (Click to see the log.)"

	entry[ "StateIcon" ] = url_for( "static", filename = GetStateIcon( releaseInfo.JobRunningState ) )
	
	if len( releaseInfo.ErrorMessage ) > 0:
		entry[ "ErrorMessage" ] = releaseInfo.ErrorMessage

	if releaseInfo.HasPtpId():
		if releaseInfo.HasPtpTorrentId():
			entry[ "PtpUrl" ] = "https://passthepopcorn.me/torrents.php?id=%s&torrentid=%s" % ( releaseInfo.GetPtpId(), releaseInfo.GetPtpTorrentId() )
		else:
			entry[ "PtpUrl" ] = "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.GetPtpId()
	elif releaseInfo.HasImdbId() and ( not releaseInfo.IsZeroImdbId() ):
		entry[ "PtpUrl" ] = "https://passthepopcorn.me/torrents.php?imdb=%s" % releaseInfo.GetImdbId()

	entry[ "LogPageUrl" ] = url_for( "log", jobId = releaseInfo.Id )
	entry[ "Size" ] = SizeToText( releaseInfo.Size )
	entry[ "Date" ] = TimeDifferenceToText( datetime.datetime.utcnow() - Database.TimeStampToUtcDateTime( releaseInfo.LastModificationTime ), 2 )

	if releaseInfo.CanEdited():
		entry[ "EditJobUrl" ] = url_for( "EditJob", jobId = releaseInfo.Id )
	if releaseInfo.CanStopped():
		entry[ "StopJobUrl" ] = url_for( "StopJob", jobId = releaseInfo.Id )
	if releaseInfo.CanResumed():
		entry[ "StartJobUrl" ] = url_for( "StartJob", jobId = releaseInfo.Id )
	if releaseInfo.CanDeleted():
		entry[ "CanDeleteJob" ] = True

	source = MyGlobals.SourceFactory.GetSource( releaseInfo.AnnouncementSourceName )
	if source is not None:
		filename = "source_icon/%s.ico" % releaseInfo.AnnouncementSourceName
		entry[ "SourceIcon" ] = url_for( "static", filename = filename )
		entry[ "SourceUrl" ] = source.GetUrlFromId( releaseInfo.AnnouncementId )

@app.route( "/jobs/", defaults = { "page": 1 } )
@app.route( "/jobs/page/<int:page>/" )
@requires_auth
def jobs(page):
	jobsPerPage = 50

	if page < 1:
		page = 1

	offset = ( page - 1 ) * jobsPerPage
	query = Database.DbSession.query( ReleaseInfo )

	# Search text
	searchText = request.args.get( "searchstr", "" )
	if len( searchText ) > 0:
		# We replace the periods and the hyphen because of the relase names.
		searchWords = searchText.replace( ".", " " ).replace( "-", " " ).split( " " )
		for searchWord in searchWords:
			searchWord = searchWord.strip()
			if len( searchWord ) > 0:
				# "_", "%" and "\" have be escaped because the contains function uses SQL LIKE
				searchWord.replace( "\\", "\\\\" )
				searchWord.replace( "%", "\\%" )
				searchWord.replace( "_", "\\_" )
				query = query.filter( ReleaseInfo.ReleaseName.contains( searchWord ) )

	# Search states
	states = request.args.getlist( "state[]" )
	if ( states and len( states ) > 0 ):
		stateQuery = or_()
		for state in states:
			stateQuery.append( or_( ReleaseInfo.JobRunningState == state ) )

		query = query.filter( stateQuery )

	totalJobs =  query.count()

	# Ordering

	orderWay = request.args.get( "orderway" )
	orderWayFunction = asc
	if orderWay != 'asc':
		orderWayFunction = desc
		orderWay = ''

	orderBy = request.args.get( "orderby" )
	if orderBy == 'size':
		query = query.order_by( orderWayFunction( ReleaseInfo.Size ) )
	else:
		query = query.order_by( orderWayFunction( ReleaseInfo.LastModificationTime ) )
		orderBy = ''

	query = query.limit( jobsPerPage ).offset( offset )

	pagination = Pagination( page, jobsPerPage, totalJobs )
	
	entries = []
	for releaseInfo in query:
		entry = {}
		ReleaseInfoToJobsPageData( releaseInfo, entry )
		entries.append( entry )

	settings = { "SearchText": searchText, "OrderBy": orderBy, "OrderWay": orderWay, "States": states }
	if Settings.OpenJobPageLinksInNewTab == "0":
		settings[ "OpenJobPageLinksInNewTab" ] = ""
	else:
		settings[ "OpenJobPageLinksInNewTab" ] = ' target="_blank"'

	return render_template( "jobs.html", entries = entries, pagination = pagination, settings = settings )

@app.route( "/job/<int:jobId>/start/" )
@requires_auth
def StartJob(jobId):
	# TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
	# Probably only the WorkerThread should change the running state.		
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	if not releaseInfo.CanResumed():
		return "The job is already running!"

	releaseInfo.JobRunningState = JobRunningState.WaitingForStart
	
	# Make sure that job is no longer handled as an automatically started job.
	# Manual forced jobs will resumed as manual forced.
	if releaseInfo.JobStartMode == JobStartMode.Automatic:
		releaseInfo.JobStartMode = JobStartMode.Manual

	# Resume the job normally.
	releaseInfo.SetStopBeforeUploading( False )
	
	Database.DbSession.commit()
	MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageStartJob( jobId ) )
	return "OK"

@app.route( "/job/<int:jobId>/stop/" )
@requires_auth
def StopJob(jobId):
	# TODO: This is very far from perfect. There is no guarantee that the job didn't stop meanwhile.
	# Probably only the WorkerThread should change the running state.		
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	if not releaseInfo.CanStopped():
		return "The job is already stopped!"
	
	MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageStopJob( jobId ) )
	return "OK"
