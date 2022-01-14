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

# Installation details

PtpUploader needs Python 3.7+, as well as a couple other programs.
The docker image contains all these images by default, and most distrubutions
provide easy-to-install packages.

Required external programs:
- rTorrent or transmission
  - if transmission is being used, the transmissionrpc package must be installed
- One of: mpv (preferred), ffmpeg, mplayer
- Mediainfo

Optional external programs:
- ImageMagick: Highly recommended for losslessly compressing PNG screenshots
- FlexGet: Can be used to write announce files
- autodl-irssi: Can	be used	to write announce files

## Upgrading

For both installation methods, you can simply update the repo and follow
the installation instructions again.
```bash
cd PtpUploader
git pull
# Re-do installation
```

# Command line only usage

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

# Using an external database

By default PtpUploader will set up and use a SQLite database autoatically.
For most setups, this will work perfectly fine, however if you want to
use a separate database such as PostgreSQL or MySQL/MariaDB for
performance (e.g. adding more workers) or conveience, that's possible
via Django settings.
