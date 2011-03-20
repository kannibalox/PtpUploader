from Job.JobManager import JobManager

from Globals import Globals
from PtpUploaderException import *

import threading
import time

class PtpUploader:
	TheJobManager = None
	WaitEvent = threading.Event()
	
	@staticmethod
	def __GetLoggerFromException(exception):
		if hasattr( exception, "Logger" ):
			return exception.Logger
		else:
			return Globals.Logger

	@staticmethod
	def AddToDatabaseQueue(releaseInfoId):
		PtpUploader.TheJobManager.AddToDatabaseQueue( releaseInfoId )
		PtpUploader.WaitEvent.set()

	@staticmethod
	def Work():
		Globals.Logger.info( "Entering into the main loop." )
		PtpUploader.TheJobManager = JobManager()

		while True:
			try:
				if not PtpUploader.TheJobManager.ProcessJobs():
					# Sleep 30 seconds (or less if there is an event), if there was no work to do.
					PtpUploader.WaitEvent.clear()
					PtpUploader.WaitEvent.wait( 30 )
			except (KeyboardInterrupt, SystemExit):
				raise
			except PtpUploaderInvalidLoginException, e:
				PtpUploader.__GetLoggerFromException( e ).exception( "Aborting." )
				break
			except Exception, e:
				PtpUploader.__GetLoggerFromException( e ).exception( "Caught exception in the main loop. Trying to continue." )