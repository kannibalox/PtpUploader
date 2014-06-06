from WebServer import app

from Authentication import requires_auth
from MyGlobals import MyGlobals
from Database import Database
from Logger import Logger
from ReleaseInfo import ReleaseInfo

from flask import render_template, redirect, request, url_for

import os

@app.route( '/job/<int:jobId>/delete/' )
@requires_auth
def DeleteTheJob(jobId):
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()

	# TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
	# Probably the WorkerThred should do the deleting.
	if not releaseInfo.CanDeleted():
		return "The job is currently running and can't be deleted!"

	deleteMode = request.args[ "mode" ].upper()
	deleteSourceData = deleteMode == 'DELETEJOBANDSOURCEDATA' or deleteMode == 'DELETEJOBANDALLDATA'
	deleteUploadData = deleteMode == 'DELETEJOBANDUPLOADDATA' or deleteMode == 'DELETEJOBANDALLDATA'

	announcementSource = releaseInfo.AnnouncementSource
	if announcementSource is None:
		announcementSource = MyGlobals.SourceFactory.GetSource( releaseInfo.AnnouncementSourceName )

	if releaseInfo.Logger is None:
		releaseInfo.Logger = Logger( releaseInfo.GetLogFilePath() )

	announcementSource.Delete( releaseInfo, MyGlobals.GetTorrentClient(), deleteSourceData, deleteUploadData )

	Database.DbSession.delete( releaseInfo )
	Database.DbSession.commit()

	return "OK"