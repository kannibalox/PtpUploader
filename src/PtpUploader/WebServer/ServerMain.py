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

from flask import redirect, request, url_for
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
    releaseInfo = ReleaseInfo.objects.get(Id=jobId)

    logFilePath = releaseInfo.GetLogFilePath()
    log_msg = ""

    if os.path.isfile(logFilePath):
        with open(logFilePath, "r") as fh:
            log_msg = fh.read()
    else:
        log_msg = "Log file '%s' doesn't exists!" % logFilePath

    log_msg = log_msg.replace("\n", r"<br>")

    return log_msg


@app.route("/quit")
@requires_auth
def quit():
    MyGlobals.PtpUploader.add_message(PtpUploaderMessageQuit())

    func = request.environ.get("werkzeug.server.shutdown")
    func()

    return "Quitting."
