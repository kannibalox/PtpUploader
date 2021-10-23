import datetime
import platform
import time

from django.db.models import Q
from sqlalchemy import create_engine, exc, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings


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


def GetDatabaseUrl():
    # In case of Linux the path is already an absolute path and thus starts with a slash.
    path = Settings.GetDatabaseFilePath()

    # To use a Windows path, regular drive specifications and backslashes can be used. Double backslashes are probably needed:
    if platform.system() == "Windows":
        path = path.replace("\\", "/")

    return "sqlite:///" + path


def MigrateSchema():
    pass
    # There are two possible reasons for the exception:
    # - column already exists, no need for schema migration: "duplicate column name"
    # - the database has just been created, the table is not yet exists, no need for schema migration: "no such table"
    # try:
    #     Database.DbSession.execute(
    #         """ALTER TABLE release ADD COLUMN IncludedFiles VARCHAR DEFAULT "";"""
    #     )
    #     Database.DbSession.execute(
    #         """ALTER TABLE release ADD COLUMN PtpTorrentId VARCHAR DEFAULT "";"""
    #     )
    #     Database.DbSession.execute(
    #         """ALTER TABLE release ADD COLUMN Subtitles VARCHAR DEFAULT "";"""
    #     )
    # except exc.OperationalError:
    #     pass

    # try:
    #     Database.DbSession.execute(
    #         """ALTER TABLE release ADD COLUMN DuplicateCheckCanIgnore INTEGER DEFAULT "0";"""
    #     )
    # except exc.OperationalError:
    #     pass

    # try:
    #     Database.DbSession.execute(
    #         """ALTER TABLE release ADD COLUMN ScheduleTimeUtc VARCHAR DEFAULT "2001-01-01 01:01:01";"""
    #     )
    # except exc.OperationalError:
    #     pass

    # try:
    #     Database.DbSession.execute(
    #         """ALTER TABLE release ADD COLUMN UploadTorrentCreatePath VARCHAR DEFAULT "";"""
    #     )
    # except exc.OperationalError:
    #     pass


def InitDb():
    MyGlobals.Logger.info("Initializing database.")

    # Database.DbEngine = create_engine(GetDatabaseUrl())
    # Database.DbSession = scoped_session(
    #     sessionmaker(autocommit=False, autoflush=False, bind=Database.DbEngine)
    # )
    # Database.Base.query = Database.DbSession.query_property()

    # MigrateSchema()
    for releaseInfo in ReleaseInfo.objects.filter(JobRunningState__in=[
        JobRunningState.WaitingForStart, JobRunningState.Scheduled, JobRunningState.InProgress
    ]):
        releaseInfo.JobRunningState = JobRunningState.Paused
        releaseInfo.save()
