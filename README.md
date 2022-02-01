# PtpUploader

A small uploader for a mildly popular movie site.

## About

With PtpUploader's WebUI you can upload to PTP by specifying a torrent and an IMDb or PTP link. The torrent
can be a local path, a link to another site, or a literal `.torrent` file.

There is also an automatic mode built-in that can check announcements from IRC or RSS and upload everything
(semi-)automatically.

**It is still solely your responsibility to make sure anything you upload has correct information
and is allowed under the rules.**

## Getting started

### Manual

1. Install required dependencies.
This is example is for Ubuntu, the exact command/package names may change depending on your distro:
```bash
sudo apt install python3 mpv imagemagick mediainfo
```
2. Install the python package:
```
## Using a dedicated virtualenv is optional but highly recommended
# sudo apt install python3-venv
# virtualenv ~/.venv/ptpuploader/
# source ~/.venv/ptpuploader/bin/activate
pip3 install PtpUploader
```
3. Create the config file:
```bash
mkdir -pv ~/.config/ptpuploader/
wget https://raw.githubusercontent.com/kannibalox/PtpUploader/main/src/PtpUploader/config.default.yml -O ~/.config/ptpuploader/config.yml
nano ~/.config/ptpuploader/config.yml # Edit config file as needed
```
4. Start the process:
```bash
PtpUploader runuploader
```
5. Add an admin user:
```bash
PtpUploader createsuperuser
```
6. Navigate to [http://localhost:8000/jobs] and enter the admin credentials.

### Docker

1. Clone the repo
```bash
git clone https://github.com/kannibalox/PtpUploader.git
cd PtpUploader/
```
2. Create the config file
```
mkdir -pv ~/.config/ptpuploader/
wget https://raw.githubusercontent.com/kannibalox/PtpUploader/main/src/PtpUploader/config.default.yml -O ~/.config/ptpuploader/config.yml
nano ~/.config/ptpuploader/config.yml # Edit config file as needed
```
When running in docker, be sure to enter the address to rTorrent's SCGI port (**not** a ruTorrent port).
2. Build the image and start the daemon in the background
```bash
sudo docker build -t ptpuploader .
sudo docker run --name ptpuploader -d \
    -v YOUR_WORK_DIR:YOUR_WORK_DIR \ # modify to match your work_dir in config.yml
    -v $HOME/.config/ptpuploader/:/root/.config/ptpuploader/
    -p 8000:8000 ptpuploader
```
3. Add an admin user.
```bash
sudo docker exec -it ptpuploader PtpUploader createsuperuser
```
4. Navigate to [http://localhost:8000/jobs] and enter the admin credentials.

## Next Steps and Help

See [INSTALL.md](INSTALL.md) and the comments in the config file for advanced usage instructions.

Support is provided on [PTP](https://passthepopcorn.me/forums.php?action=viewthread&threadid=9245) or in Github issues.

## Changelog

Many things have changed in preparation for version 1.0. Most importantly, only python 3.7+ is supported.

Non-exhaustive list of other changes:
- Reduce login sessions by write to a cookie file
- Update UI with new theme
- Allow viewing screenshots in edit page
- Add uploads in bulk
- Prowlarr integration
