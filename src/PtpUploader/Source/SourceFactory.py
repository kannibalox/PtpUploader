from Cinemageddon import Cinemageddon;
from Gft import Gft;
from Manual import Manual;

# A source have to support the following methods:
# Login, PrepareDownload, DownloadTorrent, ExtractRelease and IsSingleFileTorrentNeedsDirectory.
class SourceFactory:
	@staticmethod
	def GetSource(announcement):
		if announcement.AnnouncementSourceName == "cg":
			return Cinemageddon;
		elif announcement.AnnouncementSourceName == "gft":
			return Gft;
		elif announcement.AnnouncementSourceName == "manual":
			return Manual;
		
		return None;