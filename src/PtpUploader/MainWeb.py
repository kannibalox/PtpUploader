from WebServer.WebServer import WebServer

from Globals import Globals
from PtpUploader import PtpUploader
from Settings import Settings
from Database import InitDb

def Initialize():
	Settings.LoadSettings()
	Globals.InitializeGlobals( Settings.WorkingPath )

def Run():
	print "Starting..."
	InitDb()

	# Do not start the web server if the username or the password is not set.
	webServerThread = None
	if len( Settings.WebServerUsername ) > 0 and len( Settings.WebServerPassword ) > 0:
		webServerThread = WebServer()
		webServerThread.start()

	try:
		PtpUploader.Work()
	except (KeyboardInterrupt, SystemExit):
		pass

	print "Stopping..."
	if webServerThread is not None:
		webServerThread.StopServer()

if __name__ == '__main__':
	Initialize()
	Run()