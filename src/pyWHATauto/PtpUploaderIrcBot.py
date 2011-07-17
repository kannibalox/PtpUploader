# This is just a wrapper for pyWA by JohnnyFive.
# pyWA does all the hard work for us hanging on IRC. We just handle the downloads. :)

import WHATauto

import os
import re
import sys
import threading

WorkingDirectoryPath = ""
AnnouncementDirectoryPath = ""

class AnnouncementFileWriter:
	def __init__(self, path):
		self.Path = path
		
	def Write(self):
		file = open( self.Path, "w" )
		file.close()

def SendAnnouncementToPtpUploader(source, id, releaseName):
	global AnnouncementDirectoryPath
	
	# Create the announcement file for PtpUploader.
	fileName = "[source=%s][id=%s][title=%s]" % ( source, id, releaseName )
	announcementFilePath = os.path.join( AnnouncementDirectoryPath, fileName )
	announcementFileWriter = AnnouncementFileWriter( announcementFilePath )

	# TODO: make a config for delaying instead of this quick hack.
	#if releaseName.lower().find( "720p" ) == -1:
	announcementFileWriter.Write()
	#else:
	#	print "Delaying release '%s' by one hour." % releaseName
	#	timer = threading.Timer( 90 * 60, announcementFileWriter.Write )
	#	timer.start()

# TODO: the announcement parsing in pyWHATauto already parser the regex, would be nice to use that instead of these.

def HandleGftAutoAnnouncement(announcement):
	match = re.match( r"NEW :: ([^:]+) :: ([^:]+) :: http://www\.thegft\.org/details\.php\?id=([\d]+) :: .*", announcement );
	if match is None:
		print "PtpUploaderIrcBot can't parse GFT announcement: '%s'." % announcement;
		return;

	SendAnnouncementToPtpUploader( "gft", id = match.group( 3 ), releaseName = match.group( 1 ) );

def HandleSceneAccessAutoAnnouncement(announcement):
	match = re.match( r"""NEW in (.*?): -> (.*?) \(Uploaded (.*?) after pre\) - \((.*?)\) - .*?id=(\d+)""", announcement )
	if match is None:
		print "PtpUploaderIrcBot can't parse SCC announcement: '%s'." % announcement
		return;

	SendAnnouncementToPtpUploader( "scc", id = match.group( 5 ), releaseName = match.group( 2 ) )

def HandleTorrentLeechAutoAnnouncement(announcement):
	match = re.match( r"New Torrent Announcement: <([^>]*)>[\W]*Name:'([^']*)[\W]*uploaded by '([^']*)' -\W+http://www.torrentleech.org/torrent/(\d+)", announcement );
	if match is None:
		print "PtpUploaderIrcBot can't parse TL announcement: '%s'." % announcement;
		return;

	SendAnnouncementToPtpUploader( "tl", id = match.group( 4 ), releaseName = match.group( 2 ) );

def MyDownload(downloadID, downloadType, site, location=False, network=False, target=False, retries=0, email=False, notify=False, filterName=False, announce=False, formLogin=False, sizeLimits=False, name=False):
	global AnnouncementDirectoryPath;
	global WorkingDirectoryPath;
	
	print "PtpUploaderIrcBot got a new announcement. Site: '%s'. Id: '%s'. Announcement text: '%s'." % ( site, downloadID, announce );

	if announce: # Automatic announcements come with the full announcement message.
		if site == "thegft":
			HandleGftAutoAnnouncement( announce )
		elif site == "sceneaccess":
			HandleSceneAccessAutoAnnouncement( announce )
		elif site == "torrentleech":
			HandleTorrentLeechAutoAnnouncement( announce )

def main(argv):
	global AnnouncementDirectoryPath;
	global WorkingDirectoryPath;

	if len( argv ) != 2:
		print "Usage: PtpUploaderIrcBot [working directory of PtpUploader]";
		return;

	# Check the working directory.
	WorkingDirectoryPath = argv[ 1 ];
	if not os.path.exists( WorkingDirectoryPath ):
		print "Working directory '%s' doesn't exists." % WorkingDirectoryPath;
		return;

	# Check the announcement directory.
	AnnouncementDirectoryPath = os.path.join( WorkingDirectoryPath, "announcement" );
	if not os.path.exists( AnnouncementDirectoryPath ):
		print "Announcement directory '%s' doesn't exists." % AnnouncementDirectoryPath;
		return;

	# Replace download function with ours.
	WHATauto.download = MyDownload;
	WHATauto.main();

if __name__ == '__main__':
	#main( sys.argv );
	main( [ "", "d:\\source\\ptp test\\WorkingDirectory" ] );