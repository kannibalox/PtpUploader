import os
import sys
import uuid

from flask import jsonify, make_response, request
from PtpUploader.Helper import GetSuggestedReleaseNameAndSizeFromTorrentFile
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.NfoParser import NfoParser
from PtpUploader.PtpUploaderMessage import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.WebServer import app


def MakeExternalCreateJobErrorResponse(errorMessage):
    response = make_response(jsonify(result="Error", message=errorMessage))
    response.headers[
        "Access-Control-Allow-Origin"
    ] = "*"  # Enable cross-origin resource sharing.
    return response


def DoParsePageForExternalCreateJob(releaseInfo, sourceUrl, pageContent):
    source, id = MyGlobals.SourceFactory.GetSourceAndIdByUrl(sourceUrl)
    if source is None:
        return False

    try:
        source.ParsePageForExternalCreateJob(MyGlobals.Logger, releaseInfo, pageContent)
    except Exception:
        MyGlobals.Logger.exception("Got exception in DoParsePageForExternalCreateJob.")


@app.route("/ajax/create", methods=["POST"])
def ajaxExternalCreateJob():
    if ("Password" not in request.values) or request.values[
        "Password"
    ] != Settings.GreasemonkeyTorrentSenderPassword:
        return MakeExternalCreateJobErrorResponse(
            "Invalid Greasemonkey Send to Script password!"
        )

    file = request.files.get("Torrent")
    # file is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.)
    if not file:
        return MakeExternalCreateJobErrorResponse("Got no torrent file!")

    filename = "external job." + str(uuid.uuid1()) + ".torrent"
    sourceTorrentFilePath = os.path.join(Settings.GetTemporaryPath(), filename)
    file.save(sourceTorrentFilePath)

    releaseName, torrentContentSize = GetSuggestedReleaseNameAndSizeFromTorrentFile(
        sourceTorrentFilePath
    )

    releaseInfo = ReleaseInfo()
    releaseInfo.JobRunningState = JobRunningState.Paused
    releaseInfo.JobStartMode = JobStartMode.Manual
    releaseInfo.SourceTorrentFilePath = sourceTorrentFilePath
    releaseInfo.AnnouncementSourceName = "torrent"
    releaseInfo.ReleaseName = releaseName
    releaseInfo.Size = torrentContentSize
    releaseInfo.SetOverrideScreenshots(Settings.OverrideScreenshots)
    releaseInfo.ReleaseNotes = Settings.ReleaseNotes

    if Settings.ForceDirectorylessSingleFileTorrent:
        releaseInfo.SetForceDirectorylessSingleFileTorrent()

    if Settings.PersonalRip:
        releaseInfo.SetPersonalRip()

    if Settings.SkipDuplicateChecking:
        releaseInfo.DuplicateCheckCanIgnore = sys.maxsize

    imdbId = ""
    if "ImdbUrl" in request.values:
        imdbId = NfoParser.GetImdbId(request.values["ImdbUrl"])
        if len(imdbId) > 0:
            releaseInfo.ImdbId = imdbId

    if "PageContent" in request.values:
        DoParsePageForExternalCreateJob(
            releaseInfo, request.values["SourceUrl"], request.values["PageContent"]
        )

    releaseInfo.save()

    # Just add the job, don't start it.

    response = make_response(jsonify(result="OK", jobId=releaseInfo.Id))
    response.headers[
        "Access-Control-Allow-Origin"
    ] = "*"  # Enable cross-origin resource sharing.
    return response
