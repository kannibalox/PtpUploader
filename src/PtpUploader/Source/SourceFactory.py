from Source.Cinemageddon import Cinemageddon
from Source.Cinematik import Cinematik
from Source.File import File
from Source.Gft import Gft
from Source.Karagarga import Karagarga
from Source.SceneAccess import SceneAccess
from Source.Torrent import Torrent
from Source.TorrentLeech import TorrentLeech

from MyGlobals import MyGlobals
from Settings import Settings

class SourceFactory:
	def __init__(self):
		self.Sources = {}

		self.__AddSource( File() )
		self.__AddSource( Torrent() )
		
		self.__AddSource( Cinemageddon() )
		self.__AddSource( Cinematik() )
		self.__AddSource( Gft() )
		self.__AddSource( Karagarga() )
		self.__AddSource( TorrentLeech() )

		sceneAccess = SceneAccess()
		self.__AddSource( sceneAccess )
		if sceneAccess.IsEnabled():
			sceneAccess.InviteToIrc()

		MyGlobals.Logger.info( "Sources initialized." )

	def __AddSource(self, source):
		if source.IsEnabled():
			source.Login()
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