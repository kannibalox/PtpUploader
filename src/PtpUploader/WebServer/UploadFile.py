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


def UploadFile(releaseInfo, request):
    path = request.values.get("existingfile_input")
    if path is None:
        return False

    if not os.path.exists(path):
        return False

    releaseInfo.AnnouncementSourceName = "file"
    releaseInfo.ReleaseDownloadPath = path
    releaseInfo.ReleaseName = Path(path).stem

    return True
