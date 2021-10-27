import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PtpUploader.Settings")
django.setup()

from PtpUploader.Database import InitDb
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderRunner import PtpUploaderRunner
from PtpUploader.Settings import Settings
from PtpUploader.Source.SourceFactory import SourceFactory
from PtpUploader.WebServer.MyWebServer import MyWebServer
from PtpUploader.Job import Supervisor

def Initialize():
    Settings.LoadSettings()

    MyGlobals.InitializeGlobals(Settings.WorkingPath)

    if not Settings.VerifyPaths():
        return False

    return True


def Run():
    InitDb()

    try:
        MyGlobals.SourceFactory = SourceFactory()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        MyGlobals.Logger.exception("Got exception while creating SourceFactory()")
        raise

    MyGlobals.PtpUploader = Supervisor.JobSupervisor()

    # Do not start the web server if the username or the password is not set.
    webServerThread = None
    if len(Settings.WebServerUsername) > 0 and len(Settings.WebServerPassword) > 0:
        webServerThread = MyWebServer()
        webServerThread.start()

    MyGlobals.PtpUploader.run()

    if webServerThread is not None:
        webServerThread.StopServer()


def Main():
    if Initialize():

        Run()


if __name__ == "__main__":
    Main()
