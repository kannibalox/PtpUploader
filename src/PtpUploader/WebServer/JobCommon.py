import json
import os
import urllib.parse
from datetime import datetime
from urllib.parse import parse_qs

from flask import jsonify, request
from PtpUploader.Helper import TimeDifferenceToText
from PtpUploader.IncludedFileList import IncludedFileList
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.NfoParser import NfoParser
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth
from werkzeug.utils import secure_filename

from PtpUploader import Ptp


class JobCommon:
    # Needed because urlparse return with empty netloc if protocol is not set.
    @staticmethod
    def __AddHttpToUrl(url):
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return "http://" + url

    @staticmethod
    def __GetYouTubeId(text):
        url = urllib.parse.urlparse(JobCommon.__AddHttpToUrl(text))
        if url.netloc == "youtube.com" or url.netloc == "www.youtube.com":
            params = parse_qs(url.query)
            youTubeIdList = params.get("v")
            if youTubeIdList is not None:
                return youTubeIdList[0]

        return ""

    @staticmethod
    def GetPtpOrImdbId(releaseInfo, text):
        imdbId = NfoParser.GetImdbId(text)
        if len(imdbId) > 0:
            releaseInfo.ImdbId = imdbId
        elif text == "0" or text == "-":
            releaseInfo.ImdbId = "0"
        else:
            # Using urlparse because of torrent permalinks:
            # https://passthepopcorn.me/torrents.php?id=9730&torrentid=72322
            url = urllib.parse.urlparse(JobCommon.__AddHttpToUrl(text))
            if (
                url.netloc == "passthepopcorn.me"
                or url.netloc == "www.passthepopcorn.me"
                or url.netloc == "tls.passthepopcorn.me"
            ):
                params = parse_qs(url.query)
                ptpIdList = params.get("id")
                if ptpIdList is not None:
                    releaseInfo.PtpId = ptpIdList[0]

    @staticmethod
    def FillReleaseInfoFromRequestData(releaseInfo, request):
        # For PTP

        releaseInfo.Type = request.values["type"]
        JobCommon.GetPtpOrImdbId(releaseInfo, request.values["imdb"])
        releaseInfo.Directors = request.values["artists[]"]
        releaseInfo.Title = request.values["title"].strip()
        releaseInfo.Year = request.values["year"]
        if "genre_tags[]" in request.values:
            releaseInfo.Tags = ", ".join(request.values.getlist("genre_tags[]"))
        else:
            releaseInfo.Tags = ""
        releaseInfo.MovieDescription = request.values["album_desc"]
        releaseInfo.CoverArtUrl = request.values["image"].strip()
        releaseInfo.YouTubeId = JobCommon.__GetYouTubeId(request.values["trailer"])

        if request.values.get("personal_rip") is not None:
            releaseInfo.SetPersonalRip()

        if request.values.get("scene") is not None:
            releaseInfo.SetSceneRelease()

        if request.values.get("special") is not None:
            releaseInfo.SetSpecialRelease()

        if request.values.get("TrumpableForNoEnglishSubtitles") is not None:
            releaseInfo.SetTrumpableForNoEnglishSubtitles()
        if request.values.get("TrumpableForHardcodedSubtitles") is not None:
            releaseInfo.SetTrumpableForHardcodedSubtitles()

        codec = request.values.get("codec")
        if (codec is None) or codec == "---" or codec == "Other":
            releaseInfo.Codec = request.values["other_codec"]
        else:
            releaseInfo.Codec = codec

        container = request.values.get("container")
        if (container is None) or container == "---" or container == "Other":
            releaseInfo.Container = request.values["other_container"]
        else:
            releaseInfo.Container = container

        resolutionType = request.values.get("resolution")
        if (resolutionType is not None) and resolutionType != "---":
            releaseInfo.ResolutionType = resolutionType

        releaseInfo.Resolution = request.values["other_resolution"]

        source = request.values.get("source")
        if (source is None) or source == "---" or source == "Other":
            releaseInfo.Source = request.values["other_source"]
        else:
            releaseInfo.Source = source

        releaseInfo.RemasterTitle = request.values["remaster_title"]
        releaseInfo.RemasterYear = request.values["remaster_year"]

        # Other

        if request.values.get("force_upload") is None:
            releaseInfo.JobStartMode = JobStartMode.Manual
        else:
            releaseInfo.JobStartMode = JobStartMode.ManualForced

        if request.values.get("ForceDirectorylessSingleFileTorrent") is not None:
            releaseInfo.SetForceDirectorylessSingleFileTorrent()

        if request.values.get("StartImmediately") is not None:
            releaseInfo.SetStartImmediately()

        releaseInfo.ReleaseNotes = request.values["ReleaseNotes"]
        releaseInfo.SetSubtitles(request.form.getlist("subtitle[]"))
        releaseInfo.IncludedFiles = request.values["IncludedFilesCustomizedList"]
        releaseInfo.DuplicateCheckCanIgnore = int(
            request.values.get("SkipDuplicateCheckingButton", 0)
        )
        releaseInfo.SetOverrideScreenshots(
            request.values.get("OverrideScreenshots") is not None
        )

    @staticmethod
    def __GetPtpOrImdbLink(releaseInfo):
        if releaseInfo.PtpId:
            return "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.PtpId
        if releaseInfo.ImdbId:
            if releaseInfo.IsZeroImdbId():
                return "0"
            return "http://www.imdb.com/title/tt%s/" % releaseInfo.ImdbId

        return ""

    @staticmethod
    def __GetYouTubeLink(releaseInfo):
        if len(releaseInfo.YouTubeId) > 0:
            return "http://www.youtube.com/watch?v=%s" % releaseInfo.YouTubeId

        return ""

    @staticmethod
    def FillDictionaryFromReleaseInfo(job, releaseInfo):
        # For PTP
        job["type"] = releaseInfo.Type
        job["imdb"] = JobCommon.__GetPtpOrImdbLink(releaseInfo)
        job["artists[]"] = releaseInfo.Directors
        job["title"] = releaseInfo.Title
        job["year"] = releaseInfo.Year
        job["genre_tags"] = releaseInfo.Tags.split(", ")
        job["album_desc"] = releaseInfo.MovieDescription
        job["image"] = releaseInfo.CoverArtUrl
        job["trailer"] = JobCommon.__GetYouTubeLink(releaseInfo)

        if releaseInfo.PersonalRip:
            job["PersonalRip"] = "on"

        if releaseInfo.SceneRelease:
            job["scene"] = "on"

        if releaseInfo.IsSpecialRelease():
            job["special"] = "on"

        if releaseInfo.IsTrumpableForNoEnglishSubtitles():
            job["TrumpableForNoEnglishSubtitles"] = "on"
        if releaseInfo.IsTrumpableForHardcodedSubtitles():
            job["TrumpableForHardcodedSubtitles"] = "on"

        job["codec"] = releaseInfo.Codec
        job["container"] = releaseInfo.Container
        job["resolution"] = releaseInfo.ResolutionType
        job["other_resolution"] = releaseInfo.Resolution
        job["source"] = releaseInfo.Source
        job["remaster_title"] = releaseInfo.RemasterTitle
        job["remaster_year"] = releaseInfo.RemasterYear
        job["Screenshots"] = {}
        if releaseInfo.Screenshots:
            for f in json.loads(releaseInfo.Screenshots):
                path = f[0].replace(releaseInfo.UploadTorrentCreatePath, "").strip("/")
                job["Screenshots"][path] = ""
                for s in f[1]:
                    job["Screenshots"][path] += f'<img src="{s}"/>'

        # Other
        job["JobId"] = releaseInfo.Id

        if releaseInfo.JobStartMode == JobStartMode.ManualForced:
            job["force_upload"] = "on"

        if releaseInfo.IsForceDirectorylessSingleFileTorrent():
            job["ForceDirectorylessSingleFileTorrent"] = "on"

        if releaseInfo.IsStartImmediately():
            job["StartImmediately"] = "on"

        job["ReleaseName"] = releaseInfo.ReleaseName
        job["ReleaseNotes"] = releaseInfo.ReleaseNotes

        job["Subtitles"] = releaseInfo.GetSubtitles()
        job["Tags"] = releaseInfo.Tags.split(",")
        job["IncludedFilesCustomizedList"] = releaseInfo.IncludedFiles
        job["SkipDuplicateCheckingButton"] = int(releaseInfo.DuplicateCheckCanIgnore)

        if releaseInfo.OverrideScreenshots:
            job["OverrideScreenshots"] = 1

        if releaseInfo.PtpId:
            if releaseInfo.PtpTorrentId:
                job[
                    "PtpUrl"
                ] = "https://passthepopcorn.me/torrents.php?id=%s&torrentid=%s" % (
                    releaseInfo.PtpId,
                    releaseInfo.PtpTorrentId,
                )
            else:
                job["PtpUrl"] = (
                    "https://passthepopcorn.me/torrents.php?id=%s" % releaseInfo.PtpId
                )
        elif releaseInfo.ImdbId and releaseInfo.ImdbId != 0:
            job["PtpUrl"] = (
                "https://passthepopcorn.me/torrents.php?imdb=%s" % releaseInfo.ImdbId
            )


