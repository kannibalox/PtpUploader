from NfoParser import NfoParser;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;
from Unrar import Unrar;

import fnmatch; 
import os;

class SceneRelease:
	def __init__(self, path):
		self.Path = path;
		self.Nfo = "";

	@staticmethod
	def GetSourceAndFormatFromSceneReleaseName(ptpUploadInfo, releaseName):
		lowerReleaseName = releaseName.lower();
		if lowerReleaseName.find( "dvdrip.xvid" ) != -1:
			ptpUploadInfo.Quality = "Standard Definition";
			ptpUploadInfo.Source = "DVD";
			ptpUploadInfo.Codec = "XviD"
			ptpUploadInfo.ResolutionType = "Other";
		elif lowerReleaseName.find( "bdrip.xvid" ) != -1:
			ptpUploadInfo.Quality = "Standard Definition";
			ptpUploadInfo.Codec = "XviD"
			ptpUploadInfo.Source = "Blu-Ray";
			ptpUploadInfo.ResolutionType = "Other";
		elif lowerReleaseName.find( "720p.bluray.x264" ) != -1:
			ptpUploadInfo.Quality = "High Definition";
			ptpUploadInfo.Source = "Blu-Ray";
			ptpUploadInfo.Codec = "x264"
			ptpUploadInfo.ResolutionType = "720p";
		elif lowerReleaseName.find( "1080p.bluray.x264" ) != -1:
			ptpUploadInfo.Quality = "High Definition";
			ptpUploadInfo.Source = "Blu-Ray";
			ptpUploadInfo.Codec = "x264"
			ptpUploadInfo.ResolutionType = "1080p";
		else:
			raise PtpUploaderException( "Can't figure out release source and quality from release name '%s'." % releaseName );

		ptpUploadInfo.Scene = "on";

	# return: value[ "cds" ] = CD1, CD2, ... if presents
	# value[ "subtitle" ] = subtitle directory if presents
	# value[ "nfo" ] = nfo path
	@staticmethod
	def __GetImportantDirectories(path):
		cds = [];
		subtitle = None;
		nfoPath = None;
		
		entries = os.listdir( path );
		for entry in entries:
			entryPath = os.path.join( path, entry );
			entryLower = entry.lower();

			if os.path.isdir( entryPath ):
				if fnmatch.fnmatch( entryLower, "cd*" ):
					cds.append( entryPath );
				elif fnmatch.fnmatch( entryLower, "subs" ):
					subtitle = entryPath;
			elif os.path.isfile( entryPath ):
				if fnmatch.fnmatch( entryLower, "*.nfo" ):
					nfoPath = entryPath;
		
		return { "cds": cds, "subtitle": subtitle, "nfo": nfoPath };
	
	def __ExtractVideos(self, logger, cds, destination):
		if ( len( cds ) == 0 ):
			cds.append( self.Path );
		
		logger.info( "Extracting videos from %s to '%s'." % ( cds, destination ) );
		
		for directory in cds:
			rars = Unrar.GetRars( directory );
			if len( rars ) == 1:
				Unrar.Extract( rars[ 0 ], destination );
			elif len( rars ) > 1:
				raise PtpUploaderException( "Directory '%s' contains more than one RAR." % directory );
			else:
				raise PtpUploaderException( "Directory '%s' doesn't contains any RAR files." % directory );
	
	# Subtitles may contain the uncut version too.
	def __ExtractSubtitle(self, logger, subtitlePath, destination):
		if subtitlePath is None:
			return;
				
		logger.info( "Extracting subtitle from '%s' to '%s'." % ( subtitlePath, destination ) );
		
		rars = Unrar.GetRars( subtitlePath );
		if len( rars ) == 0:
			raise PtpUploaderException( "Subtitle directory '%s' exists but doesn't contains any RAR files." % subtitlePath );
		
		for rar in rars:
			Unrar.Extract( rar, destination );

		rars = Unrar.GetRars( destination );
		for rar in rars:
			Unrar.Extract( rar, destination );
			os.remove( rar );

	def Extract(self, logger, destination):
		logger.info( "Extracting release from '%s' to '%s'." % ( self.Path, destination ) );
		
		# Get the main files.
		directories = self.__GetImportantDirectories( self.Path );
		cds = directories[ "cds" ];
		subtitleDirectory = directories[ "subtitle" ];
		nfoPath = directories[ "nfo" ];

		# Read the NFO file.
		if nfoPath is None:
			raise PtpUploaderException( "Can't find NFO in directory '%s'." % self.Path );
		
		self.Nfo = NfoParser.ReadNfoFileToUnicode( nfoPath );
		 
		self.__ExtractVideos( logger, cds, destination );
		self.__ExtractSubtitle( logger, subtitleDirectory, destination );