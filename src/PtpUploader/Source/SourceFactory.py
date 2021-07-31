from .AlphaRatio import AlphaRatio
from .Cinemageddon import Cinemageddon
from .Cinematik import Cinematik
from .DigitalHive import DigitalHive
from .File import File
from .FunFile import FunFile
from .Gft import Gft
from .HDBits import HDBits
from .HDTorrents import HDTorrents
from .Karagarga import Karagarga
from .Torrent import Torrent
from .TorrentBytes import TorrentBytes
from .TorrentLeech import TorrentLeech

from ..MyGlobals import MyGlobals
from ..Settings import Settings


class SourceFactory:
    def __init__(self):
        self.Sources = {}

        self.__AddSource(File())
        self.__AddSource(Torrent())

        self.__AddSource(AlphaRatio())
        self.__AddSource(Cinemageddon())
        self.__AddSource(Cinematik())
        self.__AddSource(DigitalHive())
        self.__AddSource(FunFile())
        self.__AddSource(Gft())
        self.__AddSource(HDBits())
        self.__AddSource(HDTorrents())
        self.__AddSource(Karagarga())
        self.__AddSource(TorrentBytes())
        self.__AddSource(TorrentLeech())

        MyGlobals.Logger.info("Sources initialized.")

    def __AddSource(self, source):
        source.LoadSettings(Settings)
        if source.IsEnabled():
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
