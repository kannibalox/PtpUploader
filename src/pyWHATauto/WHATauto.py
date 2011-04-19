#! /usr/bin/env python
# -*- coding: UTF-8 -*-
#python 2.5 support for the "with" command
from __future__ import with_statement

print 'Starting main program.'
print 'pyWHATauto: johnnyfive. WHATauto original creator: mlapaglia.'

import sys
if sys.version_info < (2, 6) and sys.version_info >= (2, 5):
    try:
        #more support for 2.5
        import irclib25 as irclib
        import globals25 as G
        import handlePubMSG25 as handlePubMSG
        print 'You are using python 2.5. Support for this version thanks to yots.'
    except ImportError, e:
        print 'ERROR: There was an error importing a required module. Please re-download pyWA.'
        var = raw_input("This program will now exit (okay): ")
        quit()

elif sys.version_info >= (2, 6):
    try:
        import irclib26 as irclib
        import globals26 as G
        import handlePubMSG26 as handlePubMSG
    except ImportError, e:
        print 'ERROR: There was an error importing a required module. Please re-downloakd pyWA.'
        var = raw_input("This program will now exit (okay): ")
        quit()

VERSION = 'v1.291'

print 'You are running pyWHATauto version %s\n'%VERSION

#from time import strftime, strptime
from datetime import datetime, timedelta
from decimal import Decimal
import db, web, time, os, re, htmllib, ConfigParser, threading, thread, urllib, urllib2, datetime, random, cookielib, socket#, WHATparse as WP

def main():
    global irc, log, lastFSCheck, last
    last = False
    lastFSCheck = False
    os.chdir(G.SCRIPTDIR)
    loadConfigs()
    if G.LOG:
        if not os.path.isdir(os.path.join(G.SCRIPTDIR,'logs')):
            os.makedirs(os.path.join(G.SCRIPTDIR,'logs'))
        log = False
    global WIN32FILE
    WIN32FILE = False
    if os.name == 'nt':
        try:
            import win32file
            WIN32FILE = True
        except ImportError:
            out('ERROR','The module win32file is not installed. Please download it from http://sourceforge.net/projects/pywin32/files/')
            out('ERROR','The program will continue to function normally except where win32file is needed.')
            WIN32FILE = False
    out('DEBUG','Starting report thread.\n')        
    thread.start_new_thread(writeReport,(20,))
    out('DEBUG','Report thread started.\n')
    
	# TnS: we don't need the database.
    #out('DEBUG','Starting DB thread.\n')  
    #Create the DB object
    #DB = db.sqlDB(G.SCRIPTDIR, G.Q)
    #DB.setDaemon(True)
    #DB.start()
    #out('DEBUG','DB thread started.\n')
    
	# TnS: we don't need the WebUI.
    #out('DEBUG','Starting web thread.\n')  
    #Create the web object
    #try:
    #    WEB = web.WebServer(G.SCRIPTDIR, SETUP.get('setup','password'), SETUP.get('setup','port'))
    #except Exception, e:
    #    print e.message
    #WEB.setDaemon(True)
    #WEB.start()
    #out('DEBUG','Web thread started.\n')
    
    irc = irclib.IRC()
    out('INFO','Main program loaded. Starting bots.\n')
    
    if G.TESTING:
        startBots()
    else:
        thread.start_new_thread(startBots,(tuple()))
    
    Prompt(.5) 
        
def Prompt(n):
    global log
    while 1:
        time.sleep(n)
        if G.EXIT:
            print 'Exiting.'
            if G.LOG:
                log.close()
            sys.exit(1)
        
def loadConfigs():
    global REGEX, SETUP, CRED, FILTERS, CUSTOM, ALIASES#, REPORTS , NETWORKS
    REPORT = ConfigParser.RawConfigParser()
    REPORT.readfp(open(os.path.join(G.SCRIPTDIR,'reports.conf')))
    
    REGEX = ConfigParser.RawConfigParser()
    REGEX.readfp(open(os.path.join(G.SCRIPTDIR,'regex.conf')))
    
    SETUP = ConfigParser.RawConfigParser()
    SETUP.readfp(open(os.path.join(G.SCRIPTDIR,'setup.conf')))
    
    CRED = ConfigParser.RawConfigParser()
    CRED.readfp(open(os.path.join(G.SCRIPTDIR,'credentials.conf')))
    
    CUSTOM = ConfigParser.RawConfigParser()
    CUSTOM.readfp(open(os.path.join(G.SCRIPTDIR,'custom.conf')))
    
    FILTERS = ConfigParser.RawConfigParser()
    try:
        FILTERS.readfp(open(os.path.join(G.SCRIPTDIR,'filters.conf')))
    except ConfigParser.ParsingError, e:
        out('ERROR','There is a problem with your filters.conf. If using newlines, please make sure that each new line is tabbed in once. Error: %s'%e)
        var = raw_input("This program will now exit (okay): ")
        quit()
    
    
    if SETUP.has_option('debug', 'testing'):
        if SETUP.get('debug', 'testing').rstrip().lstrip() == '1':
            G.TESTING = True
            
    if SETUP.has_option('setup','log'):
        if SETUP.get('setup','log').rstrip().lstrip() == '1':
            G.LOG = True
    
    #load the reports. Since we re-write the entire file every time, we have to load them all.
    for site in REPORT.sections():
        G.REPORTS[site] = dict()
        G.REPORTS[site]['seen'] = int(REPORT.get(site, 'seen'))
        G.REPORTS[site]['downloaded'] = int(REPORT.get(site, 'downloaded'))
        
    for net, ali in SETUP.items('aliases'):
        G.ALIAS[ali] = net
        
    for net, ali in CUSTOM.items('aliases'):
        G.ALIAS[ali] = net
        
    if REGEX.has_option('version','version'):
        G.REGVERSION = int(REGEX.get('version','version'))

    for configs in CRED.sections(): #for network in credentials.conf
#        for key, value in CRED.items(configs):
        #if the REPORTS.conf is missing this network, add it!
        if not G.REPORTS.has_key(configs):
            G.REPORTS[configs] = dict()
            G.REPORTS[configs]['seen'] = 0
            G.REPORTS[configs]['downloaded'] = 0
            
        G.NETWORKS[configs] = dict()
        G.NETWORKS[configs]['creds'] = dict()
        for key, value in CRED.items(configs):
            G.NETWORKS[configs]['creds'][key] = value
            
        G.NETWORKS[configs]['regex'] = dict()
        
        if REGEX.has_section(configs):
            for key, value in REGEX.items(configs):
                G.NETWORKS[configs]['regex'][key] = value
            
        if CUSTOM.has_section(configs):
            for key, value in CUSTOM.items(configs):
                G.NETWORKS[configs]['regex'][key] = value
                
        G.NETWORKS[configs]['setup'] = dict()
        for key, value in SETUP.items('setup'):
            G.NETWORKS[configs]['setup'][key] = value

        G.NETWORKS[configs]['notif'] = dict()
        for key, value in SETUP.items('notification'):
            G.NETWORKS[configs]['notif'][key] = value
            
        G.NETWORKS[configs]['aliases'] = dict()
        for key, value in SETUP.items('aliases'):
            G.NETWORKS[configs]['aliases'][key] = value
        for key, value in CUSTOM.items('aliases'):
            G.NETWORKS[configs]['aliases'][key] = value
            
        G.NETWORKS[configs]['filters'] = dict()
        for f in FILTERS.sections():
            if FILTERS.get(f, 'site') == configs:
                G.NETWORKS[configs]['filters'][f] = dict()
                for key, value in FILTERS.items(f):
                    G.NETWORKS[configs]['filters'][f][key] = value
                #load the filter state into the filters dictionary
                G.FILTERS[f.lower()] = FILTERS.get(f, 'active')
                #if the filter has been manually toggled, load that value instead
                if f.lower() in G.FILTERS_CHANGED:
                    G.NETWORKS[configs]['filters'][f]['active'] = G.FILTERS_CHANGED[f.lower()]                       
    
def reloadConfigs():
    global SITES
    loadConfigs()
    for key,bot in G.RUNNING.items():
        bot.saveNewConfigs(G.NETWORKS[bot.getBotName()])
    out('INFO','Configs re-loaded.')

def out(level, msg, site=False):
    global last, log
    levels = ['error','msg','info','cmd','filter','debug']
    #getting color output ready for when I decide to implement it
    colors = {'error':'%s','msg':'%s','info':'%s','cmd':'%s','filter':'%s','debug':'%s'}
    if levels.index(level.lower()) <= levels.index(SETUP.get('setup','verbosity').lower()):
        if site:
            if site != last and last != False:
                print '\r'
                if G.LOG:
                    logging('\n')
            if SETUP.has_option('aliases', site):
                msg = '%s:[%s]%s' %(level,SETUP.get('aliases', site), msg)
                print colors[level.lower()]%msg
            else:
                msg='%s:[%s]%s' %(level,site, msg)
                print msg
            last = site
        else:
            msg='%s: %s' %(level, msg)
            print msg
        if G.LOG:
            logging(msg)

def logging(msg):
    global log, logdate
    #Create the log file
    logdir = os.path.join(G.SCRIPTDIR,'logs')
    if not log:
        logdate = datetime.datetime.now().strftime("%m.%d.%Y-%I.%M")
        log = open(os.path.join(logdir,'pyWALog-'+logdate+'.txt'),'w')
        x= datetime.datetime.strptime(logdate,"%m.%d.%Y-%I.%M")
    if datetime.datetime.now() - datetime.datetime.strptime(logdate,"%m.%d.%Y-%I.%M") > timedelta(hours=24):
        log.close()
        logdate = datetime.datetime.now().strftime("%m.%d.%Y-%I.%M")
        log = open(os.path.join(logdir,'pyWALog-'+logdate+'.txt'),'w')    
    log.write(msg+"\n")
    log.flush() 

def startBots():
    G.LOCK.acquire()
    global SETUP, CUSTOM
    for key in G.NETWORKS.keys():
        if SETUP.has_option('sites', key) and SETUP.get('sites', key).lstrip().rstrip() == '1':
            G.RUNNING[key] = autoBOT(key,G.NETWORKS[key])
        elif CUSTOM.has_option('sites', key) and CUSTOM.get('sites', key).lstrip().rstrip() == '1':
            G.RUNNING[key]=autoBOT(key,G.NETWORKS[key])
    G.LOCK.release()
    
    started=dict()
    
    for key, network in G.RUNNING.items():
        if started.has_key(network.regex['server']):
            network.setSharedConnection(G.RUNNING[started[network.regex['server']]].connection)
        else:
            started[network.regex['server']] = key
            network.connect()
        
    thread.start_new_thread(irc.process_forever(),(tuple()))
    
def writeReport(n):
    while 1:
        last = None
        G.LOCK.acquire()
        if last != G.REPORTS:
            config = ConfigParser.RawConfigParser()
            for section in G.REPORTS.keys():
                config.add_section(section)
                config.set(section,'seen',G.REPORTS[section]['seen'])
                config.set(section,'downloaded',G.REPORTS[section]['downloaded'])
            #release the lock before we waste time writing the config.
            G.LOCK.release()
            # Writing our configuration file to 'reports.conf'
            try:
                with open('reports.conf', 'wb') as configfile:
                        config.write(configfile)
                last = G.REPORTS
            except IOError, e:
                out('ERROR',e)          
        else:
            G.LOCK.release()
        #have the thread sleep for 10 seconds. no need to write this any more actively than that.
        time.sleep(n)

