from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import re;
import subprocess;

class MediaInfo:
	def __init__(self, logger, path):
		self.Path = path;
		self.FormattedMediaInfo = "";
		self.DurationInSec = 0;
		self.Container = "";
		self.Codec = "";
		self.Width = 0;
		self.Height = 0;
		
		self.__ParseMediaInfo( logger )

	# Returns with the media info.
	@staticmethod
	def ReadMediaInfo(logger, path):
		logger.info( "Reading media info from '%s'." % path );
		
		args = [ Settings.MediaInfoPath, path ];
		proc = subprocess.Popen( args, stdout = subprocess.PIPE );
		stdout, stderr = proc.communicate();
		errorCode = proc.wait();
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) );			
		
		return stdout.decode( "utf-8", "ignore" );
	
	# Returns with the media infos.
	@staticmethod
	def ReadAndParseMediaInfos(logger, videoFiles):
		mediaInfos = [];
		for video in videoFiles:
			mediaInfo = MediaInfo( logger, video );
			mediaInfos.append( mediaInfo );
			
		return mediaInfos;

	@staticmethod
	def __ParseSize(mediaPropertyValue):
		mediaPropertyValue = mediaPropertyValue.replace( "pixels", "" );
		mediaPropertyValue = mediaPropertyValue.replace( " ", "" ); # Resolution may contain space, so remove. Eg.: 1 280
		return int( mediaPropertyValue );

	# Matches duration in the following format. All units and spaces are optional.
	# 1h 2mn 3s
	@staticmethod
	def __GetDurationInSec(duration):
		# Nice regular expression. :)
		# r means to do not unescape the string
		# ?: means to do not store that group capture
		match = re.match( r"(?:(\d+)h\s?)?(?:(\d+)mn\s?)?(?:(\d+)s\s?)?" , duration )
		if not match:
			return 0;
	
		duration = 0;
		if match.group( 1 ):
			duration += int( match.group( 1 ) ) * 60 * 60;
		if match.group( 2 ):
			duration += int( match.group( 2 ) ) * 60;
		if match.group( 3 ):
			duration += int( match.group( 3 ) );
		
		return duration;		

	def __ParseMediaInfo(self, logger):
		mediaInfoText = MediaInfo.ReadMediaInfo( logger, self.Path );

		section = "";
		for line in mediaInfoText.splitlines():
			if line.find( ":" ) == -1:
				if len( line ) > 0:
					section = line;
					line = "[b]" + line + "[/b]";
			else:
				mediaPropertyName, separator, mediaPropertyValue = line.partition( ": " );
				mediaPropertyName = mediaPropertyName.strip();

				if section == "General":
					if mediaPropertyName == "Complete name":
						continue; # Do not include complete name. Filename will be before the media info dump.
					elif mediaPropertyName == "Format":
						self.Container = mediaPropertyValue.lower();
					elif mediaPropertyName == "Duration":
						self.DurationInSec = MediaInfo.__GetDurationInSec( mediaPropertyValue );
				elif section == "Video":
					if mediaPropertyName == "Codec ID":
						self.Codec = mediaPropertyValue.lower();
					elif mediaPropertyName == "Width":
						self.Width = MediaInfo.__ParseSize( mediaPropertyValue );
					elif mediaPropertyName == "Height":
						self.Height = MediaInfo.__ParseSize( mediaPropertyValue );

			self.FormattedMediaInfo += line + "\n";
			
	def IsAvi(self):
		return self.Container == "avi";

	def IsMkv(self):
		return self.Container == "matroska";

	def IsDivx(self):
		return self.Codec == "dx50";
	
	def IsXvid(self):
		return self.Codec == "xvid";

	def IsX264(self):
		return self.Codec == "v_mpeg4/iso/avc";