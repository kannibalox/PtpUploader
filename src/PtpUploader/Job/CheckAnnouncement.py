from InformationSource.Imdb import Imdb
from InformationSource.MoviePoster import MoviePoster

from Ptp import Ptp
from PtpUploaderException import *

class CheckAnnouncement:
	def __init__(self, releaseInfo):
		self.ReleaseInfo = releaseInfo
		self.MovieOnPtpResult = None

	def __PrepareDownload(self):
		result = self.ReleaseInfo.AnnouncementSource.PrepareDownload( self.ReleaseInfo.Logger, self.ReleaseInfo )
		if result is None:
			return False
		return True

	def __ValidateReleaseInfo(self):
		# Make sure we have the IMDb id.
		if len( self.ReleaseInfo.GetImdbId() ) <= 0:
			self.ReleaseInfo.Logger.error( "IMDb id can't be found." )
			return False
	
		# Make sure the source is providing a name.
		if len( self.ReleaseInfo.ReleaseName ) <= 0:
			self.ReleaseInfo.Logger.error( "Name of the release is not specified." )
			return False

		# Make sure the source is providing release quality information.
		if len( self.ReleaseInfo.Quality ) <= 0:
			self.ReleaseInfo.Logger.error( "Quality of the release is not specified." )
			return False

		# Make sure the source is providing release source information.
		if len( self.ReleaseInfo.Source ) <= 0:
			self.ReleaseInfo.Logger.error( "Source of the release is not specified." )
			return False

		# Make sure the source is providing release codec information.
		if len( self.ReleaseInfo.Codec ) <= 0:
			self.ReleaseInfo.Logger.error( "Codec of the release is not specified." )
			return False

		# Make sure the source is providing release resolution type information.
		if len( self.ReleaseInfo.ResolutionType ) <= 0:
			self.ReleaseInfo.Logger.error( "Resolution type of the release is not specified." )
			return False		

		# HD XviDs are not allowed.
		if self.ReleaseInfo.Quality == "High Definition" and ( self.ReleaseInfo.Codec == "XviD" or self.ReleaseInfo.Codec == "DivX" ):
			raise PtpUploaderException( "Forbidden combination of quality '%s' and codec '%s'." % ( self.ReleaseInfo.Quality, self.ReleaseInfo.Codec ) )
		
		return True

	def __CheckIfExistsOnPtp(self):			
		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that nothing interesting has been announcened for a while. 
		Ptp.Login()

		self.MovieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )

		# If this is an automatic announcement then we have to check if is it already on PTP.
		if not self.ReleaseInfo.IsManualAnnouncement:
			existingRelease = self.MovieOnPtpResult.IsReleaseExists( self.ReleaseInfo )
			if existingRelease is not None:
				self.ReleaseInfo.Logger.info( "Release '%s' already exists on PTP. Skipping upload because of format '%s'." % ( self.ReleaseInfo.ReleaseName, existingRelease ) )
				return False

		return True
	
	def __FillOutDetailsForNewMovie(self):
		# If this movie has no page yet on PTP then fill out the required info (title, year, etc.).
		if self.MovieOnPtpResult.IsMoviePageExists():
			return True

		Ptp.FillImdbInfo( self.ReleaseInfo.Logger, self.ReleaseInfo )

		if "adult" in self.ReleaseInfo.Tags:
			self.ReleaseInfo.Logger.info( "Ignoring release '%s' because its genre is adult." % self.ReleaseInfo.ReleaseName )
			return False
		
		imdbInfo = Imdb.GetInfo( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )

		if imdbInfo.IsSeries:
			self.ReleaseInfo.Logger.info( "Ignoring release '%s' because it is a series." % self.ReleaseInfo.ReleaseName )
			return False

		# PTP return with the original title, IMDb's iPhone API returns with the international English title.
		self.ReleaseInfo.InternationalTitle = imdbInfo.Title
		if self.ReleaseInfo.Title != self.ReleaseInfo.InternationalTitle and len( self.ReleaseInfo.InternationalTitle ) > 0:
			self.ReleaseInfo.Title += " AKA " + self.ReleaseInfo.InternationalTitle

		if len( self.ReleaseInfo.MovieDescription ) <= 0:
			self.ReleaseInfo.MovieDescription = imdbInfo.Plot 

		if len( self.ReleaseInfo.CoverArtUrl ) <= 0:
			self.ReleaseInfo.CoverArtUrl = imdbInfo.PosterUrl 
			if len( self.ReleaseInfo.CoverArtUrl ) <= 0:
				self.ReleaseInfo.CoverArtUrl = MoviePoster.Get( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() ) 
	
		return True
	
	def Work(self):
		self.ReleaseInfo.Logger.info( "Working on announcement from '%s' with id '%s' and name '%s'." % ( self.ReleaseInfo.AnnouncementSource.Name, self.ReleaseInfo.AnnouncementId, self.ReleaseInfo.ReleaseName ) )

		if not self.__PrepareDownload():
			return False
		if not self.__ValidateReleaseInfo():
			return False
		if not self.__CheckIfExistsOnPtp():
			return False
		if not self.__FillOutDetailsForNewMovie():
			return False
		
		return True
	
	@staticmethod
	def DoWork(releaseInfo): 
		try:
			checkAnnouncement = CheckAnnouncement( releaseInfo )
			return checkAnnouncement.Work()
		except Exception, e:
			e.Logger = releaseInfo.Logger
			raise