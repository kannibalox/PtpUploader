"""Handle deletion of jobs when requested by user"""
import logging
import threading

from PtpUploader.Job.WorkerBase import WorkerBase
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.Settings import Settings


logger = logging.getLogger(__name__)


class Delete(WorkerBase):
    """Create a simple worker with a single phase"""

    def __init__(self, release_id: int, mode: str, stop_requested: threading.Event):
        super().__init__(release_id, stop_requested)
        self.Phases = [self.__delete]
        self.mode = mode

    def __delete(self):
        if not self.ReleaseInfo.CanDeleted():
            logger.error("The job is currently running and can't be deleted!")
            return "Error"

        delete_mode = self.mode.lower()
        delete_source_data = delete_mode in ["job_source", "job_all"]
        delete_upload_data = delete_mode in ["job_upload", "job_all"]

        announcement_source = self.ReleaseInfo.AnnouncementSource
        if announcement_source is None:
            announcement_source = MyGlobals.SourceFactory.GetSource(
                self.ReleaseInfo.AnnouncementSourceName
            )

        if announcement_source is not None:  # Still possibly not there
            announcement_source.Delete(
                self.ReleaseInfo,
                Settings.GetTorrentClient(),
                delete_source_data,
                delete_upload_data,
            )

        self.ReleaseInfo.delete()
        logger.info("Release deleted")

        return "OK"
