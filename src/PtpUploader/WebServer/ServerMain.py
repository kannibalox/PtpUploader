'''

TODO:

File selector:
	- jQuery File Tree -- http://abeautifulsite.net/blog/2008/03/jquery-file-tree/
	- jfiletree -- http://code.google.com/p/jfiletree/
	- tree
		- http://code.google.com/p/dynatree/
		- http://www.jstree.com/ -- with json data source

jQuery File Upload
https://github.com/blueimp/jQuery-File-Upload/

'''

from WebServer import app

from Authentication import requires_auth
from Database import Database
from MyGlobals import MyGlobals
from PtpUploaderMessage import *
from ReleaseInfo import ReleaseInfo

from flask import render_template, request, redirect, url_for

import os

@app.route( '/' )
@requires_auth
def index():
	return redirect( url_for( "jobs" ) )

@app.route( '/job/<int:jobId>/log/' )
@requires_auth
def log(jobId):
	releaseInfo = Database.DbSession.query( ReleaseInfo ).filter( ReleaseInfo.Id == jobId ).first()
	
	logFilePath = releaseInfo.GetLogFilePath()
	log = ""
	
	if os.path.isfile( logFilePath ):
		file = open( logFilePath )
		log = file.read()
		file.close()
	else:
		log = "Log file '%s' doesn't exists!" % logFilePath

	log = log.replace( "\n", r"<br>" )

	return log

@app.route( "/quit" )
@requires_auth
def quit():
	MyGlobals.PtpUploader.AddMessage( PtpUploaderMessageQuit() )

	func = request.environ.get( 'werkzeug.server.shutdown' )
	func()

	return "Quitting."