from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.Settings import Settings
from PtpUploader.Source.Cinemageddon import Cinemageddon
from PtpUploader.Source.File import File
from PtpUploader.Source.Karagarga import Karagarga
from PtpUploader.Source.Prowlarr import Prowlarr
from PtpUploader.Source.Torrent import Torrent


class SourceFactory:
    def __init__(self):
        self.Sources = {}

        self.__AddSource(File())
        self.__AddSource(Torrent())

        self.__AddSource(Cinemageddon())
        self.__AddSource(Karagarga())
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
        for _, source in list(self.Sources.items()):
            source_id = source.GetIdFromUrl(url)
            if source_id:
                return source, source_id

        return None, ""
