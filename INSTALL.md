# Configuration

PtpUploader uses [dynaconf](https://www.dynaconf.com/) for configuration, which allows
for more complex setups than just using `config.yml`, e.g. loading values from environment
variables. Please see their documentation for details.

Django's [settings file](https://docs.djangoproject.com/en/4.0/topics/settings/) also
allows for setting up even more complex configurations. Some will be discussed here,
however trying to list all of the neat things you can do is an impossible task.

## Uploading

To start your first upload, go to `localhost:8000/upload`, and use the form to fill out as much
information as possible about your upload. One of the first three fields (link, local path, or file)
must be filled out, but anything else can be left blank, and PtpUploader will alert you if anything
is missing.

**It is still solely your responsibility to make sure any you upload has correct information
and is allowed under the rules.**

Once the job is submitted, it can viewed on the jobs page at `localhost:8000/jobs`.

### Automatic announcing 

PtpUploader has the ability to receive jobs from files placed in the announce folder
(`$WORK_DIR/announce/`). These files are JSON formatted, and allow for customizing the submitted
job with some additional information. An example of using flexget and autodl-irssi to create these
files is available in the repo.

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

