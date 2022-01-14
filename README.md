# PtpUploader
A small uploader for a mildly popular movie site

## About

With the PtpUploader's WebUI you can upload to PTP by specifying a torrent and an IMDb or PTP link. The torrent
can be a local path, a link to another site, or a literal `.torrent` file.

There is also an automatic mode built-in that can check announcements from IRC or RSS and upload everything automatically.

## Quick start

### Manual

1. Install required dependencies:
This is example is for Ubuntu, the exact command/package names may change depending on your distro
```bash
sudo apt install python3 mpv imagemagick mediainfo
## Optional but highly recommended
# sudo apt install python3-venv
# virtualenv ~/.venv/ptpuploader/
# source ~/.venv/ptpuploader/bin/activate
## End optional section
pip install https://github.com/kannibalox/PtpUploader/archive/refs/heads/main.tar.gz
```
2. Create the config file
```bash
mkdir -pv ~/.config/ptpuploader/
cp src/PtpUploader/config.default.yml ~/.config/ptpuploader/config.yml
nano ~/.config/ptpuploader/config.yml # Edit config file as desired
```
3. Start the process
```bash
python -m PtpUploader.manage runuploader 0.0.0.0:8000
```
### Docker

1. Clone the repo
```bash
git clone https://github.com/kannibalox/PtpUploader.git
cd PtpUploader/
```
2. Create the config file
```
mkdir -pv ~/.config/ptpuploader/
cp src/PtpUploader/config.default.yml ~/.config/ptpuploader/config.yml
nano ~/.config/ptpuploader/config.yml # Edit config file as desired
```
When running in docker, be sure to enter the address to rTorrent's SCGI port (**not** ruTorrent's port).
2. Start the daemon in the background
```bash
sudo docker build -t ptpuploader .
sudo docker run ptpuploader -d \
    -v $PWD/data:/data \
    -v ~/.config/ptpuploader/:/root/.config/ptpuploader/:ro
    -p 8000:8000
```
3. Add an admin user.
```bash
sudo docker exec -it ptpuploader -d createsuperuser
```
4. Navigate to [http://localhost:8000/jobs] and enter the admin credentials.

## Changelog

Many things have changed in version 1.0. Most importantly, only python 3+ is supported.

Non-exhaustive list of other changes:
- Reduce login sessions by storing cookie
- Update UI
- Allow viewing screenshots in edit page
- Bulk uploads
- Prowlarr integration

## Questions, help

See the config file comments and [INSTALL.md](INSTALL.md) for advanced usage instructions.

Support is provided on [PTP](https://passthepopcorn.me/forums.php?action=viewthread&threadid=9245).
