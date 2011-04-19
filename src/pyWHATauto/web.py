'''
Created on Aug 13, 2010

@author: JohnnyFive
'''

import cgi, time, sqlite3, os
from threading import Thread
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

CONN = False
C = False
webpass = "fun"

if __name__ != '__main__':
    import __main__

class WebServer( Thread ):
    
    def __init__(self, loadloc, pw, port):
        global webpass
        Thread.__init__(self)
        self.loadloc = loadloc
        self.port = port
        webpass = pw
  
    def run(self):
        global CONN, C
        CONN = sqlite3.connect(os.path.join(self.loadloc, 'example.db'))
        #CONN = sqlite3.connect(":memory:")
        C = CONN.cursor()
        
        self.server = HTTPServer(('', int(self.port)), MyHandler)
        print 'started httpserver...'
        self.server.serve_forever()

class MyHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        try:
            if self.path.split('?')[0].lower().endswith(".pywa"):   #our dynamic content
                if self.path.startswith("/index"):
                    self.send_response(200)
                    self.send_header('Content-type',    'text/html')
                    self.end_headers()
                    C.execute('SELECT name FROM sqlite_master')
                    for table in C:
                        self.wfile.write('SITE: %s<br>'%table)
                        self.wfile.write("<p>")
                        C.execute('SELECT * FROM %s'%table)
                        for row in C:
                            for item in row:
                                if type(item) == 'string': 
                                    self.wfile.write("%s | "%item.decode('utf-8'))
                                else:
                                    self.wfile.write("%s | "%item)
                            self.wfile.write("<br>")
                        self.wfile.write("</p>")
                elif self.path.startswith("/test"):
                    self.send_response(200)
                    self.send_header('Content-type',    'text/html')
                    self.end_headers()
                    self.wfile.write('<a href="http://127.0.0.1:8080/dl.pywa?pass=fun&site=what&id=825235">link</a>')
                elif self.path.startswith("/dl"):
                    arg = self.path.split("?")
                    arg = arg[1].split('&')
                    args = dict()
                    for a in arg:
                        args[a.split('=')[0]] = a.split('=')[1]
                    if 'pass' in args and args['pass'] == webpass:
                        print "WebUI download request for id '%s' from '%s'."%(args['id'], args['site'])
                        if 'name' in args:
                            ok = __main__.dlFromWeb(args['site'], args['id'], name=args['name'])
                        else:
                            ok = __main__.dlFromWeb(args['site'], args['id'])
                        self.send_response(200)
                        self.send_header('Content-type',    'text/html')
                        self.end_headers()
                        if ok:
                            self.wfile.write("<html><head><script>t = null;function moveMe(){t = setTimeout(\"self.open('close.pywa','_self')\",1000);}</script></head><body onload=\"moveMe()\">")
                            self.wfile.write("Download started for id '%s' from '%s'."%(args['id'], args['site']))
                            self.wfile.write("</body></html>")
                        else:
                            self.wfile.write("There was an error in your request. Try double-checking the site name.")      
                    else:
                        self.send_response(200)
                        self.send_header('Content-type',    'text/html')
                        self.end_headers()
                        self.wfile.write("Incorrect password supplied. Try again.")
                        __main__.out('ERROR','Received a webUI download command with the wrong password.',args['site'])
                elif self.path.startswith("/close"):
                    self.send_response(200)
                    self.send_header('Content-type',    'text/html')
                    self.end_headers()
                    self.wfile.write("<html><head><script language=\"javascript\" type=\"text/javascript\">self.close();</script></head><body>")
                    self.wfile.write("</body></html>")
                
            return
                
        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)

def main():
    
    import sys    
        
    try:
        WEB = WebServer(os.path.join(os.path.realpath(os.path.dirname(sys.argv[0]))), webpass)
        WEB.start()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    main()

