from Globals import Globals
from Ptp import Ptp
from PtpUploader import PtpUploader
from Settings import Settings

def Initialize():
	Settings.LoadSettings()
	Globals.InitializeGlobals( Settings.WorkingPath )

def MainBotMode():
	Ptp.Login()
	ptpUploader = PtpUploader()
	ptpUploader.Work()

if __name__ == '__main__':
	Initialize()
	MainBotMode()