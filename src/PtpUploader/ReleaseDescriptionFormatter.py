import os

class ReleaseDescriptionFormatter:
	@staticmethod	
	def Format(releaseInfo, scaleSize, mediaInfos, includeReleaseName):
		screenshots = releaseInfo.GetScreenshotList()

		releaseInfo.Logger.info( "Making release description for release '%s' with screenshots at %s." % ( releaseInfo.ReleaseName, screenshots ) )
		releaseDescription = u""

		if includeReleaseName:
			releaseDescription = u"[size=4][b]%s[/b][/size]\n\n" % releaseInfo.ReleaseName

		if len( releaseInfo.ReleaseNotes ) > 0:
			releaseDescription += u"%s\n\n" % releaseInfo.ReleaseNotes

		if scaleSize is not None:
			releaseDescription += u"Screenshots are showing the display aspect ratio. Resolution: %s.\n\n" % scaleSize 

		for screenshot in screenshots:
			releaseDescription += u"[img=%s]\n\n" % screenshot

		for mediaInfo in mediaInfos:
			# Add file name before each media info if there are more than one videos in the release.
			if len( mediaInfos ) > 1:
				fileName = os.path.basename( mediaInfo.Path )
				releaseDescription += u"[size=3][u]%s[/u][/size]\n\n" % fileName

			releaseDescription += mediaInfo.FormattedMediaInfo

		# Add NFO if presents
		if len( releaseInfo.Nfo ) > 0:
			releaseDescription += u"[size=3][u]NFO[/u][/size]:[pre]\n%s\n[/pre]" % releaseInfo.Nfo

		return releaseDescription