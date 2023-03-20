import re
from pathlib import Path

from PtpUploader.Settings import config


def set_included_upload_files(release, overwrite=False):
    if release.SourceIsAFile():
        return
    if release.IncludedFileList and not overwrite:
        return
    source = Path(release.GetReleaseUploadPath())
    included_files = []
    for path in source.rglob("*"):
        topdir = path.parts[0].lower()
        if topdir in config.uploader.ignore_dirs:
            continue
        if any([re.match(r, path.name) for r in config.uploader.ignore_files]):
            continue
        if path.suffix.strip(".").lower() in (
            config.uploader.video_files + config.uploader.additional_files
        ):
            included_files.append(str(path.relative_to(source)))
    release.IncludedFileList = included_files
