"""

TODO:

File selector:
	- jQuery File Tree -- http://abeautifulsite.net/blog/2008/03/jquery-file-tree/
	- jfiletree -- http://code.google.com/p/jfiletree/
	- tree
		- http://code.google.com/p/dynatree/
		- http://www.jstree.com/ -- with json data source

jQuery File Upload
https://github.com/blueimp/jQuery-File-Upload/

"""

import os

from flask import redirect, render_template, request, url_for

from PtpUploader.Database import Database
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderMessage import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.WebServer import app
from PtpUploader.WebServer.Authentication import requires_auth


@app.route("/")
@requires_auth
def index():
    return redirect(url_for("jobs"))


@app.route("/job/<int:jobId>/log/")
@requires_auth
def log(jobId):
    releaseInfo = ReleaseInfo.objects.get(Id = jobId)

    logFilePath = releaseInfo.GetLogFilePath()
    log = ""

    if os.path.isfile(logFilePath):
        file = open(logFilePath)
        log = file.read()
        file.close()
    else:
        log = "Log file '%s' doesn't exists!" % logFilePath

    log = log.replace("\n", r"<br>")

    return log


@app.route("/quit")
@requires_auth
def quit():
    MyGlobals.PtpUploader.AddMessage(PtpUploaderMessageQuit())

    func = request.environ.get("werkzeug.server.shutdown")
    func()

    return "Quitting."
