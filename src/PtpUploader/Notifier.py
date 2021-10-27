import configparser
import os
import sys

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader import Ptp
from PtpUploader.Settings import Settings


def LoadNotifierSettings():
    configParser = configparser.ConfigParser()
    configParser.optionxform = str  # Make option names case sensitive.

    # Load Notifier.ini from the same directory where PtpUploader is.
    settingsDirectory, moduleFilename = os.path.split(
        __file__
    )  # __file__ contains the full path of the current running module
    settingsPath = os.path.join(settingsDirectory, "Notifier.ini")
    configParser.read(settingsPath)

    return configParser.get("Settings", "UserId")


def Notify(releaseName, uploadedTorrentUrl):
    logger = MyGlobals.Logger

    userId = LoadNotifierSettings()
    userId = userId.strip()
    if not userId.isdigit():
        return

    Ptp.Login()
    subject = "[PtpUploader] %s" % releaseName
    message = (
        "This is an automatic notification about a new [url=%s]upload[/url]."
        % uploadedTorrentUrl
    )
    Ptp.SendPrivateMessage(userId, subject, message)


if __name__ == "__main__":
    Settings.LoadSettings()
    MyGlobals.InitializeGlobals(Settings.WorkingPath)

    if len(sys.argv) == 3:
        Notify(sys.argv[1], sys.argv[2])
