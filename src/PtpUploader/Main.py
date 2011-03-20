from WebServer.MyWebServer import MyWebServer

from MyGlobals import MyGlobals
from PtpUploader import PtpUploader
from Settings import Settings
from Database import InitDb

def Initialize():
	Settings.LoadSettings()
	MyGlobals.InitializeGlobals( Settings.WorkingPath )

def Run():
	print "Starting..."
	InitDb()

	MyGlobals.PtpUploader = PtpUploader()

	# Do not start the web server if the username or the password is not set.
	webServerThread = None
	if len( Settings.WebServerUsername ) > 0 and len( Settings.WebServerPassword ) > 0:
		webServerThread = MyWebServer()
		webServerThread.start()

	try:
		MyGlobals.PtpUploader.Work()
	except (KeyboardInterrupt, SystemExit):
		pass

	print "Stopping..."
	if webServerThread is not None:
		webServerThread.StopServer()

if __name__ == '__main__':
	Initialize()
	Run()