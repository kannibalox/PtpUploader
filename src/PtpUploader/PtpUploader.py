from .Job.WorkerThread import WorkerThread

from .MyGlobals import MyGlobals
from .PtpUploaderMessage import *

import queue
import threading

class PtpUploader:
	def __init__(self):
		self.WaitEvent = threading.Event()
		self.StopRequested = False
		self.MessageQueue = queue.Queue() # Contains class instances from PtpUploaderMessage.
		self.WorkerThread = WorkerThread()

	def AddMessage(self, message):
		self.MessageQueue.put( message )
		self.WaitEvent.set()
		
	def __ProcessMessages(self):
		while not self.MessageQueue.empty():
			message = self.MessageQueue.get()
			if isinstance( message, PtpUploaderMessageNewAnnouncementFile ):
				self.WorkerThread.RequestHandlingOfNewAnnouncementFile( message.AnnouncementFilePath )
			elif isinstance( message, PtpUploaderMessageStartJob ):
				self.WorkerThread.RequestStartJob( message.ReleaseInfoId )
			elif isinstance( message, PtpUploaderMessageStopJob ):
				self.WorkerThread.RequestStopJob( message.ReleaseInfoId )
			elif isinstance( message, PtpUploaderMessageQuit ):
				self.StopRequested = True

	def __MessageLoop(self):
		MyGlobals.Logger.info( "Entering into message loop." )

		while not self.StopRequested:
			# If there is no timeout for the wait call then KeyboardInterrupt exception is never sent. 
			# http://stackoverflow.com/questions/1408356/keyboard-interrupts-with-pythons-multiprocessing-pool/1408476#1408476
			# (We don't need the timeout.)
			self.WaitEvent.wait( 60 ) # 60 seconds.
			self.WaitEvent.clear()
			self.__ProcessMessages()

	def Work(self):
		self.WorkerThread.StartWorkerThread()

		try:
			self.__MessageLoop()
		except (KeyboardInterrupt, SystemExit):
			MyGlobals.Logger.info( "Got keyboard interrupt or system exit exception." )
			
		self.WorkerThread.StopWorkerThread()