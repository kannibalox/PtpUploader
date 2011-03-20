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

	webServerThread = WebServer()
	webServerThread.start()

	try:
		PtpUploader.Work()
	except (KeyboardInterrupt, SystemExit):
		pass

	print "Stopping..."
	webServerThread.StopServer()

if __name__ == '__main__':
	Initialize()
	Run()