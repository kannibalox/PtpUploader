import logging
import os
import urllib

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from PtpUploader import Ptp
from PtpUploader.Helper import SizeToText, TimeDifferenceToText
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.NfoParser import NfoParser
from PtpUploader.PtpUploaderMessage import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings

from . import forms


logger = logging.getLogger(__name__)


def GetStateIcon(state: int) -> str:
    if state == ReleaseInfo.JobState.InDownload:
        return '<div class="download-spinner"></div>'
    if state == ReleaseInfo.JobState.InProgress:
        return '<div class="inprogress-spinner"></div>'
    if state in [
        ReleaseInfo.JobState.Ignored,
        ReleaseInfo.JobState.Ignored_AlreadyExists,
        ReleaseInfo.JobState.Ignored_Forbidden,
        ReleaseInfo.JobState.Ignored_MissingInfo,
        ReleaseInfo.JobState.Ignored_NotSupported,
    ]:
        return '<span class="icon"><i class="fas fa-exclamation-triangle has-text-warning"></i></span>'
    i = {
        ReleaseInfo.JobState.Finished: "fa-check has-text-success",
        ReleaseInfo.JobState.Failed: "fa-exclamation-circle has-text-danger",
        ReleaseInfo.JobState.WaitingForStart: "fa-hourglass has-text-info",
        ReleaseInfo.JobState.Paused: "fa-pause has-text-info",
        ReleaseInfo.JobState.DownloadedAlreadyExists: "fa-frown has-text-warning",
        ReleaseInfo.JobState.InProgress: "fa-spinner fa-pulse has-text-info",
        ReleaseInfo.JobState.InDownload: "spinner",
    }
    return f'<span class="icon"><i class="fas {i[state]}"></i></span>'


def jobs(request):
    return render(request, "jobs.html")


def log(request, r_id: int):
    get_object_or_404(ReleaseInfo, Id=r_id)

    log_msg = ""
    logFilePath = os.path.join(Settings.GetJobLogPath(), str(r_id))

    if os.path.isfile(logFilePath):
        with open(logFilePath, "r") as fh:
            log_msg = fh.read()
    else:
        log_msg = "Log file '%s' doesn't exists!" % logFilePath

    log_msg = log_msg.replace("\n", r"<br>")

    return HttpResponse(log_msg)


def GetPtpOrImdbId(releaseInfo, text):
    imdbId = NfoParser.GetImdbId(text)
    if len(imdbId) > 0:
        releaseInfo.ImdbId = imdbId
    elif text in ["0", "-"]:
        releaseInfo.ImdbId = "0"
    else:
        # Using urlparse because of torrent permalinks:
        # https://passthepopcorn.me/torrents.php?id=9730&torrentid=72322
        url = urllib.parse.urlparse(text)
        if (
            url.netloc == "passthepopcorn.me"
            or url.netloc == "www.passthepopcorn.me"
            or url.netloc == "tls.passthepopcorn.me"
        ):
            params = urllib.parse.parse_qs(url.query)
            ptpIdList = params.get("id")
            if ptpIdList is not None:
                releaseInfo.PtpId = ptpIdList[0]


def jobs_get_latest(request):
    releaseInfo = ReleaseInfo()
    GetPtpOrImdbId(releaseInfo, request.GET["PtpOrImdbLink"])

    torrentId = 0
    uploadedAgo = ""

    if releaseInfo.ImdbId != "0":
        Ptp.Login()

        movieOnPtpResult = None
        if releaseInfo.PtpId:
            movieOnPtpResult = Ptp.GetMoviePageOnPtp(logger, releaseInfo.PtpId)
        else:
            movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId(logger, releaseInfo.ImdbId)

        if movieOnPtpResult:
            torrent = movieOnPtpResult.GetLatestTorrent()
            if torrent:
                torrentId = torrent.TorrentId

                difference = datetime.utcnow() - torrent.GetUploadTimeAsDateTimeUtc()
                uploadedAgo = (
                    "(Latest torrent uploaded: "
                    + TimeDifferenceToText(difference).lower()
                    + ")"
                )

    return JsonResponse(
        {"Result": "OK", "TorrentId": torrentId, "UploadedAgo": uploadedAgo}
    )


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
        else:
            entry["AnnouncementSourceName"] = {
                "sort": "",
                "_": "",
            }

        icon = GetStateIcon(release.JobRunningState)
        logUrl = reverse("log", args=[release.Id])
        entry["JobRunningState"] = {
            "sort": release.JobRunningState,
            "_": f'<a href="{logUrl}" title="{release.get_JobRunningState_display()}">{icon}</a>',
        }

        # Build actions
        entry["Actions"] = "<span>"
        if release.CanResumed():
            url = reverse("start_job", args=[release.Id])
            icon = static("start.png")
            entry[
                "Actions"
            ] += f'<a href="#" onclick=\'executeJobCommand( this, {release.Id}, "/start" ); jobsTable.ajax.reload(null, false); return false;\'><span class="icon is-small"><i class="fas fa-play-circle"></i></span></a>'
        if release.CanStopped():
            url = reverse("stop_job", args=[release.Id])
            icon = static("stop.png")
            entry[
                "Actions"
            ] += f'<a href="#" onclick=\'executeJobCommand( this, {release.Id}, "/stop" ); jobsTable.ajax.reload(null, false); return false;\'><span class="icon is-small"><i class="fas fa-stop-circle"></i></span></a>'
        if release.CanEdited():
            url = reverse("edit_job", args=[release.Id])
            icon = static("edit.png")
            entry[
                "Actions"
            ] += f'<a href="{url}"><span class="icon"><i class="fas fa-edit"></i></span></a>'
        if release.CanDeleted():
            icon = static("delete.png")
            entry[
                "Actions"
            ] += f'<a href="#" class="delete_job_context_menu" PtpUploaderJobId="{release.Id}"><span class="icon is-small"><i class="fas fa-trash has-text-danger"></i></span></a>'
        entry["Actions"] += "</span>"
        entries.append(entry)

    return JsonResponse({"data": entries, "settings": settings})


