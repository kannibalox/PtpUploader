import os

from flask import redirect, render_template, request, url_for

from PtpUploader.Database import Database
from PtpUploader.Logger import Logger
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth


@app.route("/job/<int:jobId>/delete/")
@requires_auth
def DeleteTheJob(jobId):
    releaseInfo = (
        Database.DbSession.query(ReleaseInfo).filter(ReleaseInfo.Id == jobId).first()
    )

    # TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
    # Probably the WorkerThread should do the deleting.
    if not releaseInfo.CanDeleted():
        return "The job is currently running and can't be deleted!"

    deleteMode = request.args["mode"].upper()
    deleteSourceData = (
        deleteMode == "DELETEJOBANDSOURCEDATA" or deleteMode == "DELETEJOBANDALLDATA"
    )
    deleteUploadData = (
        deleteMode == "DELETEJOBANDUPLOADDATA" or deleteMode == "DELETEJOBANDALLDATA"
    )

    announcementSource = releaseInfo.AnnouncementSource
    if announcementSource is None:
        announcementSource = MyGlobals.SourceFactory.GetSource(
            releaseInfo.AnnouncementSourceName
        )

    if releaseInfo.Logger is None:
        releaseInfo.Logger = Logger(releaseInfo.GetLogFilePath())

    announcementSource.Delete(
        releaseInfo, MyGlobals.GetTorrentClient(), deleteSourceData, deleteUploadData
    )

    Database.DbSession.delete(releaseInfo)
    Database.DbSession.commit()

    return "OK"
