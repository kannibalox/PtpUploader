import datetime
import time

from sqlalchemy.ext.declarative import declarative_base

from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.ReleaseInfo import ReleaseInfo


class Database:
    DbEngine = None
    DbSession = None
    Base = declarative_base()

    @staticmethod
    def MakeTimeStamp():
        # time.time() returns the time as a floating point number expressed in seconds since the epoch, in UTC.
        return int(time.time() * 100)

    @staticmethod
    def TimeStampToUtcDateTime(timeStamp):
        return datetime.datetime.utcfromtimestamp(timeStamp / 100)


def InitDb():
    MyGlobals.Logger.info("Initializing database.")

    for releaseInfo in ReleaseInfo.objects.filter(JobRunningState__in=[
        JobRunningState.WaitingForStart, JobRunningState.Scheduled, JobRunningState.InProgress
    ]):
        releaseInfo.JobRunningState = JobRunningState.Paused
        releaseInfo.save()
