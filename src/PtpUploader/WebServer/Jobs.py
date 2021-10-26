import datetime

from django.utils import timezone
from django.core.serializers import serialize
from django.forms.models import model_to_dict
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


@app.route("/jobs/", defaults={"page": 1})
@app.route("/jobs/page/<int:page>/")
@requires_auth
def jobs(page):
    entries = []
    settings = {}
    return render_template("jobs.html", entries=entries, settings=settings)


@app.route("/ajax/jobs")
def jobs_json():
    settings = {}
    if Settings.OpenJobPageLinksInNewTab == "0":
        settings["OpenJobPageLinksInNewTab"] = ""
    else:
        settings["OpenJobPageLinksInNewTab"] = ' target="_blank"'

    entries = []
    for release in ReleaseInfo.objects.all():
        # Preprocess some values for consistent formatting
        entry = {}
        for field in ["PtpId", "ImdbId", "ErrorMessage", "ReleaseName", "PtpTorrentId"]:
            entry[field] = getattr(release, field)
        entry["Size"] = {
            "sort": int(release.Size),
            "_": SizeToText(release.Size),
        }
        entry["LastModificationTime"] = {
            "sort": int(release.LastModificationTime.strftime("%s")),
            "_": TimeDifferenceToText(
                timezone.now() - release.LastModificationTime,
                2,
            ),
        }

        source = MyGlobals.SourceFactory.GetSource(release.AnnouncementSourceName)
        if source is not None:
            icon = url_for("static", filename=f"source_icon/{source.Name}.ico")
            entry["AnnouncementSourceName"] = {
                "sort": release.AnnouncementSourceName,
                "_": f'<img src="{icon}">',
            }
            url = source.GetUrlFromId(release.AnnouncementId)
            if url:
                entry["AnnouncementSourceName"][
                    "_"
                ] = f'<a href="{url}"><img src="{icon}"></a>'

        icon = url_for("static", filename=GetStateIcon(release.JobRunningState))
        logUrl = url_for("log", jobId=release.Id)
        entry["JobRunningState"] = {
            "sort": release.JobRunningState,
            "_": f'<a href="{logUrl}"><img src="{icon}"/></a>',
        }

        entry["Actions"] = ""
        if release.CanResumed():
            url = url_for("StartJob", jobId=release.Id)
            icon = url_for("static", filename="start.png")
            entry[
                "Actions"
            ] += f'<a href="#" onclick=\'executeJobCommand( this, {release.Id}, "/start/" ); jobsTable.ajax.reload(null, false); return false;\'><img src={icon} title="Start"></a>'
        if release.CanStopped():
            url = url_for("StopJob", jobId=release.Id)
            icon = url_for("static", filename="stop.png")
            entry[
                "Actions"
            ] += f'<a href="#" onclick=\'executeJobCommand( this, {release.Id}, "/stop/" ); jobsTable.ajax.reload(null, false); return false;\'><img src={icon} title="Stop"></a>'
        if release.CanEdited():
            url = url_for("EditJob", jobId=release.Id)
            icon = url_for("static", filename="edit.png")
            entry["Actions"] += f'<a href="{url}"><img src={icon} title="Edit"></a>'
        if release.CanDeleted():
            url = url_for("StartJob", jobId=release.Id)
            icon = url_for("static", filename="delete.png")
            entry[
                "Actions"
            ] += f'<a href="#" class="delete_job_context_menu" PtpUploaderJobId="{release.Id}"><img src={icon} title="Delete"></a>'
        entries.append(entry)

    return jsonify({"data": entries, "settings": settings})


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