def tokenize(text, match=re.compile("([idel])|(\d+):|(-?\d+)").match):
    i = 0
    while i < len(text):
        m = match(text, i)
        s = m.group(m.lastindex)
        i = m.end()
        if m.lastindex == 2:
            yield "s"
            yield text[i:i+int(s)]
            i = i + int(s)
        else:
            yield s

def decode_item(next, token):
    if token == "i":
        # integer: "i" value "e"
        data = int(next())
        if next() != "e":
            raise ValueError
    elif token == "s":
        # string: "s" value (virtual tokens)
        data = next()
    elif token == "l" or token == "d":
        # container: "l" (or "d") values "e"
        data = []
        tok = next()
        while tok != "e":
            data.append(decode_item(next, tok))
            tok = next()
        if token == "d":
            data = dict(zip(data[0::2], data[1::2]))
    else:
        raise ValueError
    return data

def decode(text):
    try:
        src = tokenize(text)
        data = decode_item(src.next, src.next())
        for token in src: # look for more tokens
            raise SyntaxError("trailing junk")
    except (AttributeError, ValueError, StopIteration):
        raise SyntaxError("syntax error")
    return data

def convertDriveSizes(size, denom):
    if denom.lower() == 'k':
        return float(size)/1024.0/1024.0
    if denom.lower() == 'm':
        return float(size)/1024.0
    if denom.lower() == 'g':
        return float(size)
    if denom.lower() == 't':
        return float(size)*1024.0
        
def getDriveInfo(drive):
    if os.name == 'nt' and WIN32FILE:
        def get_drivestats(drive=None):
            '''
            returns total_space, free_space and drive letter
            '''
            drive = drive.replace(':\\', '')
            sectPerCluster, bytesPerSector, freeClusters, totalClusters = \
                win32file.GetDiskFreeSpace(drive + ":\\")
            total_space = totalClusters*sectPerCluster*bytesPerSector
            free_space = freeClusters*sectPerCluster*bytesPerSector
            return total_space, free_space
        total_space, free_space = get_drivestats(drive)
        return free_space, float(free_space)/float(total_space)
    elif os.name == 'posix':
        if SETUP.has_option('setup','limit') and SETUP.get('setup','limit').lstrip().rstrip() != '' and SETUP.get('setup','limit').lstrip().rstrip() != '0':
            import subprocess, shlex
            args = shlex.split('du -sh %s'%drive)
            du = subprocess.Popen(args,stdout=subprocess.PIPE)
            dureturn = du.communicate()[0]
            m = re.search('([\d]+)(T|G|K|M).*',dureturn)
            used = convertDriveSizes(m.group(1),m.group(2))
            free = float(SETUP.get('setup','limit'))-used
            return free, free/float(SETUP.get('setup','limit'))
        else:
            try:
                s = os.statvfs(drive) 
                return (float(s.f_bavail)*float(s.f_bsize))/1024/1024/1024, (float(s.f_bavail)/float(s.f_blocks))
            except OSError, e:
                print e
    else:
        return 1.00,1.00


lastFSCheck = False
def freeSpaceOK():
    global lastFSCheck
    drive = SETUP.get('setup', 'drive')
    limit = SETUP.get('setup', 'freepercent')
    if lastFSCheck == False:
        lastFSCheck = datetime.datetime.now()
    elif datetime.datetime.now()-lastFSCheck > datetime.timedelta(seconds=900):
        #if we haven't run this check in the last 15 minutes, then run it, otherwise it's too soon!
        free, percent = getDriveInfo(drive)
        if percent > limit: #if we are still within the limit
            return True
        else:
            return False
    else: #if we've already checked within the last 15 minutes
        return True
    
def dlFromWeb(site, id, name=False):
    site = site.lower()
    try:
        downloadType = REGEX.get(site,'downloadtype')
        loc = False
        if CRED.has_option(site,'watch'):
            loc = CRED.get(site, 'watch')
        download(id, downloadType, site, location=loc, name=name)
        return True
    except Exception, e:
        out('ERROR','Wrong site name. There is no site named \'%s\'.'%site,site)
        return False
    
