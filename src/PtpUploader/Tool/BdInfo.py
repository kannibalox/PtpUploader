import logging
import re
import shlex
import subprocess

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import config


logger = logging.getLogger(__name__)


def bdinfo_cmd() -> List[str]:
    if config.tools.bdinfo.path:
        return [
            str(Path(p).expanduser()) for p in shlex.split(config.tools.bdinfo.path)
        ]
    else:
        raise PtpUploaderException("BDInfo path not set")


def run(path: Path, mpls=None, extra_args=None) -> str:
    if mpls is None:
        mpls = get_longest_playlist(path)
    logger.info(f"Building bdinfo for path '{path}' and playlist '{mpls}'")
    with TemporaryDirectory() as tempdir:
        args: List[str] = bdinfo_cmd() + [str(path), tempdir, "-m", mpls]
        if extra_args:
            args.append(extra_args)
        proc = subprocess.run(args, check=True)
        for child in Path(tempdir).glob("*"):
            with child.open("r") as fh:
                text = fh.read()
            match = re.search(r"(DISC INFO:.*)FILES:", text, flags=re.M | re.S)
            if match:
                return match.group(1)
    raise PtpUploaderException(f"Could not find BDInfo output for path '{path}'")


def get_longest_playlist(path: Path) -> str:
    logger.info(f"Scanning '{path}' for playlists")
    proc = subprocess.run(
        bdinfo_cmd() + [str(path), "-l"], check=True, capture_output=True
    )
    longest_mpls: Optional[str] = None
    longest_len: int = 0
    for line in proc.stdout.decode().split("\n"):
        if ".MPLS" in line:
            length_str = line[26:34].split(':')
            length_sec = sum(
                [int(x[1]) * (60 ** (2 - x[0])) for x in enumerate(length_str)]
            )
            if length_sec > longest_len:
                longest_len = length_sec
                longest_mpls = line.split(" ")[9]
    if longest_mpls:
        return longest_mpls
    else:
        logger.error("Could not parse output: %s", proc.stdout.decode())
        raise PtpUploaderException(f"Could not find playlist from path '{path}'")
