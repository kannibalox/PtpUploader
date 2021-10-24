import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from flask import jsonify, request

from PtpUploader.NfoParser import NfoParser
from PtpUploader.Settings import Settings
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth


@app.route("/ajax/localdir/")
@requires_auth
def ajaxGetDirList():
    d: Path
    if "dir" not in request.args:
        d = Path(Settings.WebServerFileTreeInitRoot)
    else:
        d = Path(request.args["dir"])
    val = []
    for child in sorted(d.iterdir()):
        c = {"title": child.name, "key": str(child)}
        if child.is_dir():
            c["folder"] = True
            c["lazy"] = True
        elif child.suffix.lower() in [".mkv", ".avi", ".mp4", ".vob", ".ifo", ".bup"]:
            c["icon"] = "film"
        val.append(c)
    return jsonify(val)


@app.route("/ajaxgetinfoforfileupload/", methods=["POST"])
@requires_auth
def ajaxGetInfoForFileUpload():
    path: str = request.values.get("path")
    # file is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.)
    if not path:
        return jsonify(result="ERROR", message="Missing request parameter: path.")

    releaseName: str = ""
    imdbId: str = ""

    if os.path.isdir(path):
        # Make sure that path doesn't ends with a trailing slash or else os.path.split would return with wrong values.
        path = path.rstrip("\\/")

        # Release name will be the directory's name. Eg. it will be "anything" for "/something/anything"
        basePath, releaseName = os.path.split(path)

        # Try to read the NFO.
        nfo = NfoParser.FindAndReadNfoFileToUnicode(path)
        imdbId = NfoParser.GetImdbId(nfo)
    elif os.path.isfile(path):
        # Release name will be the file's name without extension.
        basePath, releaseName = os.path.split(path)
        releaseName, extension = os.path.splitext(releaseName)

        # Try to read the NFO.
        nfoPath = os.path.join(basePath, releaseName) + ".nfo"
        if os.path.isfile(nfoPath):
            nfo = NfoParser.ReadNfo(nfoPath)
            imdbId = NfoParser.GetImdbId(nfo)
    else:
        message = "Path '%s' does not exist." % path
        return jsonify(result="ERROR", message=message)

    imdbUrl: str = ""
    if imdbId:
        imdbUrl = "http://www.imdb.com/title/tt%s/" % imdbId

    return jsonify(result="OK", releaseName=releaseName, imdbUrl=imdbUrl)


def UploadFile(releaseInfo, request):
    path = request.values.get("existingfile_input")
    if path is None:
        return False

    if not os.path.exists(path):
        return False

    releaseInfo.AnnouncementSourceName = "file"
    releaseInfo.ReleaseDownloadPath = path

    return True