def dlCookie(downloadType, downloadID, site, cj, network=False):
        #use a login/cookie technique
        #see if there is a cookie already created.
        if not os.path.isfile(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie')):
            #check to make sure this isn't a site that needs a preset cookie.
            if REGEX.has_option(site,'presetcookie') and REGEX.get(site,'presetcookie') == '1':
                out('ERROR','This tracker requires you to manually create a cookie file before you can download',site)
            else:
                #if not, log in and create one
                cj = createCookie(site, cj)
        else:
            #load the cookie since it exists already
            try:
                cj.load(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie'), ignore_discard=True, ignore_expires=True)
            except cookielib.LoadError:
                out('ERROR','The cookie for %s is the wrong format'%site,site)
        
        #create the downloadURL based on downloadType
        if downloadType == '1': # request a download ID, and get a filename
            downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + downloadID
        elif downloadType == '2': # request a torrent.torrent, and receive the torrent
            downloadURL = G.NETWORKS[site]['regex']['downloadurl'] + '/' + downloadID + '/' + downloadID + '.torrent'
        
        #set the socket timeout
        socket.setdefaulttimeout(25)
        
        #request the file
        try:
            file_data = getFile(downloadURL,cj)
            return file_data
        except urllib2.HTTPError, e:
            out('ERROR','There was an HTTP error downloading %s'%downloadID,site)
            if network:
                network.sendMsg('There was an HTTP error downloading %s'%downloadID, target)
            return False

def dlWaffles(downloadID, cj, target, network):    
    #https://www.waffles.fm/download.php/124435/683584/Various%20Artists%20-%20Scion%20CD%20Sampler%20V.30%3A%20SMOG%20%5B2010-CD-MP3-320%5D%20%28Scene%29.torrent?passkey=XX&uid=XX
    downloadURL = '%s/%s/%s/%s.torrent?passkey=%s&uid=%s'%(G.NETWORKS['waffles']['regex']['downloadurl'],CRED.get('waffles','uid'),downloadID,downloadID,CRED.get('waffles','passkey'),CRED.get('waffles','uid'))
    
    #set the socket timeout
    socket.setdefaulttimeout(25)
    
    #request the file
    try:
        file_data = getFile(downloadURL, cj)
        return file_data
    except urllib2.HTTPError, e:
        out('ERROR','There was an HTTP error downloading %s'%downloadID,'waffles')
        if network:
            network.sendMsg('There was an HTTP error downloading %s'%downloadID, target)
        return False   
    
def download(downloadID, downloadType, site, location=False, network=False, target=False, retries=0, email=False, notify=False, filterName=False, announce=False, formLogin=False, sizeLimits=False, name=False):
        """Take an announce download ID and the site to download from, do some magical stuff with cookies, and download the torrent into the watch folder"""
        out('DEBUG', 'Downloading ID: %s, downloadType: %s, site: %s, filter: %s, location: %s, network: %s, target: %s, retries: %s, email: %s'%(downloadID, downloadType, site, filterName, location, network, target, retries, email))
        success = False
        
        #load where we should be saving the torrent if not already set
        if not location:
            location = SETUP.get('setup', 'torrentdir')
            if CRED.has_option(site, 'watch') and CRED.get(site, 'watch') != '':
                location = CRED.get(site, 'watch')
                
        #'network' is only sent if it's a manual download, so if it's false that means this is an automatic dl
        #if it's automatic, then check to see if the delay exists
        if retries == 0 and network == False:
            if SETUP.has_option('setup', 'delay') and SETUP.get('setup', 'delay').lstrip().rstrip() != '':
                time.sleep(int(SETUP.get('setup', 'delay')))
                
        #if this is a retry, then wait 20 seconds.
        if retries > 0:
            time.sleep(20)
        
        cj = cookielib.LWPCookieJar()
        
        #special download routine for waffles    
        if site.lower()=='waffles':
            file_data=dlWaffles(downloadID, cj, target, network)
            if file_data:
                file_info = file_data.info()
        else:     
        #else use the cookie to download the file
            file_data=dlCookie(downloadType, downloadID, site, cj, network)
            if file_data:
                file_info = file_data.info()
        
        #if the file returned is of type html/txt and not torrent, then the login/password are incorrect.
        try:
            if file_info.type == 'text/html':
                #then over-write the current cookie with a new one
                if REGEX.has_option(site,'presetcookie') and REGEX.get(site,'presetcookie') == '1':
                    out('ERROR','There was an error downloading torrent %s. Maybe it was deleted?'%downloadID,site)
                    if network:
                        network.sendMsg('There was an error downloading torrent %s. Maybe it was deleted?'%downloadID, target)
                elif site == 'waffles':
                    out('ERROR','There was an HTTP error downloading %s. Check your passkey/UID.'%downloadID,site)
                else:
                    cj = createCookie(site, cj)
                    try:
                        file_data=dlCookie(downloadType, downloadID, site, cj)
                        if file_data:
                            file_info = file_data.info()
                    except urllib2.HTTPError, e:
                        out('ERROR','There was an HTTP error downloading %s'%downloadID,site)
                        if network:
                            network.sendMsg('There was an HTTP error downloading %s'%downloadID, target)
        except UnboundLocalError:
            pass #if we've received a 404 error or something else, file_info won't be set
        
        try:
        #save the file
            if file_info.type == 'application/x-bittorrent':
                #figure out the filename
                #see if the file has content disposition, if it does read it.
                if not name:
                    filename = downloadID+'.torrent'
                    if 'Content-Disposition' in file_info:
                        for cd in G.CD:
                            if cd in file_info['Content-Disposition']:
                                filename = file_info['Content-Disposition'].replace(cd,'').replace('"','')
                else:
                    filename = name
                    if '.torrent' not in filename:
                        filename += '.torrent'
                        filename = urllib.unquote(filename)
                sizeOK = True
                info = file_data.read()
                if sizeLimits != False and network == False:
		    sizerange = sizeLimits.split(',')
                    fdupe = info
		    tmeta = decode(fdupe)
                    tsize = 0
		    try:
			if "files" in tmeta["info"]:
			    for tfile in tmeta["info"]["files"]:
				tsize += tfile["length"]
			elif "piece length" in tmeta["info"]:
			    tsize = tmeta['info']['piece length']
			mbsize = tsize / Decimal('1048576')
			out('INFO', '(%s) Size: %s.'%(downloadID,mbsize),site)
			if mbsize < Decimal(sizerange[0]):
			    sizeOK = False
			    out('INFO', "(%s) Torrent is smaller than required by '%s'."%(downloadID,filterName),site)
			elif mbsize > Decimal(sizerange[1]) and Decimal(sizerange[1]) != Decimal('0'):
			    sizeOK = False
			    out('INFO', "(%s) Torrent is larger than required by filter '%s'."%(downloadID,filterName),site)
			else:
			    out('INFO', "(%s) Torrent is within size range required by filter '%s'."%(downloadID,filterName),site)
		    except Exception:
			pass
                else:
                    out('INFO', '(%s) No Size check.'%downloadID,site)
                    #pass
                
                if sizeOK:    
                    local_file = open(os.path.join(location, filename),'wb')
                    
                    try:
                        local_file.write(info)
                        local_file.close()
                    except IOError:
                        #If there's no room on the hard drive
                        out('ERROR', '(%s) !! Disk quota exceeded. Not enough room for the torrent!'%downloadID,site)
                    #if the filesize of the torrent is too small, then retry in a moment
                    #only do this two times!
                    if 100 > int(os.path.getsize(os.path.join(location, filename))) and retries < 2:
                        download(downloadID, downloadType, site, location=location, network=network, target=target, retries=retries+1, sizeLimits=sizeLimits)
                        out('ERROR','(%s) !! Torrent file is not ready to be downloaded. Trying again in a moment.'%downloadID,site)
                    #if we've tried too many times, then this is a failed download.
                    elif retries >= 2:
                        out('ERROR','(%s) !! Download could not complete!'%downloadID,site)
                    elif 100 < int(os.path.getsize(os.path.join(location, filename))):
                        out('INFO','(%s) << Download complete of \'%s\' to %s'%(downloadID, filename,location),site)
                        success = True
                        #should we send out an email? or send a message to the user?
                        if email:
                            sendEmail(site, announce, filterName, filename )
                        if notify:
                            sendNotify(site, announce, filterName, filename)
            else:
                if retries < 2:
                    out('ERROR','(%s) !! Torrent file is not ready to be downloaded. Trying again in a moment.'%downloadID,site)
                    download(downloadID, downloadType, site, location=location, network=network, target=target, retries=retries+1, sizeLimits=sizeLimits)
                elif retries >= 2:
                    out('ERROR','(%s) !! Download could not complete!'%downloadID,site)
                    if network:
                        network.sendMsg('There was an error downloading %s from %s. Double check your login credentials and that the ID exists.'%(downloadID,site), target)  
        except UnboundLocalError:
            pass #if file_info.type isn't set because we received an HTTP error!
        
        if type(file_data).__name__!='bool':
            file_data.close()
                
        #if this is a manual download and successful, send notification
        if network and success:
            network.sendMsg(filename+' downloaded successfully', target)

def getFile(downloadURL, cj):
    #create the opener
    if SETUP.get('setup','verbosity').lower() == 'debug':
        opener = build_opener(cj, debug=1)
    else:
        opener = build_opener(cj)
    urllib2.install_opener(opener)
    return opener.open(downloadURL)

def createCookie(site, cj):
    urlopen = urllib2.urlopen
    Request = urllib2.Request
    #opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    if SETUP.get('setup','verbosity').lower() == 'debug':
        opener = build_opener(cj, debug=1)
    else:
        opener = build_opener(cj)
        
    urllib2.install_opener(opener)
    
    http_args = urllib.urlencode(dict(username=G.NETWORKS[site]['creds']['username'], password=G.NETWORKS[site]['creds']['password']))
    
    req = Request(G.NETWORKS[site]['regex']['loginurl'], http_args)
    req.add_header("User-Agent", "Opera/9.80 (Windows NT 5.1; U; en) Presto/2.5.22 Version/10.50")
    if site == "whatcd":
        req.add_header('Referer', 'https://ssl.what.cd/login.php')
    out('INFO','Logging into %s because a cookie was not previously saved or is outdated.'%site,site=site)
    handle = urlopen(req)
    
    cj.extract_cookies(handle, req)
    cj.save(os.path.join(G.SCRIPTDIR,'cookies',site+'.cookie'), ignore_discard=True, ignore_expires=True)
    
    return cj

def build_opener(cj, debug=False):
    # Create a HTTP and HTTPS handler with the appropriate debug
    # level.  We intentionally create a new one because the
    # OpenerDirector class in urllib2 is smart enough to replace
    # its internal versions with ours if we pass them into the
    # urllib2.build_opener method.  This is much easier than trying
    # to introspect into the OpenerDirector to find the existing
    # handlers.
    http_handler = urllib2.HTTPHandler(debuglevel=debug)
    https_handler = urllib2.HTTPSHandler(debuglevel=debug)

    # We want to process cookies
    cookie_handler = urllib2.HTTPCookieProcessor(cj)

    opener = urllib2.build_opener(http_handler, https_handler, cookie_handler)

    # Save the cookie jar with the opener just in case it's needed
    # later on
    opener.cookie_jar = cj

    return opener

def sendEmail(site, announce, filter, filename):
    # Imports
    import smtplib
    from email.mime.text import MIMEText
    
    #create the message
#    msg = 'pyWA has detected a new download.\n\nSite: %(site)s\nCaptured Announce: %(announce)s\nMatched Filter: %(filter)s\nSaved Torrent: %(filename)s'%{'filename':filename, 'filter':filter, 'site':site, 'announce':announce}
    msg = MIMEText('pyWA has detected a new download.\n\nSite: %(site)s\nCaptured Announce: %(announce)s\nMatched Filter: %(filter)s\nSaved Torrent: %(filename)s'%{'filename':filename, 'filter':filter, 'site':site, 'announce':announce})
    gmail = SETUP.get('notification','gmail')
    msg['Subject'] = 'pyWA: New %s download!'%site
    
    # Send the message via our own SMTP server
    
    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    
    #s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    try:
        out('INFO','Emailing %s with a notification.'%gmail)
        s.login(gmail, SETUP.get('notification','password'))
        s.sendmail(gmail, gmail, msg.as_string())
        s.quit()
    except Exception, e:
        out('ERROR', 'Could not send notify email. Error: %s'%e.smtp_error)

def sendNotify(site, announce, filter, filename):
    sent = False
    for key, net in G.RUNNING.items():
        #G.NETWORKS[bot.getBotName()]
        if net.getBotName() == SETUP.get('notification', 'server'):
            out('INFO', 'Messaging %s with an IRC notification.'%SETUP.get('notification', 'nick'))
            net.sendMsg('New DL! Site: %(site)s, Filter: %(filter)s, File: %(file)s '%{'site':site, 'filter':filter,'file':filename}, SETUP.get('notification', 'nick'))
            sent = True
    if not sent:
        out('ERROR','Could not send notification via %s, because I am not connected to that network'%SETUP.get('notification', 'server'))
                    
class autoBOT( ):
    """A class for connecting to an IRC network, joining an announce channel, and watching for releases to download"""
    
    def __init__(self, name, info):
        """init this shit, yo"""
        out('DEBUG', 'autoBOT: '+name+' started',site=name)
        self.name = name
        self.piggyback = False
        self.regex = info['regex']
        self.creds = info['creds']
        self.setup = info['setup']
        self.notif = info['notif']
        self.filters = info['filters']
        self.aliases = dict()
        for key, value in info['aliases'].items():
            self.aliases[value] = key
        self.announcehistory = list()
        self.connection = None
        self.who = list()
        self.partPhrase = ":I leave because I want to!"
        self.joined = False  #have we already joined the channels we're supposed to after connect?
        self.reg = dict()
        self.resistant = False
        self.ircreg = re.compile("\x0f|\x1f|\x02|\x03(?:[\d]{1,2}(?:,[\d]{1,2})?)?", re.UNICODE)
        #self.ircreg = re.compile('||(\\d){0,2}')
        for announce in info['regex']['announces'].split(', '):
            self.reg[announce] = re.compile(info['regex'][announce])
        self.checkTorrentFolders(False)
        if '!' in self.creds['nickowner']:
            self.creds['nickowner'] = self.creds['nickowner'][self.creds['nickowner'].index('!')+1:]
        
        self.advancedfilters = False
        if "advancefilters" in self.creds:
            self.advancedfilters = True
                    
            
        G.LOCK.acquire()   
        irc.add_global_handler('pubmsg', self.handlePubMessage)
        irc.add_global_handler('privmsg', self.handlePrivMessage)
        irc.add_global_handler('welcome', self.handleWelcome)
        irc.add_global_handler('nicknameinuse', self.handleNickInUse)
        irc.add_global_handler('invite', self.handleInvite)
        irc.add_global_handler('whoisuser', self.handleWhoIs)
        irc.add_global_handler('whoischannels', self.handleWhoIs)
        irc.add_global_handler('whoisserver', self.handleWhoIs)
        irc.add_global_handler('endofwhois', self.handleWhoIs)
        irc.add_global_handler('privnotice', self.handlePrivNotice)
        irc.add_global_handler('namreply', self.handleNameReply)
        irc.add_global_handler('action', self.handleAction)
        irc.add_global_handler('currenttopic', self.handleCurrentTopic)
        irc.add_global_handler('error', self.handleError) #ping, part, join  REMOVED from below: 'topicinfo', 'nomotd', 'motd', 'luserme', 'motdstart', 'endofinfo', 'motd2', 'endofmotd','featurelist','myinfo','n_global', 'n_local', 'created', 'endofnames',     
        self.what_events = ["pubnotice","quit","kick","mode","pong",'whoreply','endofwho','statskline', 'statsqline', 'statsnline', 'statsiline', 'statscommands', 'statscline', 'tracereconnect', 'statslinkinfo', 'notregistered', 'statsuptime', 'notopic', 'statsyline', 'endofstats', 'uniqopprivsneeded', 'cannotsendtochan', 'adminloc2', 'adminemail', 'luserunknown', 'luserop', 'luserconns', 'luserclient', 'adminme', 'adminloc1', 'luserchannels', 'toomanytargets', 'listend', 'toomanychannels', 'statsoline', 'wasnosuchnick', 'invitelist', 'endofinvitelist', 'nosuchchannel', 'inviting', 'summoning', 'exceptlist', 'endofexceptlist', 'noorigin', 'nosuchserver', 'nochanmodes', 'endofbanlist', 'yourebannedcreep', 'passwdmismatch', 'keyset', 'needmoreparams', 'nopermforhost', 'alreadyregistered', 'tryagain', 'endoftrace', 'tracelog', 'notonchannel', 'noadmininfo', 'umodeis', 'endoflinks', 'nooperhost', 'nosuchnick', 'fileerror', 'wildtoplevel', 'usersdisabled', 'norecipient', 'notexttosend', 'notoplevel', 'info', 'infostart', 'whoisoperator', 'whoisidle', 'whoischanop', 'whowasuser', 'users', 'usersstart', 'time', 'nousers', 'endofusers', 'servlist', 'servlistend', 'youwillbebanned', 'badchannelkey', 'serviceinfo', 'endofservices', 'service', 'youreoper', 'usernotinchannel', 'list', 'none', 'liststart', 'noservicehost', 'channelmodeis', 'away', 'banlist', 'links', 'channelcreate', 'closing', 'closeend', 'usersdontmatch', 'killdone', 'traceconnecting', 'tracelink', 'traceunknown', 'tracehandshake', 'traceuser', 'traceoperator', 'traceservice', 'traceserver', 'traceclass', 'tracenewtype', 'userhost', 'ison', 'unaway', 'nowaway', 'nologin', 'yourhost', 'rehashing', 'statslline', 'summondisabled', 'umodeunknownflag', 'bannedfromchan', 'useronchannel', 'restricted', 'cantkillserver', 'chanoprivsneeded', 'noprivileges', 'badchanmask', 'statshline', 'unknownmode', 'inviteonlychan', 'channelisfull', 'version', 'unknowncommand', 'nickcollision', 'myportis', 'banlistfull', 'erroneusnickname', 'unavailresource', 'nonicknamegiven']
        for value in self.what_events:
            irc.add_global_handler(value, self.handleAllDebug)
        #Warn if nickowner is empty!
        if self.creds['nickowner'] == '':
                out('ERROR',"Nickowner on network '%s' is blank!"%self.name,site=self.name)
        # Create a server object, connect and join the channel
        self.connection = irc.server()
        G.LOCK.release()              
        
    def saveNewConfigs(self, info):
        self.regex = info['regex']
        self.creds = info['creds']
        self.setup = info['setup']
        self.aliases = dict()
        for key, value in info['aliases'].items():
            self.aliases[value] = key
        self.filters = info['filters']
        for announce in info['regex']['announces'].split(', '):
            self.reg[announce] = re.compile(info['regex'][announce])
        self.checkTorrentFolders(None)
        
    def setSharedConnection(self, connection):
        #this means we are using another bot's connection, so don't bother 
        self.piggyback = True
        self.connection = connection
                        
    def getBotName(self):
        return self.name
        
    def checkTorrentFolders(self, target):
        #global EXIT
        for filter in self.filters.keys():
            if self.filters[filter]['active'] == '1':
                if self.filters[filter].has_key('watch') and self.filters[filter]['watch'] != '':       
                    try:
                        if not os.path.isdir( self.filters[filter]['watch'] ):
                            os.makedirs( self.filters[filter]['watch'] )
                    except Exception, e:
                        out('ERROR', e)
                        if target:
                            self.sendMsg("Error: There was a problem with the custom watch folder for filter '%s'. It will be ignored. : '%s'"%(filter,self.filters[filter]['watch']) , target)
                            self.filters[filter]['watch'] = ''
        if self.creds.has_key('watch') and self.creds['watch'] != '':       
            try:
                if not os.path.isdir( self.creds['watch'] ):
                    os.makedirs( self.creds['watch'] )
            except Exception, e:
                out('ERROR', e)
                if target:
                    self.sendMsg("Error: There was a problem with the custom watch folder for site '%s'. It will be ignored. : '%s'"%(filter,self.creds['watch']) , target)
                    self.creds['watch'] = ''
        try:
            if not os.path.isdir( self.setup['torrentdir'] ):
                os.makedirs( self.setup['torrentdir'] )
        except os.error, e:
            out('ERROR', 'torrentDir: %s caused %s'%(self.setup['torrentdir'],e))
            var = raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()
        except KeyError, e:
            out('ERROR', "Setup option 'torrentDir' is missing from setup.conf. So let's put it in there, mmmmkay?")
            var = raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()
        except Exception, e:
            out('ERROR', e)
            var = raw_input("This program will now exit (okay): ")
            G.EXIT = True
            sys.exit()
                        
    def connect(self):
        """Connect to the IRC network and join the appropriate channels"""
#        irc.debug = 1
        self.joinedchannels = False
        try:
            if 'ssl' in self.regex and self.regex['ssl'] == '1':
                cssl = True
            else:
                cssl = False
            if 'port' in self.regex:
                cport = int(self.regex['port'])
            else:
                cport = 6667
            out('INFO',"Connecting to the server: %s on port: %s SSL: %s" %(self.regex['server'],cport,cssl),site=self.name)
            if self.creds.has_key('tempbotnick'):
                botnick = self.creds['tempbotnick']
            else:
                 botnick = self.creds['botnick']  
            if 'username' in self.creds:
                username = self.creds['username']
            else:
                username = None
            if 'password' in self.creds:
                password = self.creds['password']
            else:
                password = None 
            if self.name != 'waffles':
                if "ircusesignon" in self.creds:
                    self.connection.connect(self.regex['server'], cport, botnick, password, ircname=self.creds['username'], ssl=cssl)
                else:
                    self.connection.connect(self.regex['server'], cport, botnick, ircname=self.creds['username'], ssl=cssl)
#                kwargs = {'ircname':self.creds['username'], 'ssl':cssl}
#                thread.start_new_thread(self.connection.connect,(self.regex['server'], cport, botnick),kwargs)
            elif self.name == 'waffles':
               self.connection.connect(self.regex['server'], cport, botnick, ircname=self.creds['botnick'], ssl=cssl)
        except irclib.ServerConnectionError, e:
            out('ERROR',e,site=self.name)
            time.sleep(3)
        except irclib.ServerNotConnectedError, e:
            out('ERROR',e.message(),site=self.name)
            time.sleep(3)
    
    def disconnect(self):
        self.connection.disconnect("pyWHATauto %s - http://whatscripts.com"%VERSION)
        irc.remove_global_handler('pubmsg', self.handlePubMessage)
        irc.remove_global_handler('privmsg', self.handlePrivMessage)
        irc.remove_global_handler('welcome', self.handleWelcome)
        irc.remove_global_handler('nicknameinuse', self.handleNickInUse)
        irc.remove_global_handler('invite', self.handleInvite)
        irc.remove_global_handler('privnotice', self.handlePrivNotice)
        irc.remove_global_handler('error', self.handleError)
        for value in self.what_events:
            irc.remove_global_handler(value, self.handleAllDebug)
       
    def shouldDownload(self, m, filtertype):
        i = 1 
        release = dict();        
        for str in self.regex[filtertype+'format'].split(', '):
            release[str] = m.group(i) #create the announcement/release format loaded from regex.conf
            i += 1
        #these will save the key/values that cause the filter to fail
        badkey = ''
        for filter in self.filters.keys(): #for each filter
            filter_section_ok = True
            out('FILTER','Checking filter section \'%s\'' %filter,site=self.name)
            if self.filters[filter]['active'] == '1':
                if 'filtertype' in self.filters[filter] and self.filters[filter]['filtertype'] == filtertype or len(self.regex[filtertype+'format'].split(', ')) == 1:
                    for key, value in self.filters[filter].items(): #for each individual filter option within each filter section
                        if filter_section_ok: # this will be set to False if any filters are not met
                            if key in self.regex['tags'] or key in self.regex['not_tags']: # if the filter tag is an allowed tag
                                if not self.isTagOK(key, value, release, filtertype): #is the release item matched in this filter?
                                    filter_section_ok = False #if a filter option doesn't match, then the filter section does not match
                                    badkey = key
                                    break #and break out. Otherwise keep going!
                    if filter_section_ok: #if every filter option has passed within this filter, then the section is ok.
                        out('INFO','Filter %s matches'%filter,site=self.name)
                        dir = self.setup['torrentdir']
                        if self.filters[filter].has_key('watch') and self.filters[filter]['watch'] is not None:
                            dir = self.filters[filter]['watch']
                        return dir, filter #if this entire filter has passed all it's tests, then download it! (pass the directory where the torrent should be saved)
                    #Format the output of the failed filter depending what was wrong
                    try:
                        if badkey == 'all_tags':
                            out('INFO','Filter \'%s\' failed because the release did not match %s with \'%s\''%(filter, badkey, m.group(self.regex[filtertype+'format'].split(', ').index('tags'.replace('not_',''))+1)),site=self.name)
                        elif badkey in self.regex['tags']:
                            out('INFO','Filter \'%s\' failed because the release did not match %s with \'%s\''%(filter, badkey, m.group(self.regex[filtertype+'format'].split(', ').index(badkey.replace('not_',''))+1)),site=self.name)
                        elif badkey in self.regex['not_tags']:
                            out('INFO','Filter \'%s\' failed because the release contained \'%s\' which is in %s'%(filter, m.group(self.regex[filtertype+'format'].split(', ').index(badkey.replace('not_',''))+1), badkey),site=self.name)
                    except ValueError, e:
                        out('ERROR', 'There was an error trying to output why the filter did not match. %s'%e)
                else:
                    out('INFO','Filter \'%s\' is not of type: %s' %(filter,filtertype),site=self.name)
            else:
                out('INFO','Filter \'%s\' is not active'%(filter),site=self.name)        
        return False, False  # otherwise, all filters failed the tests, so don't download

    def isTagOK(self, key, value, release, filtertype):
        if key == 'size': #if the filter includes a size limiter, just return true since we check it later anyway
            return True
        #key = filter key, value = filter value
        if key in release.keys() or key == "all_tags" and 'tags' in release.keys():# and release[key] is not None: # Check to make sure the key is in the release announcement
            if value == '1': #if the filter tag is a toggle option, just check that the option exists in the release.
                i = self.regex[filtertype+'format'].split(', ').index(key)+1
                if release[key] is not None:
#                if m.group(i):
                    out('FILTER','Detected \'%s\', which you wanted.' %(release[key]),site=self.name)
                    return True
            elif value == '0': #if the filter tag is a toggle option, just check that the option does NOT exist in the release.
                i = self.regex[filtertype+'format'].split(', ').index(key)+1
#                if m.group(i):
                if release[key] is None:
                    out('FILTER','Detected \'%s\', which you did not want.' %(release[key]),site=self.name)
                    return True
            elif value.lstrip().rstrip() == '': #test to make sure that the values for the filter option exist, if it's just blank then return true
                return True
            elif key == 'tags' and release[key] is not None:  #if the filter option is "tags", search through it for that tag, don't do a re.match.
                try:
                    for commastr in value.split(','):
                        for str in commastr.split('\n'):
                            str = str.lstrip().rstrip()
                            if str != '':
                                if str[0] != '@':
                                    retags = re.findall('[\w\._-]+', release[key])
                                    for xt in retags:
                                        if str.lower() == xt.lower():
                                            out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                            return True
                                elif str[0] == '@' and re.search(str[1:].lower(), release[key].lower().lstrip()):
                                    out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                    return True
                                else:
                                    out('DEBUG',"Didn't detect %s match using %s in %s" %(key, str,release[key]),site=self.name)
                    out('FILTER',"Didn't detect match in %s" %(key),site=self.name)
                except Exception, e:
                    out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, key, release[key], value, e),site=self.name)
                    pass
            elif key == 'all_tags' and release['tags'] is not None:
                try:
                    for commastr in value.split(','):
                        for str in commastr.split('\n'):
                            str = str.lstrip().rstrip()
                            if str != '':
                                if str.lower() not in release['tags'].lower():
                                    out('FILTER',"Didn't detect match using %s. Announcement is missing '%s'."%(key, str),site=self.name)
                                    return False
                    out('FILTER',"Detected match using all_tags.", site=self.name)
                    return True
                except Exception, e:
                    out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, key, release[key], value, e),site=self.name)
            else: #if it's not a toggle option, size option, or tags option, check to make sure the values match
                if release[key] is not None:
                    try:
                        for commastr in value.split(','):
                            for str in commastr.split('\n'):
                                str = str.lstrip().rstrip()
                                if str != '':
                                    if str[0] != '@' and str.lower() == release[key].lower():
                                        out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                        return True
                                    elif str[0] == '@' and re.match(str[1:].lower(), release[key].lower().lstrip()):
                                        out('FILTER',"Detected %s match using '%s' in %s" %(key,str,release[key]),site=self.name)
                                        return True
                                    else:
                                        out('DEBUG',"Didn't detect %s match using '%s' in %s" %(key, str, release[key]),site=self.name)
                        out('FILTER',"Didn't detect match in %s" %(key),site=self.name)
                    except Exception, e:
                        out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, key, release[key], value, e),site=self.name)
        elif "not_" in key: # how about if it's a not_filter option?
            if key.replace('not_','') in release.keys() and release[key.replace('not_','')] is not None:
                nkey = key.replace('not_','')
                if nkey == 'tags': #if the not_filter option is not_tags, search the values don't match them
                    try:
                        for commastr in value.split(','):
                            for str in commastr.split('\n'):
                                str = str.lstrip().rstrip()      
                                if str[0] != '@':
                                    retags = re.findall('[\w\._-]+', release[nkey])
                                    for xt in retags:
                                        if str.lower() == xt.lower():
                                            out('FILTER',"Detected %s present in %s, which is disallowed by %s" %(str, nkey, key),site=self.name)
                                            return False
                                elif str[0] == '@' and re.search(str[1:].lower(), release[nkey].lower().lstrip()):
                                    out('FILTER',"Detected %s present in %s, which is disallowed by %s" %(str, nkey, key),site=self.name)
                                    return False
                    except Exception, e:
                        out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, nkey, release[key], value, e),site=self.name)
                        pass
                else: #otherwise it's not multiple values to be searched, so just match it
                    try:
                        for commastr in value.split(','):
                            for str in commastr.split('\n'):
                                str = str.lstrip().rstrip()
                                if str[0] != '@' and str.lower() == release[nkey].lower():
                                    out('FILTER',"Detected %s present in %s, which is in %s" %(str, nkey, key),site=self.name)
                                    return False
                                elif str[0] == '@' and re.match(str[1:].lower(), release[nkey].lower().lstrip()):
                                    out('FILTER',"Detected %s present in %s, which is in %s " %(str, nkey, key),site=self.name)
                                    return False
                    except Exception, e:
                        out('ERROR','Tag Error: str: %s key: %s release[key]: %s Value: %s error: %s' %(str, nkey, release[key], value, e),site=self.name)
                        pass
            out('FILTER',"Didn't detect any values present in \'%s\'" %(key),site=self.name)
            return True           
        else:  
            out('FILTER','\'%s\' was required but not found in this release' %(key),site=self.name)
            return False

    def processMessages(self, msg, args):
        announce = msg
        matched = False
        for filtertype, reg in self.reg.items():
            m = reg.search(announce)
            if m:
                matched = True
                #should add announcement to SQLdb here!
                #G.DB.addAnnounce(self.name, announce, m.group(self.regex[filtertype+'format'].split(', ').index('downloadID')+1))
                G.Q.put((self.name, announce, m.group(self.regex[filtertype+'format'].split(', ').index('downloadID')+1)))
                
                location = None
                out('INFO','**** Announce found: '+m.group(0),site=self.name)
                out('DEBUG','Announce found: '+m.group(1),site=self.name)
                out('FILTER','This is a(n) %s release' %(filtertype),site=self.name)
                location, filter = self.shouldDownload(m, filtertype)
                if location:
                    downloadID = m.group(self.regex[filtertype+'format'].split(', ').index('downloadID')+1)
                    out('INFO','(%s) >> Download starting from %s'%(downloadID,self.name),self.name)
                    gmail=False                    
                    #if the filter is set to send an email on capture
                    if 'email' in self.filters[filter] and self.filters[filter]['email'] == '1':
                        gmail = True
                    #or the global email toggle is set, and the filter email option isn't disabled
                    elif self.notif['email'] == '1':
                        #if the filter has the email option at all
                        if 'email' in self.filters[filter]:
                            #and it's not set to 0
                            if self.filters[filter]['email'] != '0':
                                gmail = True
                        #if the filter does not have the email option
                        else:
                            gmail = True
                            
                    notifi = False
                    #if the filter is set to send a notification on capture
                    if 'notify' in self.filters[filter] and self.filters[filter]['notify'] == '1':
                        notifi = True
                    elif self.notif['message'] == '1':
                        if 'notify' in self.filters[filter]:
                            if self.filters[filter]['notify'] != '0':
                                notifi = True
                        else:
                            notifi = True
                            
                    if not freeSpaceOK():
                        pass
                        #out('ERROR','You have reached your free space limit. Torrent is being placed in an overflow folder.',site=self.name)
                    
                    if self.advancedfilters == True:
                        #check site filters, just returns true/false!
                        pass
                                
                    #does the announcement include a size limit?
                    sL=False
                    if "size" in self.filters[filter] and self.filters[filter]['size'].rstrip().lstrip() != '' and 2 == len(self.filters[filter]['size'].split(',')):
                        sL=self.filters[filter]['size']
                            
                    download(downloadID, self.regex['downloadtype'], self.name, location=location, email=gmail, filterName=filter, announce=announce, notify=notifi, sizeLimits=sL)   
                    G.LOCK.acquire()
                    G.REPORTS[self.name]['seen'] += 1
                    G.REPORTS[self.name]['downloaded'] += 1
                    G.LOCK.release()     
                else:
                    G.LOCK.acquire()
                    G.REPORTS[self.name]['seen'] += 1
                    G.LOCK.release()
                    out('FILTER','There was no match with any %s filters' %(filtertype),site=self.name)
    
            if not matched:
            #why isn't this an announce?
                try:
                    if self.regex.has_key('intro') and announce.lstrip().startswith(self.regex['intro'].lstrip()):
                        if G.RUNNING.has_key('whatcd'):
                            G.RUNNING['whatcd'].naughtyAnnounce(announce,self.name)
                    elif self.regex.has('intro') == False:
                        if G.RUNNING.has_key('whatcd'):
                            G.RUNNING['whatcd'].naughtyAnnounce(announce,self.name)
                except:
                    pass 
        
    def stripIRCColors(self,msg):
        msg = self.ircreg.sub('',msg)
        return msg

    def naughtyAnnounce(self, announce, network):
        self.connection.privmsg('#whatbot-debug', network + ":" + announce)

    def sendMsg(self, msg, target):
        try:
            self.connection.privmsg(target, msg)
        except irclib.ServerNotConnectedError, e:
            out('ERROR','Could not send \'%s\' to %s, most likely because you asked it to disconnect.'%(msg,target),site=self.name)
            
    def sendWhoIs(self, whonick, ownernetwork, ownertarget):
        self.ownernetwork = ownernetwork
        self.ownertarget = ownertarget
        self.connection.whois((whonick,))
    
    def partChannel(self,channel=None,channels=None):
        if channel is not None:
            if channel[0] == "#":
                self.connection.part(channel,self.partPhrase)
            else:
                self.connection.part("#"+channel,self.partPhrase)
        elif channels is not None:
            for channel in channels:
                if channel[0] == "#":
                    self.connection.part(channel,self.partPhrase)
                else:
                    self.connection.part("#"+channel,self.partPhrase)
    
    def joinChannel(self,channel=None,channels=None):
        if channel is not None:
            if channel[0] == "#":
                self.connection.join(channel)
            else:
                self.connection.join("#"+channel)
        elif channels is not None:
            for channel in channels:
                if channel[0] == "#":
                    self.connection.join(channel)
                else:
                    self.connection.join("#"+channel)
            
    def joinOtherChannels(self):
        if 'chanfilter' in self.creds:
            for xchannel in self.creds['chanfilter'].split(','):
                for channel in xchannel.split('\n'):
                    channel=channel.rstrip()
                    channel=channel.lstrip()
                    if channel != '':
                        out('INFO',"Joining channel: %s"%channel,site=self.name)
                        self.connection.join(channel)

    def handleWelcome(self, connection, e):
        if self.regex['server'] == connection.server and self.piggyback == False:
            if self.connection.is_connected():
                if 'tempbotnick' in self.creds:
                    self.connection.privmsg('nickserv', "GHOST %s %s" %(self.creds['botnick'], self.creds['nickservpass']))
                    self.connection.nick(self.creds['botnick'])
                    del self.creds['tempbotnick']
                out('INFO',"Connected to %s." %(self.regex['server']),site=self.name)
