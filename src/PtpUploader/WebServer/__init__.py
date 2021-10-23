# The __init__.py files are required to make Python treat the directories as containing packages
# http://docs.python.org/tutorial/modules.html

from flask import request, url_for

from PtpUploader.Database import Database
from PtpUploader.WebServer.MyFlask import MyFlask

app = MyFlask(__name__)

from PtpUploader.WebServer import (DeleteJob, EditJob, ExternalCreateJob,
                                   JobCommon, Jobs, MovieAvailabilityCheck,
                                   ServerMain, Upload, UploadFile)


# "Because the only difference from one URL to the other is the page part in it, we can provide a little helper function that wraps url_for to generate a new URL to the same endpoint with a different page:"
# Simple Pagination by Armin Ronacher
# http://flask.pocoo.org/snippets/44/
def url_for_other_page(page):
    args = request.view_args.copy()
    args["page"] = page
    return url_for(request.endpoint, **args)


app.jinja_env.globals["url_for_other_page"] = url_for_other_page
