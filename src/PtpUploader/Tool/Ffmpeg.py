from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os
import re
import subprocess

class Ffmpeg:
	def __init__(self, logger, inputVideoPath):
		self.Logger = logger
		self.InputVideoPath = inputVideoPath
		self.ScaleSize = None
		
		self.__CalculateSizeAccordingToAspectRatio()

	def __CalculateSizeAccordingToAspectRatio(self):
		# Get resolution and pixel aspect ratio from FFmpeg.
		args = [ Settings.FfmpegPath, "-i", self.InputVideoPath ]
		proc = subprocess.Popen( args, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
		stdout, stderr = proc.communicate()
		proc.wait()
		result = stderr.decode( "utf-8", "ignore" )

		# Formatting can be one of the following. PAR can be SAR too.
		# Stream #0.0(eng): Video: h264, yuv420p, 1280x544, PAR 1:1 DAR 40:17, 24 tbr, 1k tbn, 48 tbc
		# Stream #0.0[0x1e0]: Video: mpeg2video, yuv420p, 720x480 [PAR 8:9 DAR 4:3], 7500 kb/s, 29.97 tbr, 90k tbn, 59.94 tbc
		match = re.search( r"(\d+)x(\d+), [SP]AR \d+:\d+ DAR (\d+):(\d+)", result )
		if match is None:
			match = re.search( r"(\d+)x(\d+) \[[SP]AR \d+:\d+ DAR (\d+):(\d+)", result )
		if match is None:
			return
			
		width = int( match.group( 1 ) )
		height = int( match.group( 2 ) )
		darX = int( match.group( 3 ) )
		darY = int( match.group( 4 ) )
		# We ignore invalid resolutions, invalid aspect ratios and aspect ratio 1:1.			
		if width <= 0 or height <= 0 or darX <= 0 or darY <= 0 or ( darX == 1 and darY == 1 ):
			return
		
		newWidth = ( height * darX ) / darY
		newWidth = int( newWidth )
		if abs( newWidth - width ) <= 1:
			return

		# For FFmpeg frame size must be a multiple of 2.
		if ( newWidth % 2 ) != 0:
			newWidth += 1

		self.ScaleSize = "%sx%s" % ( newWidth, height )

	def MakeScreenshotInPng(self, timeInSeconds, outputPngPath):
		self.Logger.info( "Making screenshot with ffmpeg from '%s' to '%s'." % ( self.InputVideoPath, outputPngPath ) )

		if os.path.exists( outputPngPath ):
			raise PtpUploaderException( "Can't create screenshot because file '%s' already exists." % outputPngPath )

		# -an: disable audio
		# -sn: disable subtitle
		args = []
		time = str( int( timeInSeconds ) )
		if self.ScaleSize is None:
			args = [ Settings.FfmpegPath, "-an", "-sn", "-ss", time, "-i", self.InputVideoPath, "-vcodec", "png", "-vframes", "1", outputPngPath ]
		else:
			self.Logger.info( "Pixel aspect ratio wasn't 1:1, scaling video to resolution: '%s'." % self.ScaleSize )			
			args = [ Settings.FfmpegPath, "-an", "-sn", "-ss", time, "-i", self.InputVideoPath, "-vcodec", "png", "-vframes", "1", "-s", self.ScaleSize, outputPngPath ]

		errorCode = subprocess.call( args )
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )

	@staticmethod
	def IsEnabled():
		return len( Settings.FfmpegPath ) > 0