#                    if self.creds['nickservpass']: 
#                        self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
#                        time.sleep(.5)
            else:
                out('ERROR','Connection was lost. Maybe you were g-lined? Trying again.',site=self.name)
                self.connect()
            out('INFO','Your bots nickname MUST be registered with nickserv, otherwise it will sit here and do nothing!',site=self.name)
    
    def handleInvite(self, connection, e):
        if self.regex['server'] == connection.server:
            if e.source()[e.source().index('!')+1:].lower() == self.regex['botwho'].lower() and e.arguments()[0] == self.regex['announcechannel']:
                self.connection.join(e.arguments()[0])
                self.joined = True
                if self.name == 'waffles':
                    self.connection.nick(self.creds['botnick'])
                    self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
                
    def handlePubMessage(self, connection, e):# Any public message
        """Handles the messages received by the IRCLIB and figures out WTF to do with them. Probably throws most of them away, cause IRC is full of trash."""
        if self.regex['server'] == connection.server:
            cleanedmsg = self.stripIRCColors(e.arguments()[0])
            #make sure that we always use lower case!
            if e.source()[e.source().index('!')+1:].lower() == self.regex['botwho'].lower() and e.target().lower() in self.regex['announcechannel'].lower():
                handlePubMSG.announce(self, connection, e, cleanedmsg)
            else:
                handlePubMSG.pubMSG(self, connection, e, cleanedmsg)
    
    def handlePrivMessage(self, connection, e):
        """Handle messages sent through PM."""
        if self.regex['server'] == connection.server and self.piggyback == False:
            if e.source()[e.source().index('!')+1:] == self.creds['nickowner'] or re.search(self.creds['nickowner'].lower(),e.source().lower()):
                self.handleOwnerMessage(e.arguments()[0], e.source()[:e.source().index('!')], e.source()[:e.source().index('!')])
            else:
                print '%s:PM:%s:%s' %(self.name, e.source()[0:e.source().index('!')], e.arguments()[0])
    
    def handleAction(self, connection, e):
        """Handle messages sent as actions."""
        if self.regex['server'] == connection.server:
            if e.source()[e.source().index('!')+1:].lower() == self.regex['botwho'].lower() and e.target().lower() in self.regex['announcechannel'].lower():
                cleanedmsg = self.stripIRCColors(e.arguments()[0])
                handlePubMSG.announce(self, connection, e, cleanedmsg)
                
    def handleWhoIs(self, connection, e):
        if self.regex['server'] == connection.server and self.piggyback == False:
            if e.eventtype() == 'endofwhois':
                print self.name
                if self.ownernetwork != None and self.ownertarget != None:
                    G.RUNNING[self.ownernetwork].sendMsg(self.who,self.ownertarget)
                    self.ownernetwork = None
                    self.ownertarget = None
                    self.who = list()
            elif e.eventtype() == 'whoisuser':
                self.who.append("User: %s, Info: %s"%(e.arguments()[0],e.arguments()[1:]))
            elif e.eventtype() == 'whoischannels':
                self.who.append("Channels: %s"%e.arguments()[1:])
            elif e.eventtype() == 'whoisserver':
                self.who.append("Server info: %s"%e.arguments()[1:])
            else:
                self.who.append(e.arguments())
    
    def handleNameReply(self, connection, e):
        if 'whatcd' == self.name:
            chan = e.arguments()[1]
            if chan == "#whatbot-debug":
                self.sendMsg("SuperSecretPW","pyWhatBot")
            #elif chan == "#whatbot":
            #    self.sendMsg("SuperSecretPW","pyWhatBot")
                
    def handlePrivNotice(self, connection, e):
        if self.regex['server'] == connection.server and self.piggyback == False:
            out('INFO',"%s:%s" %(e.arguments(),e.target()),site=self.name)
            if 'password accepted' in e.arguments()[0].lower() and self.joined == False or 'you are now identified for' in e.arguments()[0].lower() and self.joined == False:
                out('INFO','You have identified with nickserv successfully.',site=self.name)
                try: #if we are registered with ident
                    if self.regex['requiresauth'] and self.regex['requiresauth'] >= '1':
                        authstring = self.regex['authstring'].strip().rstrip()
                        try:
                            if '$username' in authstring:
                                authstring = authstring.replace('$username', self.creds['username'])
                            if '$irckey' in authstring:
                                authstring = authstring.replace('$irckey', self.creds['irckey'])
                            if '$password' in authstring:
                                authstring = authstring.replace('$password', self.creds['password'])
                            if '$authchan' in authstring:
                                authstring = authstring.replace('$authchan', self.regex['authchan'])
                            if '$announcechan' in authstring:
                                authstring = authstring.replace('$announcechan', self.regex['announcechannel'])
                        except KeyError, e:
                            #spit out an error because that site is missing a certain requirement
                            pass
