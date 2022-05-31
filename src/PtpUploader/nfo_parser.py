import os
import re

from pathlib import Path

from PtpUploader.Helper import GetFileListFromTorrent

IMDB_TITLE_RE = re.compile(r"imdb\.com/[Tt]itle/tt(\d+)")


def get_imdb_id(nfo_text: str) -> str:
    match = re.search(r"imdb.com/title/tt(\d+)", nfo_text)
    if match:
        return match.group(1)
    return ""


def read_nfo(path: os.PathLike) -> str:
    with Path(path).open("rb") as nfoFile:
        return nfoFile.read().decode("cp437", "ignore")


def find_and_read_nfo(directory: os.PathLike) -> str:
    # If there are multiple NFOs, it returns an empty string
    nfos = list(Path(directory).glob("*.nfo"))
    if len(nfos) != 1:
        return ""
    return read_nfo(nfos[0])


def torrent_has_multiple_nfos(torrent_path: os.PathLike) -> bool:
    found_nfo = False
    for f in GetFileListFromTorrent(torrent_path):
        fpath = Path(f)
        if fpath.parent == "." and fpath.suffix == ".nfo":
            if found_nfo:
                return True
            else:
                found_nfo = True
    return False
