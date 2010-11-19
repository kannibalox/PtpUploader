from Globals import Globals
from Ptp import Ptp
from PtpUploader import PtpUploader
from ReleaseInfoMaker import ReleaseInfoMaker
from Settings import Settings

import sys;

def Initialize():
	Settings.LoadSettings()
	Globals.InitializeGlobals( Settings.WorkingPath )
	Globals.Logger.info( "PtpUploader v0.1 by TnS" )

def MainBotMode():
	Ptp.Login()
	ptpUploader = PtpUploader()
	ptpUploader.Work()

def MainReleaseInfoMode(path):
	ReleaseInfoMaker.MakeReleaseInfo( path )

if __name__ == '__main__':
	Initialize()
	
	if len( sys.argv ) == 2: 
		MainReleaseInfoMode( sys.argv[ 1 ] )
	else:
		MainBotMode()