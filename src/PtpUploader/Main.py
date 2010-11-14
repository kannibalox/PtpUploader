from Globals import Globals
from Ptp import Ptp
from PtpUploader import PtpUploader
from Settings import Settings

from PtpUploadInfo import PtpUploadInfo

def Main():
	Settings.LoadSettings()
	Globals.InitializeGlobals( Settings.WorkingPath )
	Globals.Logger.info( "PtpUploader v0.1 by TnS" )

	Ptp.Login()

	ptpUploader = PtpUploader()
	ptpUploader.Work()

if __name__ == '__main__':
	Main()