#                        print authstring
                        if 'authchan' in self.regex:
                            out('INFO',"Joining channel: %s by logging in with %s" %(self.regex['authchan'],self.regex['botname'].capitalize()),site=self.name)
                        else:
                            out('INFO',"Joining channel: %s by logging in with %s" %(self.regex['announcechannel'],self.regex['botname'].capitalize()),site=self.name)
                        self.connection.privmsg(self.regex['botname'],"%s"%authstring)   
                    else:
                        out('INFO',"Joining channel: %s" %(self.regex['announcechannel']),site=self.name)
                        self.connection.join(self.regex['announcechannel'])
                    if 'cmd' in self.creds and self.creds['cmd'] != '':
                        self.connection.send_raw(self.creds['cmd'])
                    self.joined = True
                    time.sleep(1)
                    self.joinOtherChannels()
                    #Join the what.cd-debug channel if you're on the what-network
                    if self.name == 'whatcd':
                        self.connection.join('#whatbot-debug')
                except irclib.ServerConnectionError, e:
                    out('ERROR',e,site=self.name)
                except irclib.ServerNotConnectedError, e:
                    out('ERROR',e.message(),site=self.name)                        
            elif 'please choose a different nick' in e.arguments()[0].lower() and self.joined == False:
                out('INFO',"Ident request received. Sending identify.",site=self.name)
                if self.creds['nickservpass']: 
                    self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
            elif 'this nick is owned by someone else' in e.arguments()[0].lower() and self.joined == False:
                out('INFO',"Ident request received. Sending identify.",site=self.name)
                if self.creds['nickservpass']: 
                    self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
            elif 'Password accepted' in e.arguments()[0]:
                out('INFO','You have identified with nickserv successfully.',site=self.name)
            elif 'You were forced to join' in e.arguments()[0]:
                #then you joined a channel\
                channel = e.arguments()[0][e.arguments()[0].index('#'):]
                out('INFO','You were forced to join %s'%channel,site=self.name)
            else:
                out('DEBUG',"(%s)%s:%s" %(e.eventtype(),e.arguments(),e.target()),site=self.name)
    
    def handleCurrentTopic(self, connection, e):
        if self.regex['server'] == connection.server:
            channel = e.arguments()[0]
            topic = self.stripIRCColors(e.arguments()[1])
            out('INFO','%s: %s'%(channel, topic),site=self.name)
    
    def handleNickInUse(self, connection, e):
        if self.regex['server'] == connection.server and self.piggyback == False:
            if 'ircallowednick' in self.creds and self.joined == False:
                out('ERROR','The nickname %s was already in use. I cannot join the announce channel without it, so I am disconnecting.' %(self.creds['ircallowednick']),site=self.name)
                self.disconnect()
            else:   
                newnick = 'pyWHATbot|' + str(random.randint(1000,3000))
                out('ERROR','The nickname %s was already in use. You have been renamed as %s.' %(self.creds['botnick'],newnick),site=self.name)
                self.connection.nick(newnick)
                self.creds['tempbotnick'] = newnick
        
    def handleError(self, connection, e):
        if self.regex['server'] == connection.server and self.piggyback == False:
            out('ERROR',"%s:%s" %(e.arguments(),e.target()),site=self.name)
            con = self.connection.is_connected()
            #this is all here cause for some reason python's SSL or TCP or whatever header checksums are bad, therefore causing the bot to disconnect after sending a NICK command during an initial connection if the current nick is already used. This is to get around that.
    
            if 'Closing link' in e.target():
                self.connection.disconnect('Cause it broke')
                out('INFO',"Waiting a few seconds before reconnect.",site=self.name)
                time.sleep(5)
            if not self.connection.is_connected():   #you have been disconnected. Who knows why?
                self.connect()  #so let's reconnect
                
    def handleAllDebug(self, connection, e):
        if self.regex['server'] == connection.server and self.piggyback == False:
            args = {}
            args["type"] = e.eventtype()
            args["source"] = e.source()
            args["channel"] = e.target()
            args["event"] = e
            if e.eventtype() == 'error':
                out('ERROR',"%s:%s" %(e.arguments(),e.target()),site=self.name)
            else:
                if e.eventtype() == 'nosuchnick' and e.arguments()[0].lower() == 'pywhatbot':
                    pass
                else:
                    out('DEBUG',"(%s)%s:%s" %(e.eventtype(),e.arguments(),e.target()),site=self.name) 
    
    def handleOwnerMessage(self, msg, target, ownernick):
        """Take commands from the operator. That's right, bow down."""              
        quit = {
                'help':'Disconnects from all NETWORKS and closes all threads.   [pyWHATauto]',
                'cmd':self.fquit                
                }
        whois = {
                    'help':'Returns a whois on the target name and network. Format %whois <network/alias> <nickname>   [pyWHATauto]',
                    'cmd':self.fwhois
                    }
        update = {
                  'help':'Updates your regex.conf to the newest version.   [pyWHATauto]',
                  'cmd':self.fupdate                
                  }
        cmd = {
               'help':'Sends a raw IRC command through the bot. Format %cmd <IRCCOMMAND> <values>. Please use the pyWHATauto commands if available, otherwise use this. For a list of IRC Commands and how to use them: http://en.wikipedia.org/wiki/List_of_Internet_Relay_Chat_commands.   [pyWHATauto]',
               'cmd':self.fcmd
               }
        ragequit = {
                    'help':"You're angry, and you're gonna let them know it!",
                    'cmd':self.fragequite                    
                    }
        filter = {
                  'help':'Allows you to control filter states, as well as list enabled/disabled filters. Type %filter <enable/disable> <filtername> to toggle a filter.    [pyWHATauto]',
                  'cmd':self.ffilter
                  }
        filters = {
                  'help':'Allows you to control filter states, as well as list enabled/disabled filters.   [pyWHATauto]',
                  'cmd':self.ffilter
                  }
        connect = {
                   'help':'Connects to a network. Format %connect <network>.   [pyWHATauto]',
                   'cmd':self.fconnect
                   }
        free = {
                  'help':'Outputs the amount of free space on the drive specified in setup.conf.   [pyWHATauto]',
                  'cmd':self.ffree
                }
        reload = {
                  'help':'Reloads all configs.   [pyWHATauto]',
                  'cmd':self.freload         
                  }
        nick = {
                'help':'Changes the bots nickname to whatever you pass it. Does not change what the bot thinks it calls itself, so a %ghost command will ignore your changes.   [pyWHATauto]',
                'cmd':self.fnick                
                }
        join = {
                'help':'Joins the specified channel(s). You can join local channels as well as cross-network. Format %join #<channel> #<channel> ... or %join <network/alias> #<channel> #<channel> ...   [pyWHATauto]',
                'cmd':self.fjoin               
                }
        part = {
                'help':'Parts the specified channel(s). You can part local channels as well as cross-network. Format %part #<channel> #<channel> ... or %part <network/alias> #<channel> #<channel> ...   [pyWHATauto]',
                'cmd':self.fpart
                }
        stats = {
                 'help':'Gives seen and download statistics on each enabled network.   [pyWHATauto]',
                 'cmd':self.fstats                
                 }
        time = {
                'help':'Outputs the local system time from where the bot resides.   [pyWHATauto]',
                'cmd':self.ftime
                }
        cycle = {
                 'help':'Rejoins the current channel.   [pyWHATauto]',
                 'cmd':self.fcycle
                 }
        sites = {
                'help':'Lists the currently enabled NETWORKS/sites and their WHATauto names.   [pyWHATauto]',
                'cmd':self.fsites
                 }
        disconnect = {
                      'help':'Disconnects from the specified network. Format: %disconnect <site>. Ex: %disconnect whatcd.   [pyWHATauto]',
                      'cmd':self.fdisconnect
                      }
        download = {
                    'help':'Downloads a torrent from a network manually. Format: %download <site> <torrentID>. For a list of site names try %sites.   [pyWHATauto]',
                    'cmd':self.fdownload
                    }
        version = {
                   'help':'Outputs the current running version to the channel.   [pyWHATauto]',
                   'cmd':self.fversion
                   }
        ghost = {
                 'help':'Ghosts the nickname set in config.   [pyWHATauto]',
                 'cmd':self.fghost
                 }
        current = {
                   'help':'Sends you a private message outputting your current filters.   [pyWHATauto]',
                   'cmd':self.fcurrent
                   }
        statsreset = {
                      'help':'Resets the stats on seen/downloaded.   [pyWHATauto]',
                      'cmd':self.fstatsreset
                      }
        uptime = {
                  'help':'Outputs how long the bot has been running.   [pyWHATauto]',
                  'cmd':self.fuptime
                  }
        help = {
                'help':'You sir, are an idiot.   [pyWHATauto]',
                'cmd':self.fhelp
                }
        
        #The dictionary of commands
        commands = {
            'quit':quit,
            'free':free,
            'drive':free,
            'join':join,
            'part':part,
            'stats':stats,
            'update':update,
            'cycle':cycle,
            'download':download,
            'disconnect':disconnect,
            'time':time,
            'cmd':cmd,
            'whois':whois,
            'statsreset':statsreset,
            'ghost':ghost,
            'ragequit':ragequit,
            'filter':filter,
            'filters':filter,
            'status':stats,
            'help':help,
            'connect':connect,
            'uptime':uptime,
            'filter':filter,
            'reload':reload,
            'current':current,
            'nick':nick,
            'sites':sites,
            'version':version,
            }
        
        cmds = msg.rstrip().split(' ')
        if cmds[0] != '' and cmds[0][0] ==  '%': #test if the msg is a potential command
            rootcmd = cmds[0][1:] 
            if commands.has_key(rootcmd): #test if it's a real command
                if len(cmds) > 1: #is this a single part command, or does it have options?
                    if cmds[1] == 'help':
                        #dic.get('a',default)('WHAT','noob')
                        self.sendMsg(commands[rootcmd]['help'], target)
                    else:
                        switches = list()
                        for item in cmds[1:]:
                            switches.append(item)
                        var = [target, switches, commands, ownernick]
                        stupid = commands[rootcmd]
                        stupid.get('cmd')(var) 
                else: #this is a single-part message
                    var = [target, None, commands, ownernick]
                    stupid = commands[rootcmd]
                    stupid.get('cmd')(var)
            else:
                'That is not a valid command. Try %help <command> for more information.'
        
    def fquit(self, vars):
        out('CMD','quit',site=self.name)
        out('INFO','I have received the quit command!',site=self.name)
        for key, bot in G.RUNNING.items():
            bot.disconnect()
        G.LOCK.acquire()
        #global EXIT
        G.EXIT = True
        G.LOCK.release()
        sys.exit()
    
    def fragequite(self, vars):
        self.partPhrase=":AND I'M NEVER COMING BACK!"
        out('CMD','quit',site=self.name)
        out('INFO','I have received the quit command!',site=self.name)
        target = vars[0]
        angorz = ["RRRRrrraaaaggggeee.", "I'm backtracing your IPs right now. You're so dead.", "I'm calling the FBI on you. What's the number, do you know?","I'm going to tell my daddy on you. He's real big where he works. Like an elephant.", "I'm so hacking through your ports right nao!", "FFFFFFFUUUUUUUUUUUUUUU", "You guys are fucking assholes!", "I'M SO ANG0RZ RIGHT NAO!", "STOP TOUCHING ME!", "Fuck this place. I'm way cooler than you.", "Who you gonna call?"]
        from random import choice
        self.sendMsg(choice(angorz), target)
        self.sendMsg("BTW, here's a link to my blog: http://perezhilton.com/", target)
        self.partChannel(target)
        for key, bot in G.RUNNING.items():
            bot.disconnect()
        G.LOCK.acquire()
        #global EXIT
        G.EXIT = True
        G.LOCK.release()
        sys.exit()
    
    def ffilter (self,vars):
        target = vars[0]
        if vars[1] != None:
            if vars[1][0].lower() == 'list':
                #print out the list of filters that have been toggled
                G.LOCK.acquire()
                #if there are any items in the changed filters list
                if len(G.FILTERS_CHANGED) > 0:
                    self.sendMsg('Manually toggled filters:',target)
                    for key, value in G.FILTERS_CHANGED.items():
                        self.sendMsg('%s: %s'%(key, value), target)
                self.sendMsg('Unchanged filters:',target)
                for key, value in G.FILTERS.items():
                    if key not in G.FILTERS_CHANGED:
                        self.sendMsg('%s: %s'%(key, value), target)
                G.LOCK.release()
            elif vars[1][0].lower() == 'enable' and len(vars[1]) == 2:
                #toggle the filter to enable it
                G.LOCK.acquire()
                if vars[1][1].lower() in G.FILTERS: #does the filter exist?
                    #then the filter is legit, so enable it
                    G.FILTERS_CHANGED[vars[1][1].lower()] = '1'
                    #Does changing the filter state put it back to it's original value? If so, delete it from the changed list
                    if G.FILTERS_CHANGED[vars[1][1].lower()] == G.FILTERS[vars[1][1].lower()]:
                        del G.FILTERS_CHANGED[vars[1][1].lower()]
                    reloadConfigs()
                    self.sendMsg('Filter %s has been toggled on.   [pyWHATauto]'%vars[1][1].lower(), target)
                else:
                    #then tell them the filter doesn't exist and how to get a list of filters
                    self.sendMsg("That filter doesn't exist. Try again!", target)
                    pass
                G.LOCK.release()
            elif vars[1][0].lower() == 'disable' and len(vars[1]) == 2:
                #toggle the filter to disable it
                G.LOCK.acquire()
                if vars[1][1].lower() in G.FILTERS: #does the filter exist?
                    #then the filter is legit, so disable it
                    G.FILTERS_CHANGED[vars[1][1].lower()] = '0'
                    #Does changing the filter state put it back to it's original value? If so, delete it from the changed list
                    if G.FILTERS_CHANGED[vars[1][1].lower()] == G.FILTERS[vars[1][1].lower()]:
                        del G.FILTERS_CHANGED[vars[1][1].lower()]
                    reloadConfigs()
                    self.sendMsg('Filter %s has been toggled off.   [pyWHATauto]'%vars[1][1].lower(), target)
                else:
                    #the filter doesn't exist
                    self.sendMsg("That filter doesn't exist. Try again!   [pyWHATauto]", target)
                G.LOCK.release()
            else:
                #incorrect command, give info
                self.sendMsg('Incorrect command structure. What does that even mean?   [pyWHATauto]', target)
        else:
            out('CMD','filter, incomplete',site=self.name)
            self.sendMsg('Filters. Like on cigarettes, except a lot healthier. Try typing %help filter to see how they are used.   [pyWHATauto]', target)
    
    def fdisconnect(self, vars):
        target = vars[0]
        if vars[1] is not None:
            network = vars[1][0]
            #if it's an alias
            if network in self.aliases.keys():
                if self.aliases[network] in G.RUNNING:
                    G.RUNNING[self.aliases[network]].disconnect()
                    self.sendMsg('I have disconnected from %s.   [pyWHATauto]'%self.aliases[network], target)
                    G.LOCK.acquire()
                    del G.RUNNING[self.aliases[network]]
                    G.LOCK.release()
            else:
                if network in G.RUNNING:
                    G.RUNNING[network].disconnect()
                    self.sendMsg('I have disconnected from %s.   [pyWHATauto]'%network, target)
                    G.LOCK.acquire()
                    del G.RUNNING[network]
                    G.LOCK.release()
            out('CMD', 'disconnect',site=network)
        else:
            self.sendMsg('That is not a full command. Format: %disconnect <network>   [pyWHATauto]', target)
            out('CMD', 'disconnect')
                       
    def fnick(self, vars):
        if vars[1] != None:
            name = vars[1][0]
            out('CMD','nick',site=self.name)
            self.connection.nick(name)
            
    def fwhois(self, vars):
        if vars[1] != None:
            target = vars[0]
            name = vars[1][1]
            network = vars[1][0]
            if network in self.aliases.keys():
                network = self.aliases[network]
            out('CMD','Whois sent for %s on %s'%(name, network),site=self.name)
            if network in G.RUNNING:
                G.RUNNING[network].sendWhoIs(name,self.name,target)        
                            
    def ffree(self, vars):
        target = vars[0]
        msg = vars[1]
        out('CMD','free',site=self.name)
        if os.name == 'nt':
            if WIN32FILE:
                free, percent = getDriveInfo(self.setup['drive'])
                msg = '**Free Space on %s: %s GB (%s%%)   [pyWHATauto]' %(self.setup['drive'], round(free/1024/1024/1024,2), round(float(percent*100),2))
            else:
                msg = 'Uhh.. I need to install win32file for this to work.'
        elif os.name == 'posix':
            try:
                free, percent = getDriveInfo(self.setup['drive'])
                msg = '**Free Space on %s: %s GB (%s%%)   [pyWHATauto]' %(self.setup['drive'], round(free,2), round(float(percent*100),2))
            except TypeError, e:
                out('ERROR',"There was an error. Double check 'drive' in setup.conf.",site=self.name)
                msg = "There was an error. Double check 'drive' in setup.conf."
        if msg != None:
            self.sendMsg(msg, target)
    
    def freload(self, vars):
        target = vars[0]
        out('CMD','reload',site=self.name)
        reloadConfigs()
        self.checkTorrentFolders(target)
        self.sendMsg('All configs (filters, setup, etc) have been reloaded.   [pyWHATauto]', target)
        
    def fupdate(self, vars):
        target = vars[0]
        out('CMD','update',site=self.name)
        try:
            webFile = urllib.urlopen('http://www.whatscripts.com/update/version')
            x=webFile.read().split('\n')
            webFile.close()
            minversion=x[0]
            regversion=x[1]
            v = float(VERSION.replace('v',''))
            #print minversion, v
            if float(minversion) <= float(VERSION.replace('v','')):
                if int(regversion) > G.REGVERSION:
                    regUpdate = urllib.urlopen('http://www.whatscripts.com/update/regex.conf')
                    localFile = open(os.path.join(G.SCRIPTDIR,'regex.conf'), 'w')
                    localFile.write(regUpdate.read())
                    regUpdate.close()
                    localFile.close()
                    reloadConfigs()
                    self.sendMsg("Your regex.conf file has been updated to the latest version.   [pyWHATauto]", target)
                else:
                    self.sendMsg("You are currently running the latest regex.conf file.   [pyWHATauto]", target)
            else:
                self.sendMsg("You need to update pyWA before you can use the new regex. You are using %s, but %s is required.   [pyWHATauto]"%(VERSION,"v"+str(minversion)), target)
        except Exception, e:
            out('ERROR',"Something happened when trying to update. %s"%e,site=self.name)
    
    def fjoin(self, vars):
        target= vars[0]
        cmd_in = vars[1]
        out('CMD','join %s' %cmd_in,site=self.name)
        #check that the channel starts with # otherwise append it!
        if cmd_in is not None:
            #if the first parameter is a network then send the channels to join to that network
            if cmd_in[0].lower() in G.RUNNING:
                #if the network is currently running
                if cmd_in[0] in G.RUNNING:
                    #if there are multiple channels to send
                    if len(cmd_in[1:]) > 1:
                        G.RUNNING[cmd_in[0]].joinChannel(channels=cmd_in[1:])
                    #otherwise just one channel
                    else:
                        print cmd_in[1]
                        G.RUNNING[cmd_in[0]].joinChannel(channel=cmd_in[1])
                    self.sendMsg('I have joined %s on %s'%(cmd_in[1:],cmd_in[0]), target)
                else:
                    out('ERROR','You tried to join a channel on a network that is not currently running')
                    self.sendMsg('I cannot join %s on %s since it is not currently connected'%(cmd_in[1:],cmd_in[0]), target)
            #if the first parameter is an alias then send the channels to join to that network
            elif cmd_in[0].lstrip().rstrip() in self.aliases:
                #if the network is currently running
                if self.aliases[cmd_in[0].lstrip()] in G.RUNNING:
                    #if there are multiple channels to send
                    if len(cmd_in[1:]) > 1:
                        G.RUNNING[self.aliases[cmd_in[0]]].joinChannel(channels=cmd_in[1:])
                    #otherwise just one channel
                    else:
                        G.RUNNING[self.aliases[cmd_in[0]]].joinChannel(channel=cmd_in[1])
                    self.sendMsg('I have joined %s on %s'%(cmd_in[1:],self.aliases[cmd_in[0]]), target)
                else:
                    out('ERROR','You tried to join a channel on a network that is not currently running')
                    self.sendMsg('I cannot join %s on %s since it is not currently connected'%(cmd_in[1:],self.aliases[cmd_in[0]]), target)
            #if the first paramter is not a network, then it must be a channel
            else:
                for chan in cmd_in:  
                    if chan[0] == "#":
                        self.connection.join(chan)
                    else:
                        self.connection.join("#"+chan)
                self.sendMsg('I have joined %s'%cmd_in, target)

    def fconnect(self, vars):
        target = vars[0]
        network = vars[1][0]
        out('CMD','connect %s'%network,site=self.name)
        if network is not None:
            #if this is an alias
            if network in G.ALIAS.keys():
                #replace it with it's real name
                network = G.ALIAS[network]
            G.LOCK.acquire()
            #check that the name given is a valid network
            if network in G.NETWORKS.keys():
                #check if the network is already running
                alreadyrunning = False
                if network in G.RUNNING:
                        alreadyrunning = True
                        self.sendMsg('That network is already running. Please %disconnect it before %connecting again.   [pyWHATauto]', target)
                
                if not alreadyrunning:
                    G.RUNNING[network] = autoBOT(network,G.NETWORKS[network])
                    reloadConfigs()
                    #now run the last appended bot and tell it to connect!
                    G.RUNNING[network].connect()
                    self.sendMsg('I am connecting to %s now.   [pyWHATauto]'%network, target)
            else:
                self.sendMsg('I have no information on a network named \'%s\'. Does it sound right to you?   [pyWHATauto]'%network, target)
            G.LOCK.release()
        else:
            self.sendMsg('That is not a full command. Format: %connect <network>   [pyWHATauto]', target)
    
    def fpart(self, vars):
        target= vars[0]
        cmd_in = vars[1]
        out('CMD','part %s' %cmd_in,site=self.name)
        #check that the channel starts with # otherwise append it!
        if cmd_in is not None:
            #if the first parameter is a network then send the channels to join to that network
            if cmd_in[0] in SETUP.items("sites"):
                #if the network is currently running
                if cmd_in[0] in G.RUNNING:
                    #if there are multiple channels to send
                    if len(cmd_in[1:]) > 1:
                        G.RUNNING[cmd_in[0]].partChannel(channels=cmd_in[1:])
                    #otherwise just one channel
                    else:
                        print cmd_in[1]
                        G.RUNNING[cmd_in[0]].partChannel(channel=cmd_in[1])
                    self.sendMsg('I have parted %s on %s'%(cmd_in[1:],cmd_in[0]), target)
                else:
                    out('ERROR','You tried to part a channel on a network that is not currently running')
                    self.sendMsg('I cannot part %s on %s since it is not currently connected'%(cmd_in[1:],cmd_in[0]), target)
            #if the first parameter is an alias then send the channels to join to that network
            elif cmd_in[0].lstrip().rstrip() in self.aliases:
                #if the network is currently running
                if self.aliases[cmd_in[0].lstrip()] in G.RUNNING:
                    #if there are multiple channels to send
                    if len(cmd_in[1:]) > 1:
                        G.RUNNING[self.aliases[cmd_in[0]]].partChannel(channels=cmd_in[1:])
                    #otherwise just one channel
                    else:
                        G.RUNNING[self.aliases[cmd_in[0]]].partChannel(channel=cmd_in[1])
                    self.sendMsg('I have parted %s on %s'%(cmd_in[1:],self.aliases[cmd_in[0]]), target)
                else:
                    out('ERROR','You tried to part a channel on a network that is not currently running')
                    self.sendMsg('I cannot part %s on %s since it is not currently connected'%(cmd_in[1:],self.aliases[cmd_in[0]]), target)
            #if the first paramter is not a network, then it must be a channel
            else:
                for chan in cmd_in:  
                    if chan[0] == "#":
                        self.connection.part(chan,self.partPhrase)
                    else:
                        self.connection.part("#"+chan,self.partPhrase)
                self.sendMsg('I have parted %s'%cmd_in, target)
        
    def fstats(self, vars):
        target = vars[0]
        msg = vars[1]
        out('CMD','stats',site=self.name)
        G.LOCK.acquire()
        for key, enabled in G.RUNNING.items():
            try:
                seen = G.REPORTS[enabled.getBotName()]['seen']
                downloaded = G.REPORTS[enabled.getBotName()]['downloaded']
                msg = 'site: %s'%enabled.getBotName()
                for x in range(len(enabled.getBotName()), 18):
                    msg+= ' '
                msg += 'seen: %s'%seen
                for x in range(len(str(seen)),6):
                    msg+= ' '
                msg += 'downloaded: %s'%downloaded
                self.sendMsg(msg, target)
            except KeyError, e:
                out('ERROR','No reports yet for %s'%e,site=self.name)           
        G.LOCK.release()
    
    def ftime(self, vars):
        target = vars[0]
        out('CMD','time',site=self.name)
        self.sendMsg(datetime.datetime.now().strftime("The date is %A %m/%d/%Y and the time is %I:%M:%S in the %p.   [pyWHATauto]"), target)
    
    def fcycle(self, vars):
        target = vars[0]
        out('CMD','cycle '+target,site=self.name)
        self.connection.part(target)
        self.connection.join(target)
    
    def fsites(self, vars):
        target = vars[0]
        out('CMD','sites',site=self.name)
        G.LOCK.acquire()
        self.sendMsg('Site Names: ', target)
        run = '[RUNNING] '
        for key,site in G.RUNNING.items():
            if SETUP.has_option('aliases', site.getBotName()):
                run += "%s=%s, "%(site.getBotName(),SETUP.get('aliases', site.getBotName()))
            elif CUSTOM.has_option('aliases', site.getBotName()):
                run += "%s=%s, "%(site.getBotName(),SETUP.get('aliases', site.getBotName()))
        self.sendMsg(run, target)
        output = '[AVAILABLE] '
        for alias, site in self.aliases.items():
            if site not in run:
                output += "%s=%s, "%(site, alias)
        output += '   [pyWHATauto]' 
        G.LOCK.release()          
        self.sendMsg(output, target)
    
    def fcmd(self,vars):
        target = vars[0]
        if vars[1] is not None:
            cmd = ''
            for c in vars[1]:
                cmd += c + " "
            cmd = cmd.rstrip()
            out('CMD','cmd: %s'%cmd,site=self.name)
            self.connection.send_raw(cmd)
        else:
            self.sendMsg('That is not a full command. Example: %cmd privmsg :johnnyfive Are you alive? Will send a private message to johnnyfive.',target)
        
    def fdownload(self, vars):
        target = vars[0]
        if vars[1] is not None:
            switch = vars[1]
            out('CMD','download %s'%(switch),site=self.name)
            if len(switch) != 2:
                self.sendMsg('That is not a full command. Format: %download <site> <torrentID>' , target)
