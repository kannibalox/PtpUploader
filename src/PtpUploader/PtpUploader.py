from Job.JobManager import JobManager

from MyGlobals import MyGlobals
from PtpUploaderException import *

import threading
import time

class PtpUploader:
	def __init__(self):
		self.WaitEvent = threading.Event()
		self.TheJobManager = JobManager()
	
	@staticmethod
	def __GetLoggerFromException(exception):
		if hasattr( exception, "Logger" ):
			return exception.Logger
		else:
			return MyGlobals.Logger

	def AddToDatabaseQueue(self, releaseInfoId):
		self.TheJobManager.AddToDatabaseQueue( releaseInfoId )
		self.WaitEvent.set()

	def Work(self):
		MyGlobals.Logger.info( "Entering into the main loop." )

		while True:
			try:
				if not self.TheJobManager.ProcessJobs():
					# Sleep 30 seconds (or less if there is an event), if there was no work to do.
					self.WaitEvent.clear()
					self.WaitEvent.wait( 30 )
			except (KeyboardInterrupt, SystemExit):
				raise
			except PtpUploaderInvalidLoginException, e:
				self.__GetLoggerFromException( e ).exception( "Aborting." )
				break
			except Exception, e:
				self.__GetLoggerFromException( e ).exception( "Caught exception in the main loop. Trying to continue." )