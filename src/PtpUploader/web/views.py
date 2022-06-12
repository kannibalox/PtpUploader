import logging
import os
import time
import urllib

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import dynaconf

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from PtpUploader import Ptp, nfo_parser
from PtpUploader.Helper import SizeToText, TimeDifferenceToText
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderMessage import (
    PtpUploaderMessageDeleteJob,
    PtpUploaderMessageStartJob,
    PtpUploaderMessageStopJob,
)
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings, config

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
        ReleaseInfo.JobState.Scheduled: "fa-clock",
    }
    return f'<span class="icon"><i class="fas {i[state]}"></i></span>'


@login_required
def jobs(request):
    return render(request, "jobs.html", {"state": ReleaseInfo.JobState.choices})


@login_required
def log(_request, r_id: int):
    get_object_or_404(ReleaseInfo, Id=r_id)

    log_msg = ""
    logFilePath = os.path.join(Settings.GetJobLogPath(), str(r_id))

    if os.path.isfile(logFilePath):
        with open(logFilePath) as fh:
            log_msg = fh.read()
    else:
        log_msg = "Log file '%s' doesn't exists!" % logFilePath

    log_msg = log_msg.replace("\n", r"<br>")

    return HttpResponse(log_msg)


def GetPtpOrImdbId(releaseInfo, text):
    imdbId = nfo_parser.get_imdb_id(text)
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
                releaseInfo.ImdbId = Ptp.GetMoviePageOnPtp(
                    logger, releaseInfo.PtpId
                ).ImdbId


@login_required
def jobs_get_latest(request):
    releaseInfo = ReleaseInfo()
    GetPtpOrImdbId(releaseInfo, request.GET["PtpOrImdbLink"])

    torrentId = 0

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
                torrentId = torrent["Id"]

                difference = datetime.now() - torrent["UploadTime"]

    return JsonResponse(
        {
            "Result": "OK",
            "TorrentId": torrentId,
            "UploadedAgo": TimeDifferenceToText(difference).lower(),
        }
    )


@login_required
def settings(request):
    if request.method == "POST":
        form = forms.SettingsForm(request.POST)
        if form.is_valid():
            config.image_host.use = form.cleaned_data["image_host_use"]
            config.ptp.username = form.cleaned_data["ptp_username"]
            config.ptp.password = form.cleaned_data["ptp_password"]
            config.ptp.announce_url = form.cleaned_data["ptp_announce_url"]
            dynaconf.loaders.yaml_loader.write(
                Path("~/.config/ptpuploader/config.yml").expanduser(),
                {
                    "ptp": {
                        "username": form.cleaned_data["ptp_username"],
                        "password": form.cleaned_data["ptp_password"],
                        "announce_url": form.cleaned_data["ptp_announce_url"],
                    },
                    "client": {
                        "use": form.cleaned_data["client_use"],
                        form.cleaned_data["client_use"]: {
                            "address": form.cleaned_data["client_address"]
                        },
                    },
                    "image_host": {"use": form.cleaned_data["image_host_use"]},
                },
            )
    else:
        form = forms.SettingsForm()
    return render(request, "settings.html", {"form": form})


@login_required
def bulk_upload(request):
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = forms.BulkReleaseForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            for link in form.cleaned_data["Links"].split("\n"):
                release = ReleaseInfo(AnnouncementId=link)
                release.JobStartMode = JobStartMode.Manual
                if "post_stop_before" in request.POST:
                    release.StopBeforeUploading = True
                else:
                    release.StopBeforeUploading = False
                release.save()
            for path in form.cleaned_data["Paths"].split("\n"):
                if not path.strip():
                    continue
                path = Path(path)
                release = ReleaseInfo()
                release.AnnouncementSourceName = "file"
                release.ReleaseDownloadPath = path
                release.ReleaseName = path.name
                release.JobStartMode = JobStartMode.Manual
                if "post_stop_before" in request.POST:
                    release.StopBeforeUploading = True
                else:
                    release.StopBeforeUploading = False
                release.save()
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect("/jobs")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = forms.BulkReleaseForm()

    return render(request, "bulk.html", {"form": form})


@login_required
def jobs_json(_):
    settings = {}

    entries = []
    for release in ReleaseInfo.objects.all():
        # Preprocess some values for consistent formatting
        entry = {}
        for field in (
            "Id",
            "PtpId",
            "ImdbId",
            "ErrorMessage",
            "ReleaseName",
            "PtpTorrentId",
        ):
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
        entry["Actions"] = []
        if release.CanResumed():
            entry["Actions"] += ["start"]
        if release.CanStopped():
            entry["Actions"] += ["stop"]
        if release.CanEdited():
            entry["Actions"] += ["edit"]
        if release.CanDeleted():
            entry["Actions"] += ["delete"]
        entry["Actions"] = (",").join(entry["Actions"])
        entries.append(entry)

        # Format scheduled items with a dynamic sub-message
        if release.JobRunningState == ReleaseInfo.JobState.Scheduled:
            entry["ErrorMessage"] = "Scheduled to  run in " + TimeDifferenceToText(
                release.ScheduleTime - timezone.now(),
                agoText="",
                noDifferenceText="just a moment",
            )

    return JsonResponse({"data": entries, "settings": settings})


@login_required
def local_dir(request):
    d: Path
    if "dir" not in request.GET:
        d = Path(config.web.file_selector_root or "~").expanduser()
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


@login_required
def start_job(_, r_id):
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
    releaseInfo.StopBeforeUploading = False

    releaseInfo.save()
    MyGlobals.PtpUploader.add_message(PtpUploaderMessageStartJob(r_id))
    return HttpResponse("OK")


