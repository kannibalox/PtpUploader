import cookielib;
import datetime;
import logging;
import os;
import sys;

class Globals:
	@staticmethod
	def InitializeGlobals(workingPath):
		Globals.InitializeLogger( workingPath );
		
		Globals.CookieJar = cookielib.CookieJar();
	
	# workingPath from Settings.WorkingPath.
	@staticmethod
	def InitializeLogger(workingPath):
		logDirPath = os.path.join( workingPath, "log" );
		if not os.path.isdir( logDirPath ):
			os.makedirs( logDirPath );
		
		logDate = datetime.datetime.now().strftime( "%Y.%m.%d. - %H_%M_%S" );
		logPath = os.path.join( logDirPath, logDate + ".txt" );
		
		Globals.Logger = logging.getLogger( 'PtpUploader' )
		
		# file
		handler = logging.FileHandler( logPath )
		formatter = logging.Formatter ( "[%(asctime)s] %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S" );
		handler.setFormatter( formatter );
		Globals.Logger.addHandler( handler );
		
		# stdout
		console = logging.StreamHandler( sys.stdout );
		console.setFormatter( formatter );
		Globals.Logger.addHandler( console );
		
		Globals.Logger.setLevel( logging.INFO );