"""
Replaces the artisanal python 2 threading system
This directly handles:
- Loading announcement files
- Scanning the DB for work
- Watching the client for pending downloads
All of these actions will happen on a schedule, but the thread can be woken up immediately by an Event.

For WorkerBase actions, they get launched into a ThreadPoolExecutor, with an event flag
to allow for interrupting the work phases. This allows this class to check the status of
any active futures when deciding how to handle start/stop requests.

However, there is no direct locking of resources, as we can use the DB as more flexible thread-safe state
holder.

It's called the JobSupervisor because supervisors are better than managers.
"""

import threading
import queue
import logging
from typing import List, Dict
from concurrent import futures

from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Job.Upload import Upload
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.CheckAnnouncement import CheckAnnouncement
from PtpUploader.PtpUploaderMessage import *

logger = logging.getLogger(__name__)


class JobSupervisor(threading.Thread):
    def __init__(self):
        super().__init__()
        self.futures: Dict[str, List[threading.Event, futures.Future]] = {}
        self.message_queue: queue.SimpleQueue = queue.SimpleQueue()
        self.stop_requested: threading.Event = threading.Event()
        self.pool: futures.ThreadPoolExecutor = futures.ThreadPoolExecutor(
            max_workers=2
        )

    def check_pending_downloads(self):
        pass

    def load_announcements(self):
        pass

    def add_message(self, message):
        if isinstance(message, PtpUploaderMessageBase):
            self.message_queue.put(message)
        else:
            logger.warning("Unknown message '%s'", message)

    def scan_db(self):
        """Find releases pending work by their DB status"""
        for release in ReleaseInfo.objects.filter(
            JobRunningState=JobRunningState.WaitingForStart
        ):
            if release.Id not in self.futures.keys():
                worker_stop_flag = threading.Event()
                worker = CheckAnnouncement(
                    release_id=release.Id, stop_requested=worker_stop_flag
                )
                self.futures[release.Id] = [
                    worker_stop_flag,
                    self.pool.submit(worker.Work),
                ]

    def process_pending(self):
        self.check_pending_downloads()
        self.load_announcements()
        self.scan_db()

    def stop_future(self, releaseId):
        pass

    def reap_finished(self):
        for key, val in list(self.futures.items()):
            flag, result = val
            if result.done():
                if result.exception():  # Exceptions are used as messengers, hence info
                    logger.info(
                        "Job %s finished with exception '%s'", key, result.exception()
                    )
                del self.futures[key]

    def run(self):
        logger.info("Starting supervisors")
        while True:
            print(self.futures)
            try:
                message = self.message_queue.get(timeout=3)
                if isinstance(message, PtpUploaderMessageStopJob):
                    self.stop_future(message.releaseInfoId)
                elif isinstance(message, PtpUploaderMessageQuit):
                    self.stop_requested.set()
            except queue.Empty:
                pass

            if self.stop_requested.is_set():
                self.cleanup_futures()
                break
            else:
                self.reap_finished()
                self.process_pending()

    def cleanup_futures(self):
        pass
