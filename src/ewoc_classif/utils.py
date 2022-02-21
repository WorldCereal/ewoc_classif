import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

_logger = logging.getLogger(__name__)


def setup_logging(loglevel: int) -> None:
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel,
        stream=sys.stdout,
        format=logformat,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def valid_year(cli_str: str) -> int:
    """Check if the intput string is a valid year

    Args:
        cli_str (str): Input string to convert in year

    Raises:
        argparse.ArgumentTypeError: [description]

    Returns:
        int: a valid year as int
    """
    try:
        return datetime.strptime(cli_str, "%Y").year
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid year: {cli_str}!") from None


def remove_tmp_files(folder: Path, suffix: str) -> None:
    """
    Remove temporary files created by the classifier in cwd
    :param folder: Folder with temp files, probably cwd
    :param suffix: Pattern for the search ex 31TCJ.tif
    :return: None
    """
    files_to_del = list(folder.rglob(f"*{suffix}"))
    for file in files_to_del:
        file.unlink()
        _logger.info(f"Deleted tmp file: {file}")
