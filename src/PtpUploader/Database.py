from MyGlobals import MyGlobals
from Settings import Settings

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

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

def GetDatabaseUrl():
	# In case of Linux the path is already an absolute path and thus starts with a slash. 
	path = Settings.GetDatabaseFilePath()

	# To use a Windows path, regular drive specifications and backslashes can be used. Double backslashes are probably needed:
	if platform.system() == "Windows":
		path = path.replace( "\\", "/" )

	return "sqlite:///" + path

def InitDb():
	MyGlobals.Logger.info( "Initializing database." )
	
	Database.DbEngine = create_engine( GetDatabaseUrl() )
	Database.DbSession = scoped_session( sessionmaker( autocommit = False, autoflush = False, bind = Database.DbEngine ) )
	Database.Base.query = Database.DbSession.query_property()
	
	# Schema migration
	# Database.DbSession.execute( """ALTER TABLE release ADD COLUMN ReleaseDownloadPath VARCHAR DEFAULT "";""" )
	
	# import all modules here that might define models so that
	# they will be registered properly on the metadata. Otherwise
	# you will have to import them first before calling InitDb()
	import ReleaseInfo
	Database.Base.metadata.create_all( bind = Database.DbEngine )

	# TODO: set all jobs to stopped