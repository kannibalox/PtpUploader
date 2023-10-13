import re
from pathlib import Path

from PtpUploader.Settings import config
from PtpUploader.release_extractor import find_allowed_files

def set_included_upload_files(release, overwrite=False):
    if release.SourceIsAFile():
        return
    if release.IncludedFileList and not overwrite:
        return
    vids, addtls = find_allowed_files(Path(release.GetReleaseUploadPath()))
    release.IncludedFileList = vids + addtls
