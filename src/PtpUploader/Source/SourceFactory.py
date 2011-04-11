from Source.Cinemageddon import Cinemageddon
from Source.File import File
from Source.Gft import Gft
from Source.Torrent import Torrent
from Source.TorrentLeech import TorrentLeech

from MyGlobals import MyGlobals
from Settings import Settings

class SourceFactory:
	def __init__(self):
		self.Sources = {}
		
		if Cinemageddon.IsEnabled():
			Cinemageddon.Login()
		self.__AddSource( Cinemageddon() )

		if Gft.IsEnabled():
			Gft.Login()
		self.__AddSource( Gft() )

		if TorrentLeech.IsEnabled():
			TorrentLeech.Login()
		self.__AddSource( TorrentLeech() )

		self.__AddSource( File() )
		self.__AddSource( Torrent() )

		MyGlobals.Logger.info( "Sources initialized." )

	def __AddSource(self, source):
		self.Sources[ source.Name ] = source

	def GetSource(self, sourceName):
		# We don't want to throw KeyError exception, so we use get.
		return self.Sources.get( sourceName ) 

	def GetSourceAndIdByUrl(self, url):
		for key, source in self.Sources.iteritems():
			id = source.GetIdFromUrl( url )
			if len( id ) > 0:
				return source, id
		
		return None, ""