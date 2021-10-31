import threading

from PtpUploader.Logger import Logger
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.Job.WorkerBase import WorkerBase

class Delete(WorkerBase):
    def __init__(self, release_id: int, mode: str, stop_requested: threading.Event):
        super().__init__(release_id, stop_requested)
        self.Phases = [
            self.__delete
        ]
        self.mode = mode

    def __delete(self):
        if not self.ReleaseInfo.CanDeleted():
            return "The job is currently running and can't be deleted!"

        deleteMode = self.mode.lower()
        deleteSourceData = deleteMode in ["job_source", "job_all"]
        deleteUploadData = deleteMode in ["job_upload", "job_all"]

        announcementSource = self.ReleaseInfo.AnnouncementSource
        if announcementSource is None:
            announcementSource = MyGlobals.SourceFactory.GetSource(
                self.ReleaseInfo.AnnouncementSourceName
            )

        if announcementSource is not None: # Still possibly not there
            if self.ReleaseInfo.Logger is None:
                self.ReleaseInfo.Logger = Logger(self.ReleaseInfo.GetLogFilePath())

            announcementSource.Delete(
                self.ReleaseInfo, Settings.GetTorrentClient(), deleteSourceData, deleteUploadData
            )

        self.ReleaseInfo.delete()

        return "OK"
