from ImageUploader import ImageUploader
from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os
import re
import subprocess

class ScreenshotMaker:
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

		# Formatting can be one of the following:		
		# Stream #0.0(eng): Video: h264, yuv420p, 1280x544, PAR 1:1 DAR 40:17, 24 tbr, 1k tbn, 48 tbc
		# Stream #0.0[0x1e0]: Video: mpeg2video, yuv420p, 720x480 [PAR 8:9 DAR 4:3], 7500 kb/s, 29.97 tbr, 90k tbn, 59.94 tbc
		match = re.search( r"(\d+)x(\d+), PAR (\d+):(\d+) DAR", result )
		if match is None:
			match = re.search( r"(\d+)x(\d+) \[PAR (\d+):(\d+) DAR", result )
		if match is None:
			return
			
		width = int( match.group( 1 ) )
		height = int( match.group( 2 ) )
		parX = int( match.group( 3 ) )
		parY = int( match.group( 4 ) )
		# We ignore invalid resolutions, invalid aspect ratios and aspect ratio 1:1.			
		if width <= 0 or height <= 0 or parX <= 0 or parY <= 0 or ( parX == 1 and parY == 1 ):
			return
		
		width = ( width * parX ) / parY
		width = int( width )

		# For FFmpeg frame size must be a multiple of 2.
		if ( width % 2 ) != 0:
			width += 1

		self.ScaleSize = "%sx%s" % ( width, height )

	# time: string in hh:mm:ss format: "00:00:20"
	def MakeScreenshotInPng(self, time, outputImagePath):
		self.Logger.info( "Making screenshot from '%s' to '%s'." % ( self.InputVideoPath, outputImagePath ) )
		
		# -an: disable audio
		# -sn: disable subtitle
		args = []
		if self.ScaleSize is None:
			args = [ Settings.FfmpegPath, "-an", "-sn", "-ss", time, "-i", self.InputVideoPath, "-vcodec", "png", "-vframes", "1", outputImagePath ]
		else:
			self.Logger.info( "Pixel aspect ratio wasn't 1:1, scaling video to resolution: '%s'." % self.ScaleSize )			
			args = [ Settings.FfmpegPath, "-an", "-sn", "-ss", time, "-i", self.InputVideoPath, "-vcodec", "png", "-vframes", "1", "-s", self.ScaleSize, outputImagePath ]

		errorCode = subprocess.call( args )
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )			

	def ConvertImageToJpg(self, sourceImagePath, outputImagePath):
		self.Logger.info( "Converting image from '%s' to '%s'." % ( sourceImagePath, outputImagePath ) )

		try:
			args = [ Settings.ImageMagickConvertPath, sourceImagePath, "-quality", "97", outputImagePath ]
			errorCode = subprocess.call( args )
			if errorCode != 0:
				raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )
		except Exception:
			self.Logger( "Got exception while trying to execute process '%s'." % args )
			raise

	# time: string in hh:mm:ss format: "00:00:20"
	def Make(self, time, outputImagePathWithoutExtension):
		outputPngPath = outputImagePathWithoutExtension + ".png"
		self.MakeScreenshotInPng( time, outputPngPath )
		
		if len( Settings.ImageMagickConvertPath ) > 0:
			outputJpgPath = outputImagePathWithoutExtension + ".jpg"
			self.ConvertImageToJpg( outputPngPath, outputJpgPath )
			os.remove( outputPngPath )
			return outputJpgPath
		else:
			return outputPngPath

	# We sort video files by their size (less than 50 MB difference is ignored) and by their name.
	# Sorting by name is needed to ensure that the screenshot is taken from the first video to avoid spoilers when a release contains multiple videos.
	# Sorting by size is needed to ensure that we don't take the screenshots from the sample or extras included.
	# Ignoring less than 50 MB differnece is needed to make sure that CD1 will be sorted before CD2 even if CD2 is larger than CD1 by 49 MB.   
	@staticmethod
	def SortVideoFiles(files):
		class SortItem:
			def __init__(self, path):
				self.Path = path
				self.LowerPath = path.lower()
				self.Size = os.path.getsize( path )

			@staticmethod
			def Compare( item1, item2 ):
				sizeDifference = item1.Size - item2.Size 
				if abs( sizeDifference ) > ( 50 * 1024 * 1024 ):
					if item1.Size > item2.Size:
						return -1
					else:
						return 1

				if item1.LowerPath < item2.LowerPath:
					return -1
				elif item1.LowerPath > item2.LowerPath:
					return 1
				else:
					return 0

		filesToSort = []
		for file in files:
			item = SortItem( file )
			filesToSort.append( item )

		filesToSort.sort( cmp = SortItem.Compare )

		files = []
		for item in filesToSort:
			files.append( item.Path )

		return files

	# Returns with the URL of the uploaded image.
	def __TakeAndUploadScreenshot(self, time, screenshotPathWithoutExtension):
		screenshotPath = self.Make( time, screenshotPathWithoutExtension )
		imageUrl = ImageUploader.Upload( self.Logger, imagePath = screenshotPath )
		os.remove( screenshotPath )
		return imageUrl

	@staticmethod
	def __SecondsToFfmpegTime(seconds):
		return str( int( seconds ) )

	# Takes five screenshots from the first 30% of the video.
	# Returns with the URLs of the uploaded images.
	def TakeAndUploadScreenshots(self, screenshotPathWithoutExtension, durationInSec):
		urls = []
		urls.append( self.__TakeAndUploadScreenshot( ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.10 ), screenshotPathWithoutExtension ) )
		urls.append( self.__TakeAndUploadScreenshot( ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.15 ), screenshotPathWithoutExtension ) )
		urls.append( self.__TakeAndUploadScreenshot( ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.20 ), screenshotPathWithoutExtension ) )
		urls.append( self.__TakeAndUploadScreenshot( ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.25 ), screenshotPathWithoutExtension ) )
		urls.append( self.__TakeAndUploadScreenshot( ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.30 ), screenshotPathWithoutExtension ) )
		return urls