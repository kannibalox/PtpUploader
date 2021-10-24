import threading

from PtpUploader.AnnouncementDirectoryWatcher import AnnouncementDirectoryWatcher
from PtpUploader.Job.JobManager import JobManager
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import *


class WorkerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, name="WorkerThread")
        self.Lock = threading.RLock()
        self.WaitEvent = threading.Event()
        self.StopRequested = False
        self.JobPhase = None
        self.JobManager = None
        self.AnnouncementDirectoryWatcher = AnnouncementDirectoryWatcher()

    def StartWorkerThread(self):
        MyGlobals.Logger.info("Starting worker thread.")

        self.start()

    def StopWorkerThread(self):
        self.AnnouncementDirectoryWatcher.StopWatching()

        MyGlobals.Logger.info("Stopping worker thread.")
        self.StopRequested = True
        self.RequestStopJob(
            -1
        )  # This sets the WaitEvent, there is no need set it again.
        self.join()

    def RequestStartJob(self, releaseInfoId):
        self.JobManager.StartJob(releaseInfoId)
        self.WaitEvent.set()

    def RequestStopJob(self, releaseInfoId):
        with self.Lock:
            self.JobManager.StopJob(releaseInfoId)
            if (self.JobPhase is not None) and (
                self.JobPhase.JobManagerItem.ReleaseInfoId == releaseInfoId
                or releaseInfoId == -1
            ):
                self.JobPhase.JobManagerItem.StopRequested = True

        self.WaitEvent.set()

    def RequestHandlingOfNewAnnouncementFile(self, announcementFilePath):
        self.JobManager.AddNewAnnouncementFile(announcementFilePath)
        self.WaitEvent.set()

    def __ProcessJobPhase(self):
        jobPhase = None

        with self.Lock:
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

        # We can't lock on this because stopping a running job wouldn't be possible that way.
        jobPhase.Work()

        with self.Lock:
            self.JobPhase = None

        return True

    @staticmethod
    def __GetLoggerFromException(exception):
        if hasattr(exception, "Logger"):
            return exception.Logger
        return MyGlobals.Logger

    def __RunInternal(self):
        try:
            if not self.__ProcessJobPhase():
                # Sleep five seconds (or less if there is an event), if there was no work to do.
                # Sleeping is needed to not to flood the torrent client with continous requests.
                self.WaitEvent.wait(5)
                self.WaitEvent.clear()
        except (KeyboardInterrupt, SystemExit):
            raise
        except PtpUploaderInvalidLoginException as e:
            WorkerThread.__GetLoggerFromException(e).exception(
                "Caught invalid login exception in the worker thread loop. Aborting."
            )
            raise
        except PtpUploaderException as e:
            WorkerThread.__GetLoggerFromException(e).warning(
                "%s (PtpUploaderException)" % str(e)
            )
        except Exception as e:
            WorkerThread.__GetLoggerFromException(e).exception(
                "Caught exception in the worker thread loop. Trying to continue."
            )

    def run(self):
        # Create JobManager from this thread.
        self.JobManager = JobManager()

        while not self.StopRequested:
            self.__RunInternal()
