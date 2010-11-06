# This is just a wrapper for pyWA by JohnnyFive.
# pyWA does all the hard work for us hanging on IRC. We just handle the downloads. :)

import WHATauto;

import os;
import re;
import sys;

WorkingDirectoryPath = "";
AnnouncementDirectoryPath = "";

def SendAnnouncementToPtpUploader(source, id, releaseName):
	global AnnouncementDirectoryPath;
	
	# Create the announcement file for PtpUploader.
	fileName = "[source=%s][id=%s][title=%s]" % ( source, id, releaseName );
	announcementFilePath = os.path.join( AnnouncementDirectoryPath, fileName );
	file = open( announcementFilePath, "w" );
	file.close();

def HandleGftAutoAnnouncement(announcement):
	match = re.match( r"NEW :: ([^:]+) :: ([^:]+) :: http://www\.thegft\.org/details\.php\?id=([\d]+) :: .*", announcement );
	if match is None:
		print "PtpUploaderIrcBot can't parse GFT announcement: '%s'." % announcement;
		return;

	SendAnnouncementToPtpUploader( "gft", id = match.group( 3 ), releaseName = match.group( 1 ) );

def MyDownload(downloadID, downloadType, site, location=False, network=False, target=False, retries=0, email=False, notify=False, filterName=False, announce=False, formLogin=False, sizeLimits=False, name=False):
	global AnnouncementDirectoryPath;
	global WorkingDirectoryPath;
	
	print "PtpUploaderIrcBot got a new announcement. Site: '%s'. Id: '%s'. Announcement text: '%s'." % ( site, downloadID, announce );

	# Map from pyWA to our name.
	if site == "thegft":
		site = "gft";

	if announce: # Automatic announcements come with the full announcement message.
		if site == "gft":
			HandleGftAutoAnnouncement( announce );
	else:
		if site == "manual": # Manual announcement and manual download.
			SendAnnouncementToPtpUploader( "manual", "0", downloadID ); # downloadID contains the release name
		else: # Manual announcement and automatic download.
			SendAnnouncementToPtpUploader( site, downloadID, "ManualAnnouncement" );

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
	main( sys.argv );