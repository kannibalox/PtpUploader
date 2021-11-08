# PtpUploader
A small uploader for a mildly popular movie site

## Quick start

### Docker

1. Start the daemon in the background
```bash
sudo docker build -t ptpuploader .
sudo docker run ptpuploader -d \
    -v $PWD/data:/data -p 8000:8000 \
    -e PTP_USERNAME=<fill this in> \
    -e PTP_PASSWORD=<fill this in> \
    -e PTP_PASSKEY=<fill this in> \
```
2. Add an admin user.
3. Navigate to [https://localhost:8000] and log in.

##### Changelog

Many things have changed in version 1.0. Most importantly, only python 3+ is supported.

Non-exhaustive list of other changes:
- Reduce login sessions by storing cookie
- Update UI
- Allow viewing screenshots in edit page
- TODO: Bulk uploads
- Prowlarr integration

##### About

With the PtpUploader's WebUI you can upload to PTP by specifying a torrent file and an IMDb or PTP link.
There is also an automatic mode built-in that can check announcements from IRC or RSS and upload everything automatically.

Supported sites for automatic mode:
* AlphaRatio
* Cinemageddon
* Cinematik
* DigitalHive
	* Thanks to CoFix!
* GFT
* HDBits
	* Thanks to cerbere!
* HD-Torrents
	* Thanks to Mako_1!
*  Karagarga
* TorrentBytes
* TorrentLeech
* FunFile
	* Thanks to dhosha!

SceneAccess support was removed on the 9th of July 2013 because of staff pressure...
RevolutionTT support was removed on the 15th of May 2015 because of staff pressure...

There is a helper [Greasemonkey script](https://raw.githubusercontent.com/TnS-hun/PtpUploader/master/PtpUploaderTorrentSender.user.js) available at to send torrents from a wide variety of sites directly to PtpUploader.

#### Questions, help

See [INSTALL.md](INSTALL.md) for installation instructions.

Support is provided on [PTP](https://passthepopcorn.me/forums.php?action=viewthread&threadid=9245).
