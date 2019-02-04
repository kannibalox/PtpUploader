from .Job.JobRunningState import JobRunningState

from .MyGlobals import MyGlobals
from .Settings import Settings

from sqlalchemy import create_engine, exc, or_
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import datetime
import platform
import time

class Database:
	DbEngine = None
	DbSession = None
	Base = declarative_base()
	
	@staticmethod
	def MakeTimeStamp():
		# time.time() returns the time as a floating point number expressed in seconds since the epoch, in UTC.
		return int( time.time() * 100 )

	@staticmethod
	def TimeStampToUtcDateTime( timeStamp ):
		return datetime.datetime.utcfromtimestamp( timeStamp / 100 )

def GetDatabaseUrl():
	# In case of Linux the path is already an absolute path and thus starts with a slash. 
	path = Settings.GetDatabaseFilePath()

	# To use a Windows path, regular drive specifications and backslashes can be used. Double backslashes are probably needed:
	if platform.system() == "Windows":
		path = path.replace( "\\", "/" )

	return "sqlite:///" + path

def MigrateSchema():
	# There are two possible reasons for the exception:
	# - column already exists, no need for schema migration: "duplicate column name"
	# - the database has just been created, the table is not yet exists, no need for schema migration: "no such table"
	try:
		Database.DbSession.execute( """ALTER TABLE release ADD COLUMN IncludedFiles VARCHAR DEFAULT "";""" )
		Database.DbSession.execute( """ALTER TABLE release ADD COLUMN PtpTorrentId VARCHAR DEFAULT "";""" )
		Database.DbSession.execute( """ALTER TABLE release ADD COLUMN Subtitles VARCHAR DEFAULT "";""" )
	except exc.OperationalError:
		pass

	try:
		Database.DbSession.execute( """ALTER TABLE release ADD COLUMN DuplicateCheckCanIgnore INTEGER DEFAULT "0";""" )
	except exc.OperationalError:
		pass

	try:
		Database.DbSession.execute( """ALTER TABLE release ADD COLUMN ScheduleTimeUtc VARCHAR DEFAULT "2001-01-01 01:01:01";""" )
	except exc.OperationalError:
		pass

	try:
		Database.DbSession.execute( """ALTER TABLE release ADD COLUMN UploadTorrentCreatePath VARCHAR DEFAULT "";""" )
	except exc.OperationalError:
		pass

def InitDb():
	MyGlobals.Logger.info( "Initializing database." )
	
	Database.DbEngine = create_engine( GetDatabaseUrl() )
	Database.DbSession = scoped_session( sessionmaker( autocommit = False, autoflush = False, bind = Database.DbEngine ) )
	Database.Base.query = Database.DbSession.query_property()
	
	MigrateSchema()
	
	# import all modules here that might define models so that
	# they will be registered properly on the metadata. Otherwise
	# you will have to import them first before calling InitDb()
	from .ReleaseInfo import ReleaseInfo
	Database.Base.metadata.create_all( bind = Database.DbEngine )

	# Make sure that jobs running states are valid. There can't be any running jobs.
	query = Database.DbSession.query( ReleaseInfo ).filter( or_( ReleaseInfo.JobRunningState == JobRunningState.WaitingForStart, ReleaseInfo.JobRunningState == JobRunningState.Scheduled, ReleaseInfo.JobRunningState == JobRunningState.InProgress ) )
	for releaseInfo in query:
		releaseInfo.JobRunningState = JobRunningState.Paused
	Database.DbSession.commit()
