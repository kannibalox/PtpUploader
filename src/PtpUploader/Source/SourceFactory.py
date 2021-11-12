from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.Settings import Settings
from PtpUploader.Source.AlphaRatio import AlphaRatio
from PtpUploader.Source.Cinemageddon import Cinemageddon
from PtpUploader.Source.Cinematik import Cinematik
from PtpUploader.Source.DigitalHive import DigitalHive
from PtpUploader.Source.File import File
from PtpUploader.Source.FunFile import FunFile
from PtpUploader.Source.Gft import Gft
from PtpUploader.Source.HDBits import HDBits
from PtpUploader.Source.HDTorrents import HDTorrents
from PtpUploader.Source.Karagarga import Karagarga
from PtpUploader.Source.Prowlarr import Prowlarr
from PtpUploader.Source.Torrent import Torrent
from PtpUploader.Source.TorrentBytes import TorrentBytes
from PtpUploader.Source.TorrentLeech import TorrentLeech


class SourceFactory:
    def __init__(self):
        self.Sources = {}

        self.__AddSource(File())
        self.__AddSource(Torrent())

        # self.__AddSource(AlphaRatio())
        self.__AddSource(Cinemageddon())
        # self.__AddSource(Cinematik())
        # self.__AddSource(DigitalHive())
        # self.__AddSource(FunFile())
        # self.__AddSource(Gft())
        # self.__AddSource(HDBits())
        # self.__AddSource(HDTorrents())
        self.__AddSource(Karagarga())
        # self.__AddSource(TorrentBytes())
        # self.__AddSource(TorrentLeech())
        self.__AddSource(Prowlarr())

        MyGlobals.Logger.info("Sources initialized.")

    def __AddSource(self, source):
        if source.IsEnabled():
            source.LoadSettings(Settings)
            source.Login()
        self.Sources[source.Name] = source

    def GetSource(self, sourceName):
        # We don't want to throw KeyError exception, so we use get.
        return self.Sources.get(sourceName)

    def GetSourceAndIdByUrl(self, url):
        for key, source in list(self.Sources.items()):
            id = source.GetIdFromUrl(url)
            if len(id) > 0:
                return source, id

        return None, ""
