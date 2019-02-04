Quick installation
==================

Run these commands from Linux's shell. (Most likely you have to use PuTTY.)

```
mkdir PTP
cd PTP
git clone https://github.com/TnS-hun/PtpUploader.git Program
wget https://pypi.python.org/packages/source/v/virtualenv/virtualenv-12.1.1.tar.gz
tar xvfz virtualenv-12.1.1.tar.gz
python virtualenv-12.1.1/virtualenv.py -v --distribute MyEnv

MyEnv/bin/pip install requests[security] || true
MyEnv/bin/pip install watchdog
MyEnv/bin/pip install https://github.com/alberanid/imdbpy/archive/imdbpy-legacy.tar.gz
MyEnv/bin/pip install https://github.com/kannibalox/PtpUploader/archive/develop.tar.gz
MyEnv/bin/pyroadmin --create-config

mkdir WorkingDirectory
cp Program/src/PtpUploader/Settings.example.ini Program/src/PtpUploader/Settings.ini
```

If you want to bypass CloudFlare's browser verification also run this:
```
MyEnv/bin/pip install cfscrape
MyEnv/bin/pip install PyExecJS
wget https://github.com/emmetio/pyv8-binaries/raw/master/pyv8-linux64.zip
unzip pyv8-linux64.zip
mv _PyV8.so Program/src/PtpUploader/
mv PyV8.py Program/src/PtpUploader/
rm pyv8-linux64.zip
```

If you're using Transmission also run this:
```
MyEnv/bin/pip install transmissionrpc
```

Edit and fill out the details in Program/src/PtpUploader/Settings.ini.

See the "Starting PtpUploader in the background" section for how to start it.

Installation details
====================

PtpUploader needs Python. Only version 2.6 and 2.7 are supported.

Depends on the following Python packages:
	- Flask: http://flask.pocoo.org/
	- poster: http://atlee.ca/software/poster/
	- PyroScope: http://code.google.com/p/pyroscope/
	- PyV8: https://code.google.com/p/pyv8/
		- Optional dependency, used by cfscrape to bypass CloudFlare.
	- Requests: http://docs.python-requests.org/en/latest/
	- SQLAlchemy: http://www.sqlalchemy.org/
	- transmissionrpc
		- This is only needed for Transmission.
	- watchdog: https://github.com/gorakhargosh/watchdog

Required programs:
	- MediaInfo: http://mediainfo.sourceforge.net/
	- mktorrent: http://mktorrent.sourceforge.net/
	- unrar: http://www.rarlab.com/rar_add.htm

One of them is required:
	- mpv: https://mpv.io/ -- this is the recommended program for taking screenshots
	- ffmpeg: http://www.ffmpeg.org/
	- MPlayer: http://www.mplayerhq.hu/

Optional programs:
	- ImageMagick: http://www.imagemagick.org/
		- Highly recommended for losslessly compressing the PNGs
	- FlexGet: http://flexget.com/
	- autodl-irssi: http://sourceforge.net/projects/autodl-irssi/

One of the following torrent clients is required:
	- rTorrent: http://libtorrent.rakshasa.no/
		- This is the recommended client. It supports fast resume.
	- Transmission: https://www.transmissionbt.com/

Extracting PtpUploader
======================

Recommended directory structure:
	- PTP
		- Program
		- WorkingDirectory

The easiest way is to get the source straight from GitHub:
```
cd ~/PTP
git clone https://github.com/TnS-hun/PtpUploader.git Program
```

Installing FFmpeg (optional)
============================

1. Create a temporary folder
2. Download the static build of FFmpeg to the temporary folder from here: https://sites.google.com/site/linuxencoding/builds
3. Extract it: `tar xvjf name_of_the_file.tar.bz2`
4. Move the file "ffmpeg" to a more convenient location
5. Delete the temporary folder
6. Set the FfmpegPath in Settings.ini and make sure that MplayerPath and MpvPath are commented out.

Compiling the latest version of MediaInfo (optional)
====================================================
1. Create a temporary folder
2. Download CLI from All in one package from this page into the temporary directory: http://mediaarea.net/en/MediaInfo/Download/Source
3. Extract it: `tar xvjf name_of_the_file.tar.bz2`
4. Compile it:
```
cd MediaInfo_CLI_GNU_FromSource/
./CLI_Compile.sh
```
4. Move the file "MediaInfo/Project/GNU/CLI/mediainfo" to a more convenient location
5. Delete the temporary folder
6. Set the MediaInfoPath in Settings.ini.

Configuring autodl-irssi (optional)
===================================

Install irssi ( http://www.irssi.org/ ).

Install auodl-irssi:
```
mkdir -p ~/.irssi/scripts/autorun
cd ~/.irssi/scripts
wget -O autodl-irssi.zip https://github.com/autodl-irssi-community/autodl-irssi/archive/master.zip
unzip autodl-irssi.zip
rm autodl-irssi.zip
mv autodl-irssi-master/* .
rm -r autodl-irssi-master
cp autodl-irssi.pl autorun/
mkdir -p ~/.autodl
```

Copy autodl-irssi-master/autodl.example.cfg to ~/.autodl/autodl.cfg
Edit ~/.autodl/autodl.cfg and fill out the details (everything that starts with YOUR_).

Configuring FlexGet (optional)
==============================

Copy Program/src/FlexGet/config.example.yml to config.yml.
Make sure you change the path of the working directory in the config file.
FlexGet needs to run periodically to update the RSS feeds.
See FlexGet's documentation for details: http://flexget.com/wiki/InstallWizard/Linux/NoRoot/Virtualenv/Scheduling

Making sure UTF-8 character encoding is set (optional)
======================================================

If you want to upload releases with accented characters you have to configure your
environment because in some Linux distributions character encoding is not set by default.

In `~/.profile` or `~/.bash_profile` set the following:
```
export LANG=en_US.UTF-8
export LOCALE=UTF-8
```

Entering this command in your terminal should print out an Euro sign (€):
```
echo -e '\xe2\x82\xac'
```

Using https (optional)
======================

This is useful if you want to use the Torrent Sender Greasemonkey script from https sites.

Install pyOpenSSL:
```
MyEnv/bin/pip install pyopenssl
```

To create a self-signed SSL certificate run the following commands (when asked for input just press Enter):
````
openssl genrsa -des3 -passout pass:1234 -out server.pass.key 2048
openssl rsa -passin pass:1234 -in server.pass.key -out server.key
rm server.pass.key
openssl req -new -batch -key server.key -out server.csr
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
rm server.csr
```

Set WebServerSslCertificatePath to the path of server.crt and WebServerSslPrivateKeyPath to the path of server.key in Settings.ini.

When first accessing PtpUploader with the https address your browser will show a warning. Just add the exception.

Starting PtpUploader in the background
======================================

Enter into your PTP directory (e.g.: cd `~/PTP`) then use the following command:
```
screen -S PtpUploader MyEnv/bin/PtpUploader
```

Use Ctrl+A, D to disconnect from screen. You can use `screen -r PtpUploader` to reconnect.

Updating PtpUploader
====================

1. Stop PtpUploader
2. Enter into your PTP directory (e.g.: `cd ~/PTP`) then use the following command
2. `MyEnv/bin/pip install -U https://github.com/kannibalox/PtpUploader/archive/develop.tar.gz`
3. Start PtpUploader

Updating the Python modules installed earlier (optional but recommended monthly)
================================================================================

```
cd PTP
MyEnv/bin/pip freeze --local | grep -v '^\-e' | cut -d = -f 1 | xargs MyEnv/bin/pip install -U
```

You can also add this to crontab so it does it automatically.
