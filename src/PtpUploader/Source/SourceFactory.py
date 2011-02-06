from Cinemageddon import Cinemageddon
from Gft import Gft
from Manual import Manual
from Settings import Settings

class SourceFactory:
	def __init__(self):
		self.Sources = {}
		
		if len( Settings.CinemageddonUserName ) > 0 and len( Settings.CinemageddonPassword ) > 0:
			Cinemageddon.Login()
			self.__AddSource( Cinemageddon() )

		if len( Settings.GftUserName ) > 0 and len( Settings.GftPassword ) > 0:
			Gft.Login()
			self.__AddSource( Gft() )

		self.__AddSource( Manual() )

	def __AddSource(self, source):
		self.Sources[ source.Name ] = source
			
	def GetSource(self, sourceName):
		# We don't want to throw KeyError exception, so we use get.
		return self.Sources.get( sourceName ) 