def MakeIncludedFilesTreeJson(includedFileList):
    class TreeFile:
        def __init__(self, name, includedFileItem):
            self.Name = name
            self.IncludedFileItem = includedFileItem

    class TreeDirectory:
        def __init__(self, name):
            self.Name = name
            self.Directories = []  # Contains TreeDirectory.
            self.Files = []  # Contains TreeFiles.

        # Adds directory if it not exists yet. Maintains sort order.
        def __AddDirectoryInternal(self, name):
            nameLower = name.lower()
            for i in range(len(self.Directories)):
                currentNameLower = self.Directories[i].Name.lower()
                if currentNameLower == nameLower:
                    return self.Directories[i]
                elif currentNameLower > nameLower:
                    newDirectory = TreeDirectory(name)
                    self.Directories.insert(i, newDirectory)
                    return newDirectory

            newDirectory = TreeDirectory(name)
            self.Directories.append(newDirectory)
            return newDirectory

        # Adds file. Maintains sort order.
        def __AddFileInternal(self, name, includedFileItem):
            nameLower = name.lower()
            for i in range(len(self.Files)):
                currentNameLower = self.Files[i].Name.lower()
                if currentNameLower > nameLower:
                    self.Files.insert(i, TreeFile(name, includedFileItem))
                    return

            self.Files.append(TreeFile(name, includedFileItem))

        def AddFile(self, includedFileItem):
            pathComponents = includedFileItem.Name.split("/")
            parent = self
            for i in range(len(pathComponents)):
                pathComponent = pathComponents[i]

                # Last component is the file.
                if i == (len(pathComponents) - 1):
                    parent.__AddFileInternal(pathComponent, includedFileItem)
                else:
                    parent = parent.__AddDirectoryInternal(pathComponent)

        def GetListForJson(self, parentList):
            for directory in self.Directories:
                entry = {"title": directory.Name, "isFolder": True}
                childList = []
                directory.GetListForJson(childList)
                if len(childList) > 0:
                    entry["children"] = childList

                parentList.append(entry)

            for file in self.Files:
                # OriginallySelected and IncludePath are custom properties.
                # http://stackoverflow.com/questions/6012734/dynatree-where-can-i-store-additional-info-in-each-node
                entry = {}
                entry["title"] = file.Name
                entry["select"] = file.IncludedFileItem.IsIncluded()
                entry["OriginallySelected"] = file.IncludedFileItem.IsDefaultIncluded()
                entry["IncludePath"] = file.IncludedFileItem.Name
                parentList.append(entry)

    root = TreeDirectory("")

    for entry in includedFileList.Files:
        root.AddFile(entry)

    list = []
    root.GetListForJson(list)
    return list


