from ImageHost.ImageUploader import ImageUploader
from Tool.ImageMagick import ImageMagick
from Tool.Ffmpeg import Ffmpeg
from Tool.Mplayer import Mplayer
from Tool.Mpv import Mpv

from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os

class ScreenshotMaker:
	def __init__(self, logger, inputVideoPath):
		self.Logger = logger

		self.InternalScreenshotMaker = None

		if Settings.IsMpvEnabled():
			self.InternalScreenshotMaker = Mpv( logger, inputVideoPath )
		elif Settings.IsMplayerEnabled():
			self.InternalScreenshotMaker = Mplayer( logger, inputVideoPath )
		else:
			self.InternalScreenshotMaker = Ffmpeg( logger, inputVideoPath )

	def GetScaleSize(self):
		return self.InternalScreenshotMaker.ScaleSize

	def __MakeUsingMplayer( self, timeInSeconds, outputImageDirectory ):
		return self.InternalScreenshotMaker.MakeScreenshotInPng( timeInSeconds, outputImageDirectory )

	def __MakeUsingMpv( self, timeInSeconds, outputImageDirectory ):
		outputPngPath = os.path.join( outputImageDirectory, "00000001.png" )
		self.InternalScreenshotMaker.MakeScreenshotInPng( timeInSeconds, outputPngPath )
		return outputPngPath

	def __MakeUsingFfmpeg( self, timeInSeconds, outputImageDirectory ):
		outputPngPath = os.path.join( outputImageDirectory, "00000001.png" )
		self.InternalScreenshotMaker.MakeScreenshotInPng( timeInSeconds, outputPngPath )
		return outputPngPath

	# Returns with the URL of the uploaded image.
	def __TakeAndUploadScreenshot(self, timeInSeconds, outputImageDirectory):
		screenshotPath = None

		if Settings.IsMpvEnabled():
			screenshotPath = self.__MakeUsingMpv( timeInSeconds, outputImageDirectory )
		elif Settings.IsMplayerEnabled():
			screenshotPath = self.__MakeUsingMplayer( timeInSeconds, outputImageDirectory )
		else:
			screenshotPath = self.__MakeUsingFfmpeg( timeInSeconds, outputImageDirectory )

		if ImageMagick.IsEnabled():
			ImageMagick.OptimizePng( self.Logger, screenshotPath )

		try:
			imageUrl = ImageUploader.Upload( self.Logger, imagePath = screenshotPath )
		finally:
			os.remove( screenshotPath )

		return imageUrl

	# Takes maximum five screenshots from the first 30% of the video.
	# Returns with the URLs of the uploaded images.
	def TakeAndUploadScreenshots(self, outputImageDirectory, durationInSec, numberOfScreenshotsToTake):
		urls = []

		if numberOfScreenshotsToTake > 5:
			numberOfScreenshotsToTake = 5

		for i in range(numberOfScreenshotsToTake ):
			position = 0.10 + ( i * 0.05 )
			urls.append( self.__TakeAndUploadScreenshot( int( durationInSec * position ), outputImageDirectory ) )

		return urls

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
				ignoreSizeDifference = 50 * 1024 * 1024
				sizeDifference = item1.Size - item2.Size 
				if abs( sizeDifference ) > ignoreSizeDifference:
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