@login_required
def stop_job(_, r_id: int):
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
    if not releaseInfo.CanStopped():
        return HttpResponse("The job is already stopped!")

    MyGlobals.PtpUploader.add_message(PtpUploaderMessageStopJob(r_id))
    return HttpResponse("OK")


@csrf_exempt
def create(request):
    if (
        request.method != "POST"
        or "password" not in request.POST
        or request.POST["password"] != config.web.api_key
    ):
        raise PermissionDenied
    dest_path = Path(Settings.GetTemporaryPath(), f"{time.time()}.torrent")
    with dest_path.open("wb") as dest:
        for chunk in request.FILES["torrent"].chunks():
            dest.write(chunk)
    release = ReleaseInfo()
    release.SourceTorrentFilePath = dest_path
    release.AnnouncementSourceName = "torrent"
    release.ImdbId = nfo_parser.get_imdb_id(request.POST["imdbUrl"])
    source, source_id = MyGlobals.SourceFactory.GetSourceAndIdByUrl(
        request.POST["SourceUrl"]
    )
    if source is not None:
        release.AnnouncementSourceName = source.Name
        release.AnnouncementId = source_id
    release.JobStartMode = JobStartMode.Manual
    release.StopBeforeUploading = True
    release.save()
    response = JsonResponse({"result": "OK", "jobId": release.Id})
    response["Access-Control-Allow-Origin"] = "*"
    return response


@login_required
def delete_job(_, r_id: int, mode: str):
    releaseInfo = ReleaseInfo.objects.get(Id=r_id)
    if not releaseInfo.CanDeleted():
        return HttpResponse("The job cannot be deleted!")

    MyGlobals.PtpUploader.add_message(PtpUploaderMessageDeleteJob(r_id, mode))
    return HttpResponse("OK")


@login_required
def edit_job(request, r_id: int = -1):
    job: Dict[str, Any] = {
        "id": r_id
    }  # Non-form data for display but too complex for a template
    if r_id > 0:
        release = get_object_or_404(ReleaseInfo, Id=r_id)
    else:
        release = ReleaseInfo()
    if request.method == "POST":
        if "delete" in request.POST:
            if not release.CanDeleted():
                return HttpResponse("The job cannot be deleted!")
            MyGlobals.PtpUploader.add_message(PtpUploaderMessageDeleteJob(r_id, "job"))
            return HttpResponseRedirect("/jobs")
        # create a form instance and populate it with data from the request:
        form = forms.ReleaseForm(request.POST, instance=release)
        # check whether it's valid:
        if form.is_valid():
            form.save()
            release.JobRunningState = JobRunningState.WaitingForStart
            if r_id < 0:
                if request.POST["TorrentLink"]:
                    source, source_id = MyGlobals.SourceFactory.GetSourceAndIdByUrl(
                        request.POST["TorrentLink"]
                    )
                    if source is None:
                        return False

                    release.AnnouncementSourceName = source.Name
                    release.AnnouncementId = source_id
                elif request.POST["LocalFile"]:
                    path = Path(request.POST["LocalFile"])
                    release.AnnouncementSourceName = "file"
                    release.ReleaseDownloadPath = path
                    release.ReleaseName = path.name
                elif request.FILES["RawFile"]:
                    dest_path = Path(
                        Settings.GetTemporaryPath(), f"{time.time()}.torrent"
                    )
                    with dest_path.open("wb") as dest:
                        for chunk in request.FILES["RawFile"].chunks():
                            dest.write(chunk)
                    release.SourceTorrentFilePath = dest_path
                    release.AnnouncementSourceName = "torrent"
            if "post_stop_before" in request.POST:
                release.StopBeforeUploading = True
            else:
                release.StopBeforeUploading = False
            GetPtpOrImdbId(release, release.ImdbId)
            release.save()
            MyGlobals.PtpUploader.add_message(PtpUploaderMessageStartJob(release.Id))
            return HttpResponseRedirect("/jobs")
    # if a GET (or any other method) we'll create a blank form
    else:
        job["Screenshots"] = {}
        if release.Screenshots:
            for f, shots in release.Screenshots.items():
                name = str(Path(f).name)
                job["Screenshots"][name] = ""
                for s in shots:
                    job["Screenshots"][name] += f'<img src="{s}"/>'
        source = MyGlobals.SourceFactory.GetSource(release.AnnouncementSourceName)
        if source is not None:
            filename = "source_icon/%s.ico" % release.AnnouncementSourceName
            job["SourceIcon"] = static(filename)
            job["SourceUrl"] = source.GetUrlFromId(release.AnnouncementId)
        job["SkipDuplicateCheckingButton"] = release.DuplicateCheckCanIgnore
        job["CanEdited"] = release.CanEdited
        job["StopBeforeUploading"] = release.StopBeforeUploading
        job["Status"] = release.get_JobRunningState_display()
        if release.ErrorMessage:
            job["Status"] += f" - {release.ErrorMessage}"

        initial = {
            "Subtitles": release.Subtitles,
            "Tags": release.Tags.split(","),
            "TrumpableNoEnglish": release.TrumpableReasons.NO_ENGLISH_SUBS
            in release.Trumpable,
            "TrumpableHardSubs": release.TrumpableReasons.HARDCODED_SUBS
            in release.Trumpable,
        }
        if release.ImdbId:
            initial["ImdbId"] = f"https://imdb.com/title/tt{release.ImdbId}"
        form = forms.ReleaseForm(instance=release, initial=initial)
    return render(request, "edit_job.html", {"form": form, "settings": {}, "job": job})
