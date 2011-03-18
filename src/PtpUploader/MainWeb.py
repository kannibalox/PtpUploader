from WebServer.ServerMain import app

from Globals import Globals
from PtpUploader import PtpUploader
from Settings import Settings
from Database import Database, InitDb

from threading import Thread

@app.after_request
def ShutdownSession(response):
    Database.DbSession.remove()
    return response

class BotThread(Thread):
	def __init__(self):
		Thread.__init__( self, name = "BotThread" )

	def run(self):
		PtpUploader.Work()
		
def StartWebServer():
	InitDb()
	app.config[ "DEBUG" ] = True
	
	host, separator, port = Settings.WebServerAddress.rpartition( ":" )
	if len( host ) <= 0:
		host = "127.0.0.1"
	
	if len( port ) > 0:
		port = int( port )
	else:
		port = 5000
	
	app.run( host = host, port = port, use_reloader = False )

if __name__ == '__main__':
	Settings.LoadSettings()
	Globals.InitializeGlobals( Settings.WorkingPath )

	botThread = BotThread()
	botThread.start()

	StartWebServer()
	
	botThread.join()