## [0.12.1]
### Fixed
- Allow loading .torrent files from the announce directory

## [0.12.0]
### Changed
- Allow selecting files manually
### Fixed
- Respect the ignore_files config setting properly

## [0.11.3]
### Changed
- Due to new restrictions for pypi, the cinemagoer package now uses
  the newest version uploaded on pypi, as opposed to installing
  directly from git (the recommended way to install by the
  project). To use the recommended installation method, run `pip
  install git+https://github.com/cinemagoer/cinemagoer` manually

### Fixed
- Check if PNGs are 16-bit and downgrade the depth when imagemagick is
  present.
- Bypass "multiple" attribute exception in Django.
- Disable scene check by default

### Added
- Malay subtitle option

## [0.11.2]
### Fixed
- Typo in scene result check

## [0.11.1]
### Fixed
- Ignore missing result during srrdb.com check
- Update objects being passed to pyrosimple

## [0.11.0]
### Added
- Experimental libmpv screenshot tool. This is primarily to help with
  keyframe-reliant codecs like VC1 that would other produce grey
  screenshots, but has not been vetted as well as the mpv
  CLI. Requires optional dependencies: `pip install pillow mpv`.
### Fixed
- Better blu-ray support
### Changed
- ReleaseInfoMaker improvements

## [0.10.2]
### Fixed
- Config option to disable recursive deletes
- Remove accented characters from CG folders
- Use IFO to detect DVD subtitles when possible

## [0.10.1]
### Fixed
- Properly ignore PTP directory when extracting releases from directories
- Two bugs from refactoring/linting efforts (#27, #28)

## [0.10.0] - 2022-06-04
### Changed
- Update CSS/JS dependencies
- Move blu-ray support out of experimental support
### Fixed
- Improve CG failed login handling
- Improve x264/x265 detection from filenames
- Auto-create VIDEO_TS folder if not present

## [0.9.1] - 2022-05-20
### Added
- 2FA support
