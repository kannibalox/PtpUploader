import datetime

from django.utils import timezone
from django.core.serializers import serialize
from flask import render_template, url_for, jsonify

from PtpUploader.Helper import SizeToText, TimeDifferenceToText
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderMessage import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth


def GetStateIcon(state):
    if state == JobRunningState.Finished:
        return "success.png"
    elif state == JobRunningState.Failed:
        return "error.png"
    elif (
        state == JobRunningState.Ignored
        or state == JobRunningState.Ignored_AlreadyExists
        or state == JobRunningState.Ignored_Forbidden
        or state == JobRunningState.Ignored_MissingInfo
        or state == JobRunningState.Ignored_NotSupported
    ):
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
    entry["Id"] = releaseInfo.Id
    entry["ReleaseName"] = releaseInfo.ReleaseName

    stateMessage = JobRunningState.ToText(releaseInfo.JobRunningState)
    if releaseInfo.JobRunningState == JobRunningState.Scheduled:
        differenceText = TimeDifferenceToText(
            releaseInfo.ScheduleTimeUtc - datetime.datetime.utcnow(), 2, " to go", ""
        )
        if len(differenceText) > 0:
            stateMessage += " (%s)" % differenceText

    entry["State"] = stateMessage + ". (Click to see the log.)"

    entry["StateIcon"] = url_for(
        "static", filename=GetStateIcon(releaseInfo.JobRunningState)
    )

    if len(releaseInfo.ErrorMessage) > 0:
        entry["ErrorMessage"] = releaseInfo.ErrorMessage

    if releaseInfo.PtpId:
        if releaseInfo.HasPtpTorrentId():
            entry[
                "PtpUrl"
            ] = "https://passthepopcorn.me/torrents.php?id=%s&torrentid=%s" % (
                releaseInfo.PtpId,
                releaseInfo.GetPtpTorrentId(),
            )
        else:
            entry["PtpUrl"] = (
                "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.PtpId
            )
    elif releaseInfo.ImdbId and releaseInfo.ImdbId != "0":
        entry["PtpUrl"] = (
            "https://passthepopcorn.me/torrents.php?imdb=%s" % releaseInfo.ImdbId
        )

    entry["LogPageUrl"] = url_for("log", jobId=releaseInfo.Id)
    entry["Size"] = SizeToText(releaseInfo.Size)
    entry["Date"] = TimeDifferenceToText(
        timezone.now() - releaseInfo.LastModificationTime,
        2,
    )

    if releaseInfo.CanEdited():
        entry["EditJobUrl"] = url_for("EditJob", jobId=releaseInfo.Id)
    if releaseInfo.CanStopped():
        entry["StopJobUrl"] = url_for("StopJob", jobId=releaseInfo.Id)
    if releaseInfo.CanResumed():
        entry["StartJobUrl"] = url_for("StartJob", jobId=releaseInfo.Id)
    if releaseInfo.CanDeleted():
        entry["CanDeleteJob"] = True

    source = MyGlobals.SourceFactory.GetSource(releaseInfo.AnnouncementSourceName)
    if source is not None:
        filename = "source_icon/%s.ico" % releaseInfo.AnnouncementSourceName
        entry["SourceIcon"] = url_for("static", filename=filename)
        entry["SourceUrl"] = source.GetUrlFromId(releaseInfo.AnnouncementId)


@app.route("/jobs/", defaults={"page": 1})
@app.route("/jobs/page/<int:page>/")
@requires_auth
def jobs(page):

    entries = []
    for releaseInfo in list(ReleaseInfo.objects.all().order_by("LastModificationTime")):
        entry = {}
        ReleaseInfoToJobsPageData(releaseInfo, entry)
        entries.append(entry)

    settings = {}
    if Settings.OpenJobPageLinksInNewTab == "0":
        settings["OpenJobPageLinksInNewTab"] = ""
    else:
        settings["OpenJobPageLinksInNewTab"] = ' target="_blank"'

    return render_template("jobs.html", entries=entries, settings=settings)


@app.route("/ajax/jobs")
def jobs_json():
    return serialize(
        "json",
        ReleaseInfo.objects.all().order_by("LastModificationTime"),
        fields=("Id", "Source", "Size", "AnnouncementSourceName"),
    )


@app.route("/job/<int:jobId>/start/")
@requires_auth
def StartJob(jobId):
    # TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
    # Probably only the WorkerThread should change the running state.
    releaseInfo = ReleaseInfo.objects.get(Id=jobId)
    if not releaseInfo.CanResumed():
        return "The job is already running!"

    releaseInfo.JobRunningState = JobRunningState.WaitingForStart

    # Make sure that job is no longer handled as an automatically started job.
    # Manual forced jobs will resumed as manual forced.
    if releaseInfo.JobStartMode == JobStartMode.Automatic:
        releaseInfo.JobStartMode = JobStartMode.Manual

    # Resume the job normally.
    releaseInfo.SetStopBeforeUploading(False)

    releaseInfo.save()
    MyGlobals.PtpUploader.AddMessage(PtpUploaderMessageStartJob(jobId))
    return "OK"


@app.route("/job/<int:jobId>/stop/")
@requires_auth
def StopJob(jobId):
    # TODO: This is very far from perfect. There is no guarantee that the job didn't stop meanwhile.
    # Probably only the WorkerThread should change the running state.
    releaseInfo = ReleaseInfo.objects.get(Id=jobId)
    if not releaseInfo.CanStopped():
        return "The job is already stopped!"

    MyGlobals.PtpUploader.AddMessage(PtpUploaderMessageStopJob(jobId))
    return "OK"
