from Source.SourceFactory import SourceFactory
from WebServer.MyWebServer import MyWebServer

from MyGlobals import MyGlobals
from PtpUploader import PtpUploader
from Settings import Settings
from Database import InitDb

def Initialize():
	Settings.LoadSettings()
	MyGlobals.InitializeGlobals( Settings.WorkingPath )

def Run():
	InitDb()

	MyGlobals.SourceFactory = SourceFactory()
	MyGlobals.PtpUploader = PtpUploader()

	# Do not start the web server if the username or the password is not set.
	webServerThread = None
	if len( Settings.WebServerUsername ) > 0 and len( Settings.WebServerPassword ) > 0:
		webServerThread = MyWebServer()
		webServerThread.start()

	MyGlobals.PtpUploader.Work()

	if webServerThread is not None:
		webServerThread.StopServer()

if __name__ == '__main__':
	Initialize()
	Run()