def local_dir(request):
    d: Path
    if "dir" not in request.GET:
        d = Path(Settings.WebServerFileTreeInitRoot)
    else:
        d = Path(request.GET["dir"])
    val = []
    for child in sorted(d.iterdir()):
        c = {"title": child.name, "key": str(child)}
        if child.is_dir():
            c["folder"] = True
            c["lazy"] = True
        elif child.suffix.lower() in [".mkv", ".avi", ".mp4", ".vob", ".ifo", ".bup"]:
            c["icon"] = "film"
        val.append(c)
    return JsonResponse(val, safe=False)  # It's just a list, probably safe


def start_job(request, r_id):
    # TODO: This is very far from perfect. There is no guarantee that the job didn't start meanwhile.
    # Probably only the WorkerThread should change the running state.
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
    if not releaseInfo.CanResumed():
        return HttpResponse("The job is already running!")

    releaseInfo.JobRunningState = JobRunningState.WaitingForStart

    # Make sure that job is no longer handled as an automatically started job.
    # Manual forced jobs will resumed as manual forced.
    if releaseInfo.JobStartMode == JobStartMode.Automatic:
        releaseInfo.JobStartMode = JobStartMode.Manual

    # Resume the job normally.
    releaseInfo.SetStopBeforeUploading(False)

    releaseInfo.save()
    MyGlobals.PtpUploader.add_message(PtpUploaderMessageStartJob(r_id))
    return HttpResponse("OK")


def stop_job(request, r_id: int):
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
    if not releaseInfo.CanStopped():
        return HttpResponse("The job is already stopped!")

    MyGlobals.PtpUploader.add_message(PtpUploaderMessageStopJob(r_id))
    return HttpResponse("OK")


def delete_job(request, r_id: int, mode: str):
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
    if not releaseInfo.CanDeleted():
        return HttpResponse("The job cannot be deleted!")

    MyGlobals.PtpUploader.add_message(PtpUploaderMessageDeleteJob(r_id, mode))
    return HttpResponse("OK")


def edit_job(request, r_id: int = -1):
    job: Dict[str, Any] = {
        "id": r_id
    }  # Non-form data for display but too complex for a template
    if r_id > 0:
        release = get_object_or_404(ReleaseInfo, Id=r_id)
    else:
        release = ReleaseInfo()
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = forms.ReleaseForm(request.POST, instance=release)
        # check whether it's valid:
        if form.is_valid():
            form.save()
            release.JobRunningState = JobRunningState.WaitingForStart
            if r_id < 0:
                if request.POST["TorrentLink"]:
                    source, id = MyGlobals.SourceFactory.GetSourceAndIdByUrl(
                        request.POST["TorrentLink"]
                    )
                    if source is None:
                        return False

                    release.AnnouncementSourceName = source.Name
                    release.AnnouncementId = id
                elif request.POST["TorrentLink"]:
                    pass
            if "post_stop_before" in request.POST:
                release.StopBeforeUploading = True
            else:
                release.StopBeforeUploading = False
            release.save()
            MyGlobals.PtpUploader.add_message(PtpUploaderMessageStartJob(release.Id))
            return HttpResponseRedirect("/jobs")
    # if a GET (or any other method) we'll create a blank form
    else:
        job["Screenshots"] = {}
        if release.Screenshots:
            for f, shots in release.Screenshots.items():
                path = Path(f).name
                job["Screenshots"][path] = ""
                for s in shots:
                    job["Screenshots"][path] += f'<img src="{s}"/>'
        source = MyGlobals.SourceFactory.GetSource(release.AnnouncementSourceName)
        if source is not None:
            filename = "source_icon/%s.ico" % release.AnnouncementSourceName
            job["SourceIcon"] = static(filename)
            job["SourceUrl"] = source.GetUrlFromId(release.AnnouncementId)
        job["SkipDuplicateCheckingButton"] = release.DuplicateCheckCanIgnore
        job["CanEdited"] = release.CanEdited

        form = forms.ReleaseForm(
            instance=release,
            initial={
                "Subtitles": release.Subtitles,
                "Tags": release.Tags.split(","),
                "TrumpableNoEnglish": release.TrumpableReasons.NO_ENGLISH_SUBS
                in release.Trumpable,
                "TrumpableHardSubs": release.TrumpableReasons.HARDCODED_SUBS
                in release.Trumpable,
            },
        )
    return render(request, "edit_job.html", {"form": form, "settings": {}, "job": job})
