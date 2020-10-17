from ..PtpUploaderException import PtpUploaderException
from ..Settings import Settings

import os
import subprocess

class Mpv:
	def __init__( self, logger, inputVideoPath ):
		self.Logger = logger
		self.InputVideoPath = inputVideoPath
		self.ScaleSize = None

	def MakeScreenshotInPng( self, timeInSeconds, outputPngPath ):
		self.Logger.info( "Making screenshot with mpv from '%s' to '%s'." % ( self.InputVideoPath, outputPngPath ) )

		if os.path.exists( outputPngPath ):
			raise PtpUploaderException( "Can't create screenshot because file '%s' already exists." % outputPngPath )

		args = [ Settings.MpvPath,
			"--no-config",
			"--no-audio",
			"--no-sub",
			"--start=" + str( int( timeInSeconds ) ),
			"--frames=1",
			"--screenshot-format=png",
			"--screenshot-png-compression=9", # doesn't seem to be working
			"--vf=scale=0:0", # 0: scaled d_width/d_height
			"--o=" + outputPngPath,
			self.InputVideoPath ]

		errorCode = subprocess.call( args )
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) )
