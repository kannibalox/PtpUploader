import re

from flask import render_template, request

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader import Ptp
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth


def GetPtpIdIfExists(imdbId, releaseInfo, anyFormat):
    movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId(MyGlobals.Logger, imdbId)
    exists = False

    if anyFormat:
        exists = movieOnPtpResult.IsMoviePageExists()
    else:
        exists = movieOnPtpResult.IsReleaseExists(releaseInfo) is not None

    if exists:
        return movieOnPtpResult.PtpId
    else:
        return None


@app.route("/movieAvailabilityCheck/", methods=["GET", "POST"])
@requires_auth
def movieAvailabilityCheck():
    if request.method == "POST":
        Ptp.Login()

        releaseInfo = ReleaseInfo()
        anyFormat = False

        format = request.values["format"]
        if format == "Any":
            anyFormat = True
        elif format == "SD XviD":
            releaseInfo.Codec = "XviD"
            releaseInfo.Container = "AVI"
            releaseInfo.ResolutionType = "Other"
            releaseInfo.Source = "DVD"
        elif format == "SD x264":
            releaseInfo.Codec = "x264"
            releaseInfo.Container = "MKV"
            releaseInfo.ResolutionType = "Other"
            releaseInfo.Source = "DVD"
        elif format == "720p":
            releaseInfo.Codec = "x264"
            releaseInfo.Container = "MKV"
            releaseInfo.ResolutionType = "720p"
            releaseInfo.Source = "Blu-ray"
        elif format == "1080p":
            releaseInfo.Codec = "x264"
            releaseInfo.Container = "MKV"
            releaseInfo.ResolutionType = "1080p"
            releaseInfo.Source = "Blu-ray"
        elif format == "4K":
            releaseInfo.Codec = "x264"
            releaseInfo.Container = "MKV"
            releaseInfo.ResolutionType = "4K"
            releaseInfo.Source = "Blu-ray"
        else:
            return "Unknown format!"

        imdbIds = request.values["imdb"]

        resultHtml = ""

        matches = re.findall(r"imdb.com/title/tt(\d+)", imdbIds)
        for match in matches:
            ptpId = GetPtpIdIfExists(match, releaseInfo, anyFormat)

            if ptpId is None:
                resultHtml += (
                    """<a href="http://www.imdb.com/title/tt%s">%s</a> - NOT ON PTP</br>"""
                    % (match, match)
                )
            else:
                resultHtml += (
                    """<a href="http://www.imdb.com/title/tt%s">%s</a> - <a href="https://passthepopcorn.me/torrents.php?id=%s">PTP</a></br>"""
                    % (match, match, ptpId)
                )

        return resultHtml

    return render_template("movieAvailabilityCheck.html")
