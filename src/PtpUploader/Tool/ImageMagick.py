from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os
import subprocess

class ImageMagick:
	@staticmethod
	def ConvertImageToJpg(logger, sourceImagePath, outputImagePath):
		logger.info( "Converting image from '%s' to '%s'." % ( sourceImagePath, outputImagePath ) )

		if not os.path.isfile( sourceImagePath ):
			raise PtpUploaderException( "Can't read source image '%s' for JPG conversion." % sourceImagePath )

		if os.path.exists( outputImagePath ):
			raise PtpUploaderException( "Can't convert image to JPG because file '%s' already exists." % outputImagePath )

		args = [ Settings.ImageMagickConvertPath, sourceImagePath, "-quality", "97", outputImagePath ]
		errorCode = subprocess.call( args )
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )

	@staticmethod
	def IsEnabled():
		return len( Settings.ImageMagickConvertPath ) > 0