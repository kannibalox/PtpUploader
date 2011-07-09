from Job.JobRunningState import JobRunningState
from Job.JobStartMode import JobStartMode
from WebServer import app
from WebServer.JobCommon import JobCommon

from Authentication import requires_auth
from MyGlobals import MyGlobals
from Database import Database
from PtpUploaderMessage import *
from ReleaseInfo import ReleaseInfo

from flask import render_template, redirect, request, url_for

@app.route( "/job/<int:jobId>/edit/", methods = [ "GET", "POST" ] )
@requires_auth
def EditJob(jobId):
	if request.method == 'POST':
		releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()

		# TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
		# Probably only the WorkerThred should change the running state.  		
		if not releaseInfo.CanEdited():
			return "The job is currently running and can't be edited!"

		JobCommon.FillReleaseInfoFromRequestData( releaseInfo, request )
		releaseInfo.JobRunningState = JobRunningState.WaitingForStart
		Database.DbSession.commit()
		MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageStartJob( releaseInfo.Id ) )

		return redirect( url_for( "jobs" ) )

	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	job = {}
	JobCommon.FillDictionaryFromReleaseInfo( job, releaseInfo )

	if releaseInfo.CanEdited():
		job[ "CanBeEdited" ] = True

	return render_template( "edit_job.html", job = job )