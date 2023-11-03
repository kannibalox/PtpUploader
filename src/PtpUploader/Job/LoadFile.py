import json
import logging

from pathlib import Path
from typing import Dict, List

from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings


logger = logging.getLogger(__name__)


def load_json_release(path: Path):
    with path.open() as fh:
        data: Dict = json.load(fh)
    release = ReleaseInfo()
    allowed_fields: List[str] = [
        "ImdbId",
        "Title",
        "Year",
        "AnnouncementId",
        "AnnouncementSourceName",
        "CoverArtUrl",
        "Codec",
        "Container",
        "Source",
        "RemasterTitle",
        "Resolution",
    ]
    for k, v in data.items():
        if k in allowed_fields:
            if k == "Source":
                pass  # TODO: properly put things into "other" as needed
            setattr(release, k, v)
    release.JobRunningState = ReleaseInfo.JobState.WaitingForStart
    release.save()
    path.unlink()

def load_torrent_release(path: Path):
    release = ReleaseInfo()
    release.AnnouncementSourceName = "torrent"
    release.SourceTorrentFilePath = path
    release.JobRunningState = ReleaseInfo.JobState.WaitingForStart
    release.save()
    path.unlink()

def scan_dir():
    path = Path(Settings.GetAnnouncementWatchPath())
    for child in path.iterdir():
        if child.is_file():
            try:
                load_json_release(child)
                continue
            except (json.decoder.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.debug("Cannot load %r as JSON (%s), attempting .torrent check", child, exc)
            try:
                load_torrent_release(child)
                continue
            except json.decoder.JSONDecodeError:
                pass
