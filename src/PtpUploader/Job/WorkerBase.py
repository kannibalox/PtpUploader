import logging
import os
import threading
import traceback

from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.PtpUploaderException import *
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings


logger = logging.getLogger(__name__)


class WorkLogFilter(logging.Filter):
    def __init__(self, release_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.release_id = release_id

    def filter(self, record):
        if "release_id" in record.__dict__:
            return self.release_id == record.release_id
        return False


class WorkerBase:
    def __init__(self, release_id: int, stop_requested: threading.Event):
        self.Phases = []
        self.stop_requested: threading.Event = stop_requested
        self.ReleaseInfo = ReleaseInfo.objects.get(Id=release_id)
        self.logHandler = (
            self.start_worker_logging()
        )  # needed to clean up after job is finished
        self.logger = self.ReleaseInfo.logger(logger)  # Just a nice shortcut

    def __WorkInternal(self):
        if not self.Phases:
            raise NotImplementedError("Add phases to this worker")
        for phase in self.Phases:
            if self.stop_requested.is_set():
                self.ReleaseInfo.JobRunningState = JobRunningState.Paused
                self.ReleaseInfo.save()
                break

            phase()
        self.stop_worker_logging()

    def stop_worker_logging(self):
        logging.getLogger().removeHandler(self.logHandler)

    def start_worker_logging(self):
        """
        Add a log handler to separate file for current thread
        """
        path = os.path.join(Settings.GetJobLogPath(), str(self.ReleaseInfo.Id))
        log_handler = logging.FileHandler(path)

        log_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)-15s" " %(name)-11s" " %(levelname)-5s" " %(message)s"
        )
        log_handler.setFormatter(formatter)

        log_filter = WorkLogFilter(self.ReleaseInfo.Id)
        log_handler.addFilter(log_filter)

        log = logging.getLogger()
        log.addHandler(log_handler)
        return log_handler

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

            if isinstance(e, PtpUploaderException) and str(e).startswith("Stopping "):
                self.ReleaseInfo.logger().info(f"Received stop: {e}")
            else:
                self.ReleaseInfo.logger().exception(traceback.format_exc())
            raise
