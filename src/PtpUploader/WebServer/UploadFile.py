from . import app
from .Authentication import requires_auth

from ..NfoParser import NfoParser
from ..Settings import Settings

from flask import jsonify, request

import os
import urllib.request, urllib.parse, urllib.error

# Needed for jQuery File Tree.
@app.route("/ajaxgetdirectorylist/", methods=["POST"])
@requires_auth
def ajaxGetDirectoryList():
    r = ['<ul class="jqueryFileTree" style="display: none;">']
    try:
        response = ['<ul class="jqueryFileTree" style="display: none;">']

        path = urllib.parse.unquote(request.values["dir"])
        if os.path.isfile(path):
            # If it is file then start browsing from its parent directory.
            path = os.path.dirname(path)
        elif not os.path.isdir(path):
            path = Settings.WebServerFileTreeInitRoot

        directories = []
        files = []

        for fileName in os.listdir(path):
            currentPath = os.path.join(path, fileName)
            item = currentPath, fileName  # Add as a tuple.
            if os.path.isdir(currentPath):
                directories.append(item)
            else:
                files.append(item)

        directories.sort()
        files.sort()

        for directory in directories:
            currentPath, fileName = directory
            response.append(
                '<li class="directory collapsed"><a href="#" rel="%s/">%s</a></li>'
                % (currentPath, fileName)
            )

        for file in files:
            currentPath, fileName = file
            extension = os.path.splitext(fileName)[1][1:]  # get .ext and remove dot
            response.append(
                '<li class="file ext_%s"><a href="#" rel="%s">%s</a></li>'
                % (extension, currentPath, fileName)
            )
    except Exception as e:
        response.append("Could not load directory: %s" % str(e))
    response.append("</ul>")
    return "".join(response)


@app.route("/ajaxgetinfoforfileupload/", methods=["POST"])
@requires_auth
def ajaxGetInfoForFileUpload():
    path = request.values.get("path")
    # file is not None even there is no file specified, but checking file as a boolean is OK. (As shown in the Flask example.)
    if not path:
        return jsonify(result="ERROR", message="Missing request parameter: path.")

    releaseName = ""
    imdbId = ""

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
            nfo = NfoParser.ReadNfoFileToUnicode(nfoPath)
            imdbId = NfoParser.GetImdbId(nfo)
    else:
        message = "Path '%s' does not exist." % path
        return jsonify(result="ERROR", message=message)

    imdbUrl = ""
    if len(imdbId) > 0:
        imdbUrl = "http://www.imdb.com/title/tt%s/" % imdbId

    return jsonify(result="OK", releaseName=releaseName, imdbUrl=imdbUrl)


def UploadFile(releaseInfo, request):
    path = request.values.get("existingfile_input")
    if path is None:
        return False

    if not os.path.exists(path):
        return False

    releaseInfo.AnnouncementSourceName = "file"
    releaseInfo.SetReleaseDownloadPath(path)

    return True
