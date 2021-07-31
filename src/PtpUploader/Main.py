from .Source.SourceFactory import SourceFactory
from .WebServer.MyWebServer import MyWebServer

from .MyGlobals import MyGlobals
from .PtpUploader import PtpUploader
from .Settings import Settings
from .Database import InitDb


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

    MyGlobals.PtpUploader = PtpUploader()

    # Do not start the web server if the username or the password is not set.
    webServerThread = None
    if len(Settings.WebServerUsername) > 0 and len(Settings.WebServerPassword) > 0:
        webServerThread = MyWebServer()
        webServerThread.start()

    MyGlobals.PtpUploader.Work()

    if webServerThread is not None:
        webServerThread.StopServer()


def Main():
    if Initialize():
        Run()


if __name__ == "__main__":
    Main()
