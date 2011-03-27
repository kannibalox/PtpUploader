# The __init__.py files are required to make Python treat the directories as containing packages
# http://docs.python.org/tutorial/modules.html

from flask import Flask

app = Flask( __name__ )

import WebServer.EditJob
import WebServer.ServerMain
import WebServer.Upload