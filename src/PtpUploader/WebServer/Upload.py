import os
import sys
import uuid
from pathlib import Path

from flask import jsonify, render_template, request
from werkzeug.utils import secure_filename

import bencode

from PtpUploader.Helper import GetSuggestedReleaseNameAndSizeFromTorrentFile, SizeToText
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderMessage import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth
from PtpUploader.WebServer.JobCommon import JobCommon
from PtpUploader.WebServer.UploadFile import UploadFile


def IsFileAllowed(filename):
    return os.path.splitext(filename)[1] == ".torrent"


def UploadTorrentFile(releaseInfo, request):
    if 'uploaded_torrent' not in request.files:
        return False
    file = request.files['uploaded_torrent']
    torrentFilename: str = file.filename
    if not IsFileAllowed(torrentFilename):
        return False

    torrentFilename = secure_filename(torrentFilename)
    torrentFilename = os.path.join(Settings.GetTemporaryPath(), torrentFilename)
    file.save(torrentFilename)
    if not os.path.isfile(torrentFilename):
        return False

    releaseInfo.SourceTorrentFilePath = torrentFilename
    releaseInfo.AnnouncementSourceName = "torrent"
    releaseInfo.Size = int(len(file.read()))
    releaseInfo.ReleaseName = Path(torrentFilename).stem
    return True


def UploadTorrentSiteLink(releaseInfo, request):
    torrentPageLink = request.values["torrent_site_link"]
    if len(torrentPageLink) <= 0:
        return False

    source, id = MyGlobals.SourceFactory.GetSourceAndIdByUrl(torrentPageLink)
    if source is None:
        return False

    releaseInfo.AnnouncementSourceName = source.Name
    releaseInfo.AnnouncementId = id
    return True


@app.route("/upload/", methods=["GET", "POST"])
@requires_auth
def upload():
    if request.method == "POST":
        releaseInfo = ReleaseInfo.objects.create()
        releaseInfo.save()

        # Announcement

        if UploadTorrentFile(releaseInfo, request):
            pass
        elif UploadFile(releaseInfo, request):
            pass
        elif UploadTorrentSiteLink(releaseInfo, request):
            pass
        else:
            return "Select something to upload!"

        if request.values["release_name"]:
            releaseInfo.ReleaseName = request.values["release_name"]
        releaseInfo.SetStopBeforeUploading(
            request.values["post"] == "Upload but stop before uploading"
        )

        JobCommon.FillReleaseInfoFromRequestData(releaseInfo, request)

        # TODO: todo multiline torrent site link field

        releaseInfo.save()
        print(releaseInfo.Id)
        MyGlobals.PtpUploader.AddMessage(PtpUploaderMessageStartJob(releaseInfo.Id))
        releaseInfo.save()

    # job parameter is needed because it uses the same template as edit job
    job = {}
    job["Subtitles"] = []
    job["SkipDuplicateCheckingButton"] = 0

    if Settings.ForceDirectorylessSingleFileTorrent:
        job["ForceDirectorylessSingleFileTorrent"] = 1

    if Settings.OverrideScreenshots:
        job["OverrideScreenshots"] = 1

    if Settings.PersonalRip:
        job["PersonalRip"] = 1

    if Settings.SkipDuplicateChecking:
        job["SkipDuplicateCheckingButton"] = sys.maxsize

    job["ReleaseNotes"] = Settings.ReleaseNotes

    return render_template("upload.html", job=job)
