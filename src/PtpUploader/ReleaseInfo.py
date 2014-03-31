from Job.FinishedJobPhase import FinishedJobPhase
from Job.JobRunningState import JobRunningState
from Job.JobStartMode import JobStartMode

from Database import Database
from PtpUploaderException import PtpUploaderException
from Settings import Settings

from sqlalchemy import Boolean, Column, DateTime, Integer, orm, String

import datetime
import os

class ReleaseInfoFlags:
	# There are three categories on PTP: SD, HD and Other. The former two can figured out from the resolution type.
	# This flag is for indicating the Other ("Not main movie") category. Extras, Rifftrax, etc. belong here.
	SpecialRelease                      = 1 << 0

	# Release made by a scene group.
	SceneRelease                        = 1 << 1
	
	# If set, then it overrides the value returned by SourceBase.IsSingleFileTorrentNeedsDirectory.
	ForceDirectorylessSingleFileTorrent = 1 << 2
	
	# If this is set then the job will be the next processed job and the download will start regardless the number of maximum parallel downloads set for the source.
	StartImmediately                    = 1 << 3

	# Job will be stopped before uploading.
	StopBeforeUploading                 = 1 << 4

	TrumpableForNoEnglishSubtitles      = 1 << 5

class ReleaseInfo(Database.Base):
	__tablename__ = "release"

	Id = Column( Integer, primary_key = True )
	
	# Announcement
	AnnouncementSourceName = Column( String )
	AnnouncementId = Column( String )
	ReleaseName = Column( String )
	
	# For PTP
	Type = Column( String )
	ImdbId = Column( String )
	Directors = Column( String )
	Title = Column( String )
	Year = Column( String )
	Tags = Column( String )
	MovieDescription = Column( String )
	CoverArtUrl = Column( String )
	YouTubeId = Column( String )
	MetacriticUrl = Column( String )
	RottenTomatoesUrl = Column( String )
	Codec = Column( String )
	CodecOther = Column( String )
	Container = Column( String )
	ContainerOther = Column( String )
	ResolutionType = Column( String )
	Resolution = Column( String )
	Source = Column( String )
	SourceOther = Column( String )
	RemasterTitle = Column( String )
	RemasterYear = Column( String )

	# Other
	JobStartMode = Column( Integer )
	JobRunningState = Column( Integer )
	FinishedJobPhase = Column( Integer )
	Flags = Column( Integer )
	ErrorMessage = Column( String )
	PtpId = Column( String )
	PtpTorrentId = Column( String )
	InternationalTitle = Column( String )
	Nfo = Column( String )
	SourceTorrentFilePath = Column( String )
	SourceTorrentInfoHash = Column( String )
	UploadTorrentCreatePath = Column( String )
	UploadTorrentFilePath = Column( String )
	UploadTorrentInfoHash = Column( String )
	ReleaseDownloadPath = Column( String )
	ReleaseUploadPath = Column( String )
	ReleaseNotes = Column( String )
	Screenshots = Column( String )
	LastModificationTime = Column( Integer, default = Database.MakeTimeStamp, onupdate = Database.MakeTimeStamp )
	Size = Column( Integer )
	Subtitles = Column( String )
	IncludedFiles = Column( String )
	DuplicateCheckCanIgnore = Column( Integer )
	ScheduleTimeUtc = Column( DateTime )
	
	def __init__(self):
		self.AnnouncementSourceName = "" # A name of a class from the Source namespace.
		self.AnnouncementId = ""
		self.ReleaseName = ""

		# <<< These are the required fields needed for an upload to PTP.
		self.Type = "Feature Film" # Feature Film, Short Film, Miniseries, Stand-up Comedy, Concert
		self.ImdbId = "" # Just the number. Eg.: 0111161 for http://www.imdb.com/title/tt0111161/
		self.Directors = "" # Stored as a comma separated list. PTP needs this as a list, use GetDirectors.
		self.Title = "" # Eg.: El Secreto de Sus Ojos AKA The Secret in Their Eyes
		self.Year = ""
		self.Tags = ""
		self.MovieDescription = u""
		self.CoverArtUrl = ""
		self.YouTubeId = "" # Eg.: FbdOnGNBMAo for http://www.youtube.com/watch?v=FbdOnGNBMAo
		self.MetacriticUrl = "" # TODO: no longer used. Only here because of SQLite.
		self.RottenTomatoesUrl = "" # TODO: no longer used. Only here because of SQLite.
		self.Codec = "" # Other, DivX, XviD, H.264, x264, DVD5, DVD9, BD25, BD50
		self.CodecOther = "" # TODO: no longer used. Only here because of SQLite.
		self.Container = "" # Other, MPG, AVI, MP4, MKV, VOB IFO, ISO, m2ts
		self.ContainerOther = "" # TODO: no longer used. Only here because of SQLite.
		self.ResolutionType = "" # Other, PAL, NTSC, 480p, 576p, 720p, 1080i, 1080p
		self.Resolution = "" # Exact resolution when ResolutionType is Other. 
		self.Source = "" # Other, CAM, TS, VHS, TV, DVD-Screener, TC, HDTV, WEB, R5, DVD, HD-DVD, Blu-ray
		self.SourceOther = "" # Source type when Source is Other.
		self.RemasterTitle = "" # Eg.: Hardcoded English
		self.RemasterYear = ""
		# Release description text is also needed for PTP but we use the other members to fill that.
		# Scene is needed too. Use IsSceneRelease.
		# Special ("Not main movie") is needed too. Use SpecialRelease.
		# >>> Till this.

		self.JobStartMode = JobStartMode.Automatic
		self.JobRunningState = JobRunningState.WaitingForStart
		self.FinishedJobPhase = 0 # Flag. Takes values from FinishedJobPhase.
		self.Flags = 0 # Takes values from ReleaseInfoFlags.
		self.ErrorMessage = ""
		self.PtpId = ""
		self.PtpTorrentId = ""
		self.InternationalTitle = "" # International title of the movie. Eg.: The Secret in Their Eyes. Needed for renaming releases coming from Cinemageddon.
		self.Nfo = u"" # TODO: it is pointless to store this is in the database
		self.SourceTorrentFilePath = ""
		self.SourceTorrentInfoHash = ""
		self.UploadTorrentCreatePath = "" # This is the final path where the torrent was created from. It's either a directory or a file (for single file uploads).
		self.UploadTorrentFilePath = ""
		self.UploadTorrentInfoHash = ""
		self.ReleaseDownloadPath = "" # Empty if using the default path. See GetReleaseDownloadPath.
		self.ReleaseUploadPath = "" # Empty if using the default path. See GetReleaseUploadPath.
		self.ReleaseNotes = ""
		self.Screenshots = "" # JSON encode of a ScreenshotList class
		self.LastModificationTime = 0
		self.Size = 0
		self.Subtitles = "" # Comma separated list of PTP language IDs. Eg.: "1, 2"
		self.IncludedFiles = "" # Contains only the customized files. Stored as JSON string.
		self.DuplicateCheckCanIgnore = 0 # The highest torrent ID from the group. (Only filled out when the user presses says he wants to skip the duplicate checking.)
		self.ScheduleTimeUtc = datetime.datetime.utcnow()
		
		self.MyConstructor()

	# "The SQLAlchemy ORM does not call __init__ when recreating objects from database rows."
	@orm.reconstructor
	def MyConstructor(self):
		self.AnnouncementSource = None # A class from the Source namespace.
		self.Logger = None
		self.SceneAccessDownloadUrl = "" # Temporary store for FunFile and SuperTorrents.
		self.SourceIsAFile = False # Used by Source.File class.
		self.JobStartTimeUtc = datetime.datetime.utcnow()

	def GetImdbId(self):
		return self.ImdbId

	def GetPtpId(self):
		return self.PtpId

	def GetPtpTorrentId(self):
		return self.PtpTorrentId

	def HasImdbId(self):
		return len( self.ImdbId ) > 0

	def IsZeroImdbId(self):
		return self.ImdbId == "0"

	def SetZeroImdbId(self):
		self.ImdbId = "0"

	def HasPtpId(self):
		return len( self.PtpId ) > 0

	def HasPtpTorrentId(self):
		return len( self.PtpTorrentId ) > 0

	def IsUserCreatedJob(self):
		return self.JobStartMode == JobStartMode.Manual or self.JobStartMode == JobStartMode.ManualForced

	def IsForceUpload(self):
		return self.JobStartMode == JobStartMode.ManualForced

	def IsSynopsisSet(self):
		return len( self.MovieDescription ) > 0

	def IsCoverArtUrlSet(self):
		return len( self.CoverArtUrl ) > 0

	def IsReleaseNameSet(self):
		return len( self.ReleaseName ) > 0

	def IsCodecSet(self): 
		return len( self.Codec ) > 0

	def IsContainerSet(self): 
		return len( self.Container ) > 0

	def IsSourceSet(self): 
		return len( self.Source ) > 0

	def IsResolutionTypeSet(self): 
		return len( self.ResolutionType ) > 0
	
	def IsSourceTorrentFilePathSet(self):
		return len( self.SourceTorrentFilePath ) > 0

	def IsUploadTorrentFilePathSet(self):
		return len( self.UploadTorrentFilePath ) > 0
	
	def GetDirectors(self):
		if len( self.Directors ) > 0:
			return self.Directors.split( ", " )
		else:
			return []
	
	def SetDirectors(self, list):
		for name in list:
			if name.find( "," ) != -1:
				raise PtpUploaderException( "Director name '%s' contains a comma." % name )
		
		self.Directors = ", ".join( list )
		
	def GetSubtitles(self):
		if len( self.Subtitles ) > 0:
			return self.Subtitles.split( ", " )
		else:
			return []

	def SetSubtitles(self, list):
		for id in list:
			if id.find( "," ) != -1:
				raise PtpUploaderException( "Language id '%s' contains a comma." % name )
		
		self.Subtitles = ", ".join( list )

	def IsSceneRelease(self):
		return ( self.Flags & ReleaseInfoFlags.SceneRelease ) != 0

	def SetSceneRelease(self):
		self.Flags |= ReleaseInfoFlags.SceneRelease

	def IsHighDefinition(self):
		return self.ResolutionType == "720p" or self.ResolutionType == "1080i" or self.ResolutionType == "1080p"

	def IsStandardDefinition(self):
		return not self.IsHighDefinition()

	def IsRemux(self):
		return self.RemasterTitle.find( "Remux" ) != -1

	def IsDvdImage(self):
		return self.Codec == "DVD5" or self.Codec == "DVD9"

	# See the description at the flag.
	def IsSpecialRelease(self):
		return ( self.Flags & ReleaseInfoFlags.SpecialRelease ) != 0

	# See the description at the flag.
	def SetSpecialRelease(self):
		self.Flags |= ReleaseInfoFlags.SpecialRelease

	# See the description at the flag.
	def IsForceDirectorylessSingleFileTorrent(self):
		return ( self.Flags & ReleaseInfoFlags.ForceDirectorylessSingleFileTorrent ) != 0

	# See the description at the flag.
	def SetForceDirectorylessSingleFileTorrent(self):
		self.Flags |= ReleaseInfoFlags.ForceDirectorylessSingleFileTorrent

	# See the description at the flag.
	def IsStartImmediately(self):
		return ( self.Flags & ReleaseInfoFlags.StartImmediately ) != 0

	# See the description at the flag.
	def SetStartImmediately(self):
		self.Flags |= ReleaseInfoFlags.StartImmediately

	# See the description at the flag.
	def IsStopBeforeUploading(self):
		return ( self.Flags & ReleaseInfoFlags.StopBeforeUploading ) != 0

	def IsTrumpableForNoEnglishSubtitles( self ):
		return ( self.Flags & ReleaseInfoFlags.TrumpableForNoEnglishSubtitles ) != 0

	def SetTrumpableForNoEnglishSubtitles( self ):
		self.Flags |= ReleaseInfoFlags.TrumpableForNoEnglishSubtitles

	# See the description at the flag.
	def SetStopBeforeUploading(self, stop):
		if stop:
			self.Flags |= ReleaseInfoFlags.StopBeforeUploading
		else:
			self.Flags &= ~ReleaseInfoFlags.StopBeforeUploading

	def CanEdited(self):
		return self.JobRunningState != JobRunningState.WaitingForStart and self.JobRunningState != JobRunningState.Scheduled and self.JobRunningState != JobRunningState.InProgress and self.JobRunningState != JobRunningState.Finished

	def IsReleaseNameEditable(self):
		return self.CanEdited() and not self.IsJobPhaseFinished( FinishedJobPhase.Download_CreateReleaseDirectory )

	def CanResumed(self):
		return self.CanEdited()

	def CanStopped(self):
		return self.JobRunningState == JobRunningState.WaitingForStart or self.JobRunningState == JobRunningState.Scheduled or self.JobRunningState == JobRunningState.InProgress

	def CanDeleted(self):
		return self.JobRunningState != JobRunningState.WaitingForStart and self.JobRunningState != JobRunningState.Scheduled and self.JobRunningState != JobRunningState.InProgress

	def IsJobPhaseFinished(self, jobPhase):
		return ( self.FinishedJobPhase & jobPhase ) != 0 

	def SetJobPhaseFinished(self, jobPhase):
		self.FinishedJobPhase |= jobPhase

	# Eg.: "working directory/log/job/1"
	def GetLogFilePath(self):
		return os.path.join( Settings.GetJobLogPath(), str( self.Id ) )

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	def GetReleaseRootPath(self):
		releasesPath = os.path.join( Settings.WorkingPath, "release" )
		return os.path.join( releasesPath, self.ReleaseName )

	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
	def GetReleaseDownloadPath(self):
		if len( self.ReleaseDownloadPath ) > 0:
			return self.ReleaseDownloadPath
		else:
			return os.path.join( self.GetReleaseRootPath(), "download" )

	def SetReleaseDownloadPath(self, path):
		self.ReleaseDownloadPath = path
	
	# Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/upload/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
	# It must contain the final release name because of mktorrent.
	def GetReleaseUploadPath(self):
		if len( self.ReleaseUploadPath ) > 0:
			return self.ReleaseUploadPath
		else:
			path = os.path.join( self.GetReleaseRootPath(), "upload" )
			return os.path.join( path, self.ReleaseName )

	def SetReleaseUploadPath(self, path):
		self.ReleaseUploadPath = path

	def IsTorrentNeedsDuplicateChecking( self, torrentId ):
		return torrentId > self.DuplicateCheckCanIgnore