@app.route("/ajaxgetincludedfilelist/", methods=["POST"])
@requires_auth
def ajaxGetIncludedFileList():
    includedFileList = IncludedFileList()
    jobId = request.values.get("JobId")
    sourceTorrentFilename = request.values.get("SourceTorrentFilename")
    releaseDownloadPath = request.values.get("ReleaseDownloadPath")
    includedFilesCustomizedList = request.values.get("IncludedFilesCustomizedList")

    if jobId:
        jobId = int(jobId)
        releaseInfo = ReleaseInfo.objects.get(Id=jobId)
        announcementSource = MyGlobals.SourceFactory.GetSource(
            releaseInfo.AnnouncementSourceName
        )
        if announcementSource:
            includedFileList = announcementSource.GetIncludedFileList(releaseInfo)
    elif sourceTorrentFilename:
        sourceTorrentFilename = secure_filename(sourceTorrentFilename)
        sourceTorrentFilename = os.path.join(
            Settings.GetTemporaryPath(), sourceTorrentFilename
        )
        includedFileList.FromTorrent(sourceTorrentFilename)
    elif releaseDownloadPath:
        includedFileList.FromDirectory(releaseDownloadPath)
    else:
        return jsonify(result="ERROR")

    includedFileList.ApplyCustomizationFromJson(includedFilesCustomizedList)

    return jsonify(result="OK", files=MakeIncludedFilesTreeJson(includedFileList))


@app.route("/ajaxgetlatesttorrent/", methods=["GET"])
@requires_auth
def ajaxGetLatestTorrent():
    releaseInfo = ReleaseInfo()
    releaseInfo.Logger = MyGlobals.Logger
    JobCommon.GetPtpOrImdbId(releaseInfo, request.values.get("PtpOrImdbLink"))

    torrentId = 0
    uploadedAgo = ""

    if releaseInfo.ImdbId != "0":
        Ptp.Login()

        movieOnPtpResult = None
        if releaseInfo.PtpId:
            movieOnPtpResult = Ptp.GetMoviePageOnPtp(
                releaseInfo.Logger, releaseInfo.PtpId
            )
        else:
            movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId(
                releaseInfo.Logger, releaseInfo.ImdbId
            )

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

    return jsonify(Result="OK", TorrentId=torrentId, UploadedAgo=uploadedAgo)
