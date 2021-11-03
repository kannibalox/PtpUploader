import logging
import os
import threading
import traceback

from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.PtpUploaderException import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings


logger = logging.getLogger()


class WorkerBase:
    def __init__(self, release_id: int, stop_requested: threading.Event):
        self.Phases = []
        self.stop_requested: threading.Event = stop_requested
        self.ReleaseInfo = ReleaseInfo.objects.get(Id=release_id)
        path = os.path.join(Settings.GetJobLogPath(), str(release_id))
        logging.basicConfig(filename=path, level=logging.DEBUG)

    def __WorkInternal(self):
        if not self.Phases:
            raise NotImplementedError("Add phases to this worker")
        for phase in self.Phases:
            if self.stop_requested.is_set():
                self.ReleaseInfo.JobRunningState = JobRunningState.Paused
                self.ReleaseInfo.save()
                return

            phase()

    def Work(self):
        try:
            self.__WorkInternal()
            self.ReleaseInfo.clean()
        except Exception as e:
            if hasattr(e, "JobRunningState"):
                self.ReleaseInfo.JobRunningState = e.JobRunningState
            else:
                self.ReleaseInfo.JobRunningState = JobRunningState.Failed

            self.ReleaseInfo.ErrorMessage = str(e)
            self.ReleaseInfo.save()

            logger.error(traceback.format_exc())
            e.Logger = logger
            raise
