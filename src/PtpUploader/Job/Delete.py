import logging
import threading

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings
from PtpUploader.Job.WorkerBase import WorkerBase

logger = logging.getLogger(__name__)


class Delete(WorkerBase):
    def __init__(self, release_id: int, mode: str, stop_requested: threading.Event):
        super().__init__(release_id, stop_requested)
        self.Phases = [self.__delete]
        self.mode = mode

    def __delete(self):
        if not self.ReleaseInfo.CanDeleted():
            logger.error("The job is currently running and can't be deleted!")
            return

        deleteMode = self.mode.lower()
        deleteSourceData = deleteMode in ["job_source", "job_all"]
        deleteUploadData = deleteMode in ["job_upload", "job_all"]

        announcementSource = self.ReleaseInfo.AnnouncementSource
        if announcementSource is None:
            announcementSource = MyGlobals.SourceFactory.GetSource(
                self.ReleaseInfo.AnnouncementSourceName
            )

        if announcementSource is not None:  # Still possibly not there
            announcementSource.Delete(
                self.ReleaseInfo,
                Settings.GetTorrentClient(),
                deleteSourceData,
                deleteUploadData,
            )

        self.ReleaseInfo.delete()
        logger.info("Release deleted")

        return "OK"