#            try:
            if CRED.has_section(switch[0]):
                self.sendMsg('Downloading %s from %s.    [pyWHATauto]'%(switch[1], switch[0]), target)
                if G.TESTING:
                    #downloadID, downloadType, site, location=False, network=False, target=False
                    download(switch[1], REGEX.get(switch[0], 'downloadtype'), switch[0], network=self, target=target)
                else:
                    kwargs = {'network':self,'target':target}
                    thread.start_new_thread(download, (switch[1], REGEX.get(switch[0], 'downloadtype'),switch[0]), kwargs)
            elif switch[0] in self.aliases:
                self.sendMsg('Downloading %s from %s.    [pyWHATauto]'%(switch[1], self.aliases[switch[0]]), target)
                if G.TESTING:
					# TnS
					#download(switch[1], G.NETWORKS[self.aliases[switch[0]]]['regex']['downloadtype'], self.aliases[switch[0]], network=self, target=target)
                    download(switch[1], "1", self.aliases[switch[0]], network=self, target=target)
                else:
                    kwargs = {'network':self,'target':target}
                    # TnS
                    #thread.start_new_thread(download, (switch[1], G.NETWORKS[self.aliases[switch[0]]]['regex']['downloadtype'], self.aliases[switch[0]]),kwargs)
                    thread.start_new_thread(download, (switch[1], "1", self.aliases[switch[0]]),kwargs)
            else:
                self.sendMsg('That site name does not seem valid. Type %sites to see a full list.   [pyWHATauto]',target)
