from Globals import Globals
from Ptp import Ptp
from PtpUploader import PtpUploader
from ReleaseInfoMaker import ReleaseInfoMaker
from Settings import Settings

import sys;

def Initialize():
	Settings.LoadSettings()
	Globals.InitializeGlobals( Settings.WorkingPath )
	Globals.Logger.info( "PtpUploader v0.2 by TnS" )
	Globals.Logger.info( "Usage:" )
	Globals.Logger.info( "Main.py without parameterss starts the bot listening for announcements." )
	Globals.Logger.info( "\"Main.py <target directory or filename>\" creates the release description and starts seeding the torrent." )
	Globals.Logger.info( "\"Main.py --notorrent <target directory or filename>\" creates the release description." )
	Globals.Logger.info( "" )

def MainBotMode():
	Ptp.Login()
	ptpUploader = PtpUploader()
	ptpUploader.Work()

def MainReleaseInfoMode():
	if len( sys.argv ) == 2:
		releaseInfoMaker = ReleaseInfoMaker( sys.argv[ 1 ] )
		releaseInfoMaker.MakeReleaseInfo( createTorrent = True )
	elif len( sys.argv ) == 3 and sys.argv[ 1 ] == "--notorrent":
		releaseInfoMaker = ReleaseInfoMaker( sys.argv[ 2 ] )
		releaseInfoMaker.MakeReleaseInfo( createTorrent = False )

if __name__ == '__main__':
	Initialize()

	if len( sys.argv ) > 1:
		MainReleaseInfoMode()
	else:
		MainBotMode()