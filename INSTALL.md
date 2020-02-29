Quick installation
==================

Run these commands from the Windows command prompt or, better yet, save them to a \*.bat file and run it in the directory you want to install it. 

```
SET VENV_VERSION=16.4.3
mkdir .\.local\ptpuploader\virtualenv-%VENV_VERSION% .\.config\ptpuploader\
cd ./.local/ptpuploader/
curl --location --output virtualenv-%VENV_VERSION%.tar.gz https://github.com/pypa/virtualenv/tarball/%VENV_VERSION%
tar xvzf virtualenv-%VENV_VERSION%.tar.gz -C virtualenv-%VENV_VERSION% --strip-components 1
python virtualenv-%VENV_VERSION%/virtualenv.py ./
.\Scripts\pip install git+https://github.com/kannibalox/pyrocore.git@py3
.\Scripts\pip install git+https://github.com/kannibalox/pyrobase.git@py3 pyrocore
.\Scripts\pip install https://github.com/bobbintb/PtpUploader/archive/develop.tar.gz
.\Scripts\pip install "requests[security]" || true
cd ..
cd ..
cd .\.config\ptpuploader
curl -sSL https://github.com/bobbintb/PtpUploader/raw/develop/src/PtpUploader/Settings.example.ini > settings.ini
curl -sSL https://github.com/bobbintb/PtpUploader/raw/develop/src/PtpUploader/SceneGroups.txt > scene_groups.txt
```

If you're using rTorrent also run this:
```
~/.local/ptpuploader/bin/pyroadmin --create-config
```
If you're using Transmission also run this:
```
~/.local/ptpuploader/bin/pip install transmissionrpc
```

If you want to bypass CloudFlare's browser verification also run this:
```
~/.local/ptpuploader/bin/pip install cfscrape
~/.local/ptpuploader/bin/pip install PyExecJS
~/.local/ptpuploader/bin/pip install pyv8
```
If the last command fails, you can install the binary manually
```
wget https://github.com/emmetio/pyv8-binaries/raw/master/pyv8-linux64.zip
unzip pyv8-linux64.zip
mv _PyV8.so ~/.local/ptpuploader/lib/
mv PyV8.py ~/.local/ptpuploader/lib/
rm pyv8-linux64.zip
```

Edit and fill out the details in `~/.config/ptpuploader/settings.ini`.

See the "Starting PtpUploader" section for how to start it.

Installation details
====================

PtpUploader needs Python. Only version 2.7 is supported (earlier versions may work, but no support is provided for them).

Depends on the following Python packages:
- PyV8: https://code.google.com/p/pyv8/
  - Optional dependency, used by cfscrape to bypass CloudFlare.
- transmissionrpc
  - Optional: This is only needed for Transmission.

Required programs:
- MediaInfo: http://mediainfo.sourceforge.net/
- unrar: http://www.rarlab.com/rar_add.htm

One of these is required for taking screenshots:
- mpv: https://mpv.io/
  - This is the recommended program
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

Making sure UTF-8 character encoding is set
===========================================

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

Setting up HTTPS (optional)
======================

This is useful if you want to use the Torrent Sender Greasemonkey script from https sites.

Install pyOpenSSL:
```
MyEnv/bin/pip install pyopenssl
```

To create a self-signed SSL certificate run the following commands (when asked for input just press Enter):

```
openssl genrsa -des3 -passout pass:1234 -out server.pass.key 2048
openssl rsa -passin pass:1234 -in server.pass.key -out server.key
rm server.pass.key
openssl req -new -batch -key server.key -out server.csr
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
rm server.csr
```

Set WebServerSslCertificatePath to the path of server.crt and WebServerSslPrivateKeyPath to the path of server.key in Settings.ini.

When first accessing PtpUploader with the https address your browser will show a warning. Just add the exception.

Starting PtpUploader
====================

To run PtpUploader in the foreground:
```
source ~/.local/ptpuploader/bin/activate
PtpUploader
```
To run PtpUploader in the background in `tmux` (recommended):
```
tmux -2u new PtpUploader "~/.local/ptpuploader/bin/PtpUploader; exec bash"
```
To run PtpUploader in the background in `screen`:
```
screen -S PtpUploader ~/.local/ptpuploader/bin/PtpUploader
```

Enter into your PTP directory (e.g.: cd `~/PTP`) then use the following command:

```
screen -S PtpUploader MyEnv/bin/PtpUploader
```

Use Ctrl+A, D to disconnect from screen. You can use `screen -r PtpUploader` to reconnect.

Updating PtpUploader
====================

1. Stop PtpUploader
2. Run `~/.local/ptpuploader/bin/pip install -U https://github.com/kannibalox/PtpUploader/archive/develop.tar.gz`
3. Start PtpUploader

Command line only usage
=======================

PtpUploader can create release description (with media info and screenshots) for manual uploading from command line.
```
source ~/.local/ptpuploader/bin/activate
ReleaseInfoMaker --help
```

Syntax:
* `ReleaseInfoMaker <target directory or filename>` creates the release description and starts seeding the torrent.
* `ReleaseInfoMaker --notorrent <target directory or filename>` creates the release description.
* `ReleaseInfoMaker --noscreens <target directory or filename>` creates the release description, without screenshots.

Use the resulting torrent that starts with PTP for uploading to the tracker.