#            except Exception, e:
#                print e
#                self.sendMsg('There was an error with that command. Error: %s.   [pyWHATauto]' %e, target)
        else:
            self.sendMsg('That is not a full command. Format: %download <site> <torrentID>' , target)
    
    def fhelp(self, vars):
        target = vars[0]
        switch = vars[1]
        commands = vars[2]
        out('CMD','help %s'%(switch),site=self.name)
        if switch is None:
            self.sendMsg('Commands: %help <topic>, %current, %update, %filter, %quit, %connect, %disconnect, %time, %uptime, %stats, %statsreset, %version, %sites, %free/%drive, %join, %whois, %part, %download, %reload, %whois, %update, %cycle, %ghost, %nick, %cmd   [pyWHATauto]', target)
        else:
            try:
                self.sendMsg(commands[switch[0]]['help'], target)
            except KeyError:
                self.sendMsg('That command does not exist. Try %help to see a list of commands.   [pyWHATauto]', target)
                
    def fversion(self, vars):
        target = vars[0]
        out('CMD','version',site=self.name)
        self.sendMsg('I am currently running pyWA version %s and regex.conf version %s by johnnyfive.'%(VERSION, G.REGVERSION), target)
    
    def fghost(self, vars):
        target = vars[0]
        out('CMD','ghost',site=self.name)
        self.connection.privmsg('nickserv', "GHOST %s %s" %(self.creds['botnick'], self.creds['nickservpass']))
        self.connection.nick(self.creds['botnick'])
        self.connection.privmsg("nickserv","identify " + self.creds['nickservpass'])
        self.sendMsg('Ghost command sent.   [pyWHATauto]',target)
    
    def fuptime(self, vars):
        out('CMD','uptime',site=self.name)
        target = vars[0]
        dtime = datetime.datetime.now() - G.STARTTIME
        hours, minutes = 0, 0
        days = dtime.days
        seconds = dtime.seconds
        if days > 1:
            days = '%s days, '%days
        elif days == 1:
            days = '1 day, '
        else:
            days = ''
        if seconds >= 3600:
            hours = seconds / 3600
            seconds = seconds - 3600 * hours
        if hours > 1:
            hours = '%s hours, '%hours
        elif hours == 1:
            hours = '1 hour, '
        else:
            hours = ''
        if dtime.seconds >= 60:
            minutes = seconds / 60
            seconds = seconds - 60 * minutes
        if minutes > 1:
            minutes = '%s minutes, '%minutes
        elif minutes == 1:
            minutes = '1 minute, '
        else:
            minutes = ''
        if seconds > 1:
            seconds = '%s seconds.'%seconds
        elif seconds == 1:
            seconds = '1 second.'
        else:
            seconds = '.'
        seconds += '   [pyWHATauto]'
        self.sendMsg('I have been running for: %s%s%s%s'%(days, hours, minutes, seconds),target)
    
    def fstatsreset(self, vars):
        target = vars[0]
        out('CMD','statsreset',site=self.name)
        G.LOCK.acquire()
        for section in G.REPORTS.keys():
            G.REPORTS[section]['seen'] = 0
            G.REPORTS[section]['downloaded'] = 0
        G.LOCK.release()
        self.sendMsg('The stats reset command has been issued.   [pyWHATauto]', target)
        
    def fcurrent(self, vars):
        nick = vars[3]
        out('CMD','current',site=self.name)
        #quickly copy the current config to local memory, and release it.
        G.LOCK.acquire()
        dsections = dict()
        for section in FILTERS.sections():
            dsections[section]=list()
            for filter in FILTERS.items(section):
                dsections[section].append(filter)
        G.LOCK.release()
        #then go through the lengthy process of sending the filters to IRC
        timer = 0
        #for every section        
        for section in dsections.keys():
            self.sendMsg('***Section: '+section, nick)
            timer += 1
            #for every filter item in each section
            for filter in dsections[section]:
                filtertitle = False
                testmsg = ''
                allowedmsg = ''
                #for each value in each filter item seperated by a ,
                for cvalue in filter[1].split(','): 
                    #for each value in each filter item seperated by a newline
                    for nvalue in cvalue.split('\n'):
                        #strip the white space characters
                        nvalue = nvalue.rstrip()
                        nvalue = nvalue.lstrip()
                        if nvalue != '':
                            #if the filter title hasn't been added to this message.
                            if not filtertitle:
                                testmsg = filter[0] + ": "
                                filtertitle = True
                            else:
                                if len(allowedmsg) != 0:
                                    testmsg += ", "
                            testmsg += nvalue
                            #if the message length plus the length of the nick plus the 12 required padding characters is less than the max IRC message
                            #then it's an allowed message. Let's try adding the next part and see if it also fits
                            if len(testmsg)+len(nick)+12 < 472:
                                allowedmsg = testmsg
                            #if it doesn't then send the last allowedmsg
                            else:
                                if timer >= 4:
                                    time.sleep(.5)
                                    timer = 0
                                self.sendMsg(allowedmsg, nick)
                                allowedmsg = filter[0] + ": " + nvalue
                                testmsg = filter[0] + ": " + nvalue
                                #and clear the testmsg by setting it to the filter option
                if len(allowedmsg) > 0:
                    self.sendMsg(allowedmsg, nick)             
                    
if __name__ == "__main__":
    main()
