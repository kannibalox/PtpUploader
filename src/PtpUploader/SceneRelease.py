from PtpUploaderException import PtpUploaderException

class SceneRelease:
	@staticmethod
	def GetSourceAndFormatFromSceneReleaseName(releaseInfo, releaseName):
		lowerReleaseName = releaseName.lower()
		if lowerReleaseName.find( "dvdrip.xvid" ) != -1:
			releaseInfo.Quality = "Standard Definition"
			releaseInfo.Source = "DVD"
			releaseInfo.Codec = "XviD"
			releaseInfo.ResolutionType = "Other"
		elif lowerReleaseName.find( "bdrip.xvid" ) != -1:
			releaseInfo.Quality = "Standard Definition"
			releaseInfo.Codec = "XviD"
			releaseInfo.Source = "Blu-ray"
			releaseInfo.ResolutionType = "Other"
		elif lowerReleaseName.find( "720p.bluray.x264" ) != -1:
			releaseInfo.Quality = "High Definition"
			releaseInfo.Source = "Blu-ray"
			releaseInfo.Codec = "x264"
			releaseInfo.ResolutionType = "720p"
		elif lowerReleaseName.find( "1080p.bluray.x264" ) != -1:
			releaseInfo.Quality = "High Definition"
			releaseInfo.Source = "Blu-ray"
			releaseInfo.Codec = "x264"
			releaseInfo.ResolutionType = "1080p"
		else:
			raise PtpUploaderException( "Can't figure out release source and quality from release name '%s'." % releaseName )
