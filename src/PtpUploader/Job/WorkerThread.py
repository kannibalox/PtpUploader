from Job.JobManager import JobManager

from MyGlobals import MyGlobals
from PtpUploaderException import *

import sqlalchemy.exc

import threading

class WorkerThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__( self, name = "WorkerThread" )
		self.Lock = threading.RLock()
		self.WaitEvent = threading.Event()
		self.StopRequested = False
		self.JobPhase = None
		self.JobManager = None

	def StartWorkerThread(self):
		MyGlobals.Logger.info( "Starting worker thread." )

		self.start()

	def StopWorkerThread(self):
		MyGlobals.Logger.info( "Stopping worker thread." )
		
		self.StopRequested = True
		self.RequestStopJob( -1 ) # This sets the WaitEvent, there is no need set it again.
		self.join()
		
	def RequestStartJob(self, releaseInfoId):
		self.JobManager.StartJob( releaseInfoId )
		self.WaitEvent.set()

	def RequestStopJob(self, releaseInfoId):
		self.Lock.acquire()		

		try:
			self.JobManager.StopJob( releaseInfoId )
			if ( self.JobPhase is not None ) and ( self.JobPhase.JobManagerItem.ReleaseInfoId == releaseInfoId or releaseInfoId == -1 ):
				self.JobPhase.JobManagerItem.StopRequested = True
		finally:
			self.Lock.release()

		self.WaitEvent.set()

	def __ProcessJobPhase(self):
		jobPhase = None

		self.Lock.acquire()		

		try:
			# If GetJobPhaseToProcess is not in lock block then this could happen:
			# 1. jobPhase = self.JobManager.GetJobPhaseToProcess()
			# 2. RequestStopJob acquires to lock
			# 3. RequestStopJob sees that the job is no longer in the pending list and not yet in self.JobPhase
			# 4. RequestStopJob releases the lock
			# 5. self.JobPhase = jobPhase
			# 6. Job avoided cancellation.
			
			jobPhase = self.JobManager.GetJobPhaseToProcess()
			self.JobPhase = jobPhase
			if jobPhase is None:
				return False
		finally:
			self.Lock.release()

		# We can't lock on this because stopping a running job wouldn't be possible that way.
		jobPhase = jobPhase.Work()

		self.Lock.acquire()		

		try:
			self.JobPhase = None
		finally:
			self.Lock.release()

		return True

	@staticmethod
	def __GetLoggerFromException(exception):
		if hasattr( exception, "Logger" ):
			return exception.Logger
		else:
			return MyGlobals.Logger

	def __RunInternal(self):
		try:
			if not self.__ProcessJobPhase():
				# Sleep 30 seconds (or less if there is an event), if there was no work to do.
				# Sleeping is needed to not to flood the AnnouncementWatcher and Rtorrent with continous requests.
				self.WaitEvent.wait( 30 )
				self.WaitEvent.clear()
		except ( KeyboardInterrupt, SystemExit ):
			raise
		except PtpUploaderInvalidLoginException, e:
			WorkerThread.__GetLoggerFromException( e ).exception( "Caught invalid login exception in the worker thread loop. Aborting." )
			raise
		except PtpUploaderException, e:
			WorkerThread.__GetLoggerFromException( e ).warning( "%s (PtpUploaderException)" % unicode( e ) )
		except sqlalchemy.exc.SQLAlchemyError, e:
			# "InvalidRequestError: This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback()."
			# If this happens, we can't do anything, all database operation would fail after this and would fill the log file.
			WorkerThread.__GetLoggerFromException( e ).exception( "Caught SQLAlchemy exception. Aborting." )
			raise
		except Exception, e:
			WorkerThread.__GetLoggerFromException( e ).exception( "Caught exception in the worker thread loop. Trying to continue." )

	def run(self):
		# Create JobManager from this thread.
		self.JobManager = JobManager()

		while not self.StopRequested:
			self.__RunInternal()