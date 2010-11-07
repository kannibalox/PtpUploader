from Globals import Globals;
from ImageUploader import ImageUploader;
from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import os;
import subprocess;

class ScreenshotMaker:
	# time: string in hh:mm:ss format: "00:00:20"
	@staticmethod
	def Make(inputVideoPath, time, outputImagePath):
		Globals.Logger.info( "Making screenshot from '%s' to '%s'." % ( inputVideoPath, outputImagePath ) );
		
		# -an: disable audio
		# -sn: disable subtitle
		args = [ Settings.FfmpegPath, "-an", "-sn", "-ss", time, "-i", inputVideoPath, "-vcodec", "png", "-vframes", "1", outputImagePath ];
		errorCode = subprocess.call( args );
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) );			

	# Sorting is needed to ensure that the screenshot is taken from the first video when a release contains multiple videos.
	# We don't want to post screenshots that contains spoilers. :)
	@staticmethod
	def SortVideoFiles(files):
		filesToSort = [];
		for file in files:
			item = file.lower(), file; # Add as a tuple.
			filesToSort.append( item );

		files = [];
		filesToSort.sort();
		for item in filesToSort:
			path = item[ 1 ]; # First element is the path in lower case, second is the original path.
			files.append( path );
		
		return files;

	# Returns with the URL of the uploaded image.
	@staticmethod
	def TakeAndUploadScreenshot(videoPath, time, screenshotPath):
		ScreenshotMaker.Make( videoPath, time, screenshotPath );
		imageUrl = ImageUploader.Upload( imagePath = screenshotPath );
		os.remove( screenshotPath );
		return imageUrl;

	@staticmethod
	def __SecondsToFfmpegTime(seconds):
		return str( int( seconds ) );

	# Takes five screenshots from the first 30% of the video.
	# Returns with the URLs of the uploaded images.
	@staticmethod
	def TakeAndUploadScreenshots(videoPath, screenshotPath, durationInSec):
		urls = [];
		urls.append( ScreenshotMaker.TakeAndUploadScreenshot( videoPath, ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.10 ), screenshotPath ) );
		urls.append( ScreenshotMaker.TakeAndUploadScreenshot( videoPath, ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.15 ), screenshotPath ) );
		urls.append( ScreenshotMaker.TakeAndUploadScreenshot( videoPath, ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.20 ), screenshotPath ) );
		urls.append( ScreenshotMaker.TakeAndUploadScreenshot( videoPath, ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.25 ), screenshotPath ) );
		urls.append( ScreenshotMaker.TakeAndUploadScreenshot( videoPath, ScreenshotMaker.__SecondsToFfmpegTime( durationInSec * 0.30 ), screenshotPath ) );
		return urls;