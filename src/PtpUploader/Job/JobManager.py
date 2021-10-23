import datetime
import threading

from PtpUploader.AnnouncementWatcher import *
from PtpUploader.Job.CheckAnnouncement import CheckAnnouncement
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.Upload import Upload
from PtpUploader.Logger import Logger
from PtpUploader.MyGlobals import MyGlobals


class JobManagerItem:
    def __init__(self, releaseInfoId, releaseInfo):
        self.ReleaseInfoId = releaseInfoId  # This will be accessed from another thread in case of stop request.
        self.ReleaseInfo = releaseInfo

        # So why this is not in ReleaseInfo? Because SQLAlchemy could possibly return with the same instance when restarting a canceled job.
        # This will be accessed from another thread in case of stop request.
        self.StopRequested = False


# All public methods are thread-safe.
# JobManager must be used from WorkerThread only (except the methods that state otherwise) because it deals with ReleaseInfo instances that can't pass thread boundaries because of SQLAlchemy.
# Both PendingAnnouncements and PendingDownloads gets modified from different thread than WorkerThread when cancelling a job so we use JobManagerItem.
# It makes the code really ugly...
class JobManager:
    def __init__(self):
        self.Lock = threading.RLock()
        self.PendingAnnouncements = []  # Contains JobManagerItem.
        self.PendingAnnouncementsFiles = []  # Contains announcement file paths.
        self.PendingDownloads = []  # Contains JobManagerItem.

        # Load unprocessed announcements from the watch directory.
        releaseInfos = AnnouncementWatcher.LoadAnnouncementFilesIntoTheDatabase()
        for releaseInfo in releaseInfos:
            jobManagerItem = JobManagerItem(releaseInfo.Id, releaseInfo)
            self.PendingAnnouncements.append(jobManagerItem)

    def __IsSourceAvailable(self, source):
        # This is handled in CheckAnnouncement.
        if source is None:
            return True

        runningDownloads = 0
        for item in self.PendingDownloads:
            releaseInfo = self.__GetJobManagerItemAsReleaseInfo(item)
            if releaseInfo.AnnouncementSource.Name == source.Name:
                runningDownloads += 1

        return runningDownloads < source.MaximumParallelDownloads

    def __CanStartPendingJob(self, releaseInfo):
        if (
            releaseInfo.JobRunningState == JobRunningState.Scheduled
            and datetime.datetime.utcnow() < releaseInfo.ScheduleTimeUtc
        ):
            return False

        return self.__IsSourceAvailable(releaseInfo.AnnouncementSource)

    def __LoadReleaseInfoFromDatabase(self, releaseInfoId):
        releaseInfo = ReleaseInfo.objects.get(Id=releaseInfoId)
        releaseInfo.Logger = Logger(releaseInfo.GetLogFilePath())
        releaseInfo.AnnouncementSource = MyGlobals.SourceFactory.GetSource(
            releaseInfo.AnnouncementSourceName
        )
        return releaseInfo

    def __GetJobManagerItemAsReleaseInfo(self, item):
        if item.ReleaseInfo is None:
            item.ReleaseInfo = self.__LoadReleaseInfoFromDatabase(item.ReleaseInfoId)
            return item.ReleaseInfo
        else:
            return item.ReleaseInfo

    def __ProcessPendingAnnouncementFiles(self):
        for announcementFilePath in self.PendingAnnouncementsFiles:
            releaseInfo = AnnouncementWatcher.ProcessAnnouncementFile(
                announcementFilePath
            )
            if releaseInfo is not None:
                jobManagerItem = JobManagerItem(releaseInfo.Id, releaseInfo)
                self.PendingAnnouncements.append(jobManagerItem)

    def __GetAnnouncementToProcess(self):
        processIndex = -1

        # Check if we can process anything from the pending announcments.
        # Jobs with immediate start option have priority over other jobs.
        for announcementIndex in range(len(self.PendingAnnouncements)):
            jobManagerItem = self.PendingAnnouncements[announcementIndex]
            releaseInfo = self.__GetJobManagerItemAsReleaseInfo(jobManagerItem)
            if releaseInfo.IsStartImmediately():
                processIndex = announcementIndex
                break
            elif processIndex == -1 and self.__CanStartPendingJob(releaseInfo):
                processIndex = announcementIndex

        if processIndex == -1:
            return None
        else:
            return self.PendingAnnouncements.pop(processIndex)

    # Must be called from the WorkerThread because of ReleaseInfo.
    def AddToPendingDownloads(self, releaseInfo):
        self.Lock.acquire()

        try:
            self.PendingDownloads.append(JobManagerItem(releaseInfo.Id, releaseInfo))
        finally:
            self.Lock.release()

    # Can be called from any thread.
    def AddNewAnnouncementFile(self, announcementFilePath):
        self.Lock.acquire()

        try:
            self.PendingAnnouncementsFiles.append(announcementFilePath)
        finally:
            self.Lock.release()
            
    def __GetFinishedDownloadToProcess(self):
        if len(self.PendingDownloads) > 0:
            print(("Pending downloads: %s" % len(self.PendingDownloads)))

        # TODO: can we use a multicast RPC call get all the statuses in one call?
        for downloadIndex in range(len(self.PendingDownloads)):
            jobManagerItem = self.PendingDownloads[downloadIndex]
            releaseInfo = self.__GetJobManagerItemAsReleaseInfo(jobManagerItem)
            logger = releaseInfo.Logger
            if releaseInfo.AnnouncementSource.IsDownloadFinished(
                logger, releaseInfo, MyGlobals.GetTorrentClient()
            ):
                return self.PendingDownloads.pop(downloadIndex)

        return None

    # Can be called from any thread.
    def StartJob(self, releaseInfoId):
        self.Lock.acquire()

        try:
            self.PendingAnnouncements.append(JobManagerItem(releaseInfoId, None))
        finally:
            self.Lock.release()

    def __StopJobInternal(self, releaseInfoId):
        # Iterate the list backwards because we may delete from it.
        for downloadIndex in reversed(list(range(len(self.PendingDownloads)))):
            item = self.PendingDownloads[downloadIndex]
            if item.ReleaseInfoId == releaseInfoId or releaseInfoId == -1:
                self.__SetJobStopped(item.ReleaseInfoId)
                self.PendingDownloads.pop(downloadIndex)

        # Iterate the list backwards because we may delete from it.
        for announcementIndex in reversed(list(range(len(self.PendingAnnouncements)))):
            item = self.PendingAnnouncements[announcementIndex]
            if item.ReleaseInfoId == releaseInfoId or releaseInfoId == -1:
                self.__SetJobStopped(item.ReleaseInfoId)
                self.PendingAnnouncements.pop(announcementIndex)

    def __SetJobStopped(self, releaseInfoId):
        # We have to get a new instance of ReleaseInfo because this function could come from another thread.
        releaseInfo = self.__LoadReleaseInfoFromDatabase(releaseInfoId)
        releaseInfo.JobRunningState = JobRunningState.Paused
        releaseInfo.save()

    # Can be called from any thread.
    def StopJob(self, releaseInfoId):
        self.Lock.acquire()

        try:
            self.__StopJobInternal(releaseInfoId)
        finally:
            self.Lock.release()

    # Must be called from the WorkerThread because of ReleaseInfo.
    def GetJobPhaseToProcess(self):
        self.Lock.acquire()

        try:
            # If there is a finished download, then upload it.
            jobManagerItem = self.__GetFinishedDownloadToProcess()
            if jobManagerItem is not None:
                return Upload(self, jobManagerItem, MyGlobals.GetTorrentClient())

            self.__ProcessPendingAnnouncementFiles()

            # If there is a new announcement, then check and start downloading it.
            jobManagerItem = self.__GetAnnouncementToProcess()
            if jobManagerItem is not None:
                return CheckAnnouncement(
                    self, jobManagerItem, MyGlobals.GetTorrentClient()
                )

            return None
        finally:
            self.Lock.release()
