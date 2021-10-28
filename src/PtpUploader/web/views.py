import json
import os

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import html, timezone
from PtpUploader.Helper import SizeToText, TimeDifferenceToText
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderMessage import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth
from PtpUploader.WebServer.JobCommon import JobCommon

from . import forms


def GetStateIcon(state: int) -> str:
    if state == JobRunningState.Finished:
        return "success.png"
    elif state == JobRunningState.Failed:
        return "error.png"
    elif state in [
        JobRunningState.Ignored,
        JobRunningState.Ignored_AlreadyExists,
        JobRunningState.Ignored_Forbidden,
        JobRunningState.Ignored_MissingInfo,
        JobRunningState.Ignored_NotSupported,
    ]:
        return "warning.png"
    elif state == JobRunningState.WaitingForStart:
        return "hourglass.png"
    elif state in [JobRunningState.InProgress, ReleaseInfo.JobState.InDownload]:
        return "throbber.gif"
    elif state == JobRunningState.Paused:
        return "pause.png"
    elif state == JobRunningState.Scheduled:
        return "scheduled.png"
    elif state == JobRunningState.DownloadedAlreadyExists:
        return "sad.png"

    # This is not possible.
    return "error.png"


def jobs(request):
    return render(request, "jobs.html")


def log(request, r_id: int):
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)

    logFilePath = releaseInfo.GetLogFilePath()
    log_msg = ""

    if os.path.isfile(logFilePath):
        with open(logFilePath, "r") as fh:
            log_msg = fh.read()
    else:
        log_msg = "Log file '%s' doesn't exists!" % logFilePath

    log_msg = log_msg.replace("\n", r"<br>")

    return HttpResponse(log_msg)


def jobs_json(request):
    settings = {}
    if Settings.OpenJobPageLinksInNewTab == "0":
        settings["OpenJobPageLinksInNewTab"] = ""
    else:
        settings["OpenJobPageLinksInNewTab"] = ' target="_blank"'

    entries = []
    for release in ReleaseInfo.objects.all():
        # Preprocess some values for consistent formatting
        entry = {}
        for field in ("PtpId", "ImdbId", "ErrorMessage", "ReleaseName", "PtpTorrentId"):
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

        # Build icons and links
        source = MyGlobals.SourceFactory.GetSource(release.AnnouncementSourceName)
        if source is not None:
            icon = static(f"source_icon/{source.Name}.ico")
            entry["AnnouncementSourceName"] = {
                "sort": release.AnnouncementSourceName,
                "_": f'<img src="{icon}">',
            }
            url = source.GetUrlFromId(release.AnnouncementId)
            if url:
                entry["AnnouncementSourceName"][
                    "_"
                ] = f'<a href="{url}"><img src="{icon}"></a>'

        icon = static(GetStateIcon(release.JobRunningState))
        logUrl = reverse("log", args=[release.Id])
        entry["JobRunningState"] = {
            "sort": release.JobRunningState,
            "_": f'<a href="{logUrl}"><img src="{icon}"/></a>',
        }

        # Build actions
        entry["Actions"] = ""
        if release.CanResumed():
            url = reverse("start_job", args=[release.Id])
            icon = static("start.png")
            entry[
                "Actions"
            ] += f'<a href="#" onclick=\'executeJobCommand( this, {release.Id}, "/start/" ); jobsTable.ajax.reload(null, false); return false;\'><img src={icon} title="Start"></a>'
        if release.CanStopped():
            url = reverse("stop_job", args=[release.Id])
            icon = static("stop.png")
            entry[
                "Actions"
            ] += f'<a href="#" onclick=\'executeJobCommand( this, {release.Id}, "/stop/" ); jobsTable.ajax.reload(null, false); return false;\'><img src={icon} title="Stop"></a>'
        if release.CanEdited():
            url = reverse("edit_job", args=[release.Id])
            icon = static("edit.png")
            entry["Actions"] += f'<a href="{url}"><img src={icon} title="Edit"></a>'
        if release.CanDeleted():
            icon = static("delete.png")
            entry[
                "Actions"
            ] += f'<a href="#" class="delete_job_context_menu" PtpUploaderJobId="{release.Id}"><img src={icon} title="Delete"></a>'
        entries.append(entry)

    return JsonResponse({"data": entries, "settings": settings})


def start_job(r_id) -> str:
    # TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
    # Probably only the WorkerThread should change the running state.
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
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
    MyGlobals.PtpUploader.add_message(PtpUploaderMessageStartJob(r_id))
    return "OK"


def stop_job(r_id) -> str:
    # TODO: This is very far from perfect. There is no guarantee that the job didn't stop meanwhile.
    # Probably only the WorkerThread should change the running state.
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
    if not releaseInfo.CanStopped():
        return "The job is already stopped!"

    MyGlobals.PtpUploader.add_message(PtpUploaderMessageStopJob(r_id))
    return "OK"


def edit_job(request, r_id: int):
    job = {}  # Non-form data for display but too complex for a template
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = forms.ReleaseForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect("/thanks/")

    # if a GET (or any other method) we'll create a blank form
    else:
        release = ReleaseInfo.objects.get(Id=r_id)
        source = MyGlobals.SourceFactory.GetSource(release.AnnouncementSourceName)
        job["Screenshots"] = {}
        if release.Screenshots:
            for f in json.loads(release.Screenshots):
                path = f[0].replace(release.UploadTorrentCreatePath, "").strip("/")
                job["Screenshots"][path] = ""
                for s in f[1]:
                    job["Screenshots"][path] += f'<img src="{s}"/>'
        if source is not None:
            filename = "source_icon/%s.ico" % release.AnnouncementSourceName
            job["SourceIcon"] = static(filename)
            job["SourceUrl"] = source.GetUrlFromId(release.AnnouncementId)

        form = forms.ReleaseForm(instance=release)
    return render(request, "edit_job.html", {"form": form, "settings": {}, "job": job})
