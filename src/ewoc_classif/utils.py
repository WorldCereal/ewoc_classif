import argparse
import logging
import os
import shutil
import sys
from datetime import datetime
from distutils.util import strtobool
from pathlib import Path
from typing import Dict, List

import pandas as pd
from loguru import logger


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
    elem_to_del = list(folder.rglob(f"*{suffix}"))
    for elem in elem_to_del:
        if elem.is_dir():
            shutil.rmtree(elem)
            logger.info(f"Deleted tmp file: {elem}")
        elif elem.is_file():
            elem.unlink()
            logger.info(f"Deleted tmp file: {elem}")


def generate_config_file(
    featuresettings: str,
    end_season_year: str,
    ewoc_season: str,
    production_id: str,
    model_version: str,
    csv_dict: Dict,
) -> Dict:
    parameters = {
        "year": end_season_year,
        "season": ewoc_season,
        "featuresettings": featuresettings,
        "save_confidence": True,
        "save_features": False,
        "localmodels": True,
        "segment": False,
        "filtersettings": {"kernelsize": 3, "conf_threshold": 0.85},
    }

    if featuresettings == "cropland":
        logger.info("Updating config file for cropland")
        models = {
            "annualcropland": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/cropland_detector_WorldCerealPixelCatBoost/config.json"
        }
        config = {"parameters": parameters, "inputs": csv_dict, "models": models}
        return config
    elif featuresettings == "croptype":
        is_dev = strtobool(os.getenv("EWOC_DEV_MODE", "False"))
        if is_dev:
            cropland_mask_bucket = f"s3://ewoc-prd-dev/{production_id}"
        else:
            cropland_mask_bucket = f"s3://ewoc-prd/{production_id}"

        logger.info("Updating config file for croptype")
        parameters["filtersettings"] = {"kernelsize": 7, "conf_threshold": 0.75}
        parameters.update(
            {
                "active_marker": True,
                "cropland_mask": cropland_mask_bucket,
                "irrigation": True,
                "irrparameters": "irrigation",
                "irrmodels": {
                    "irrigation": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/irrigation_detector_WorldCerealPixelCatBoost/config.json"
                },
            }
        )
        if ewoc_season == "summer1":
            models = {
                "maize": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/maize_detector_WorldCerealPixelCatBoost/config.json",
                "springcereals": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/springcereals_detector_WorldCerealPixelCatBoost/config.json",
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            return config
        elif ewoc_season == "summer2":
            models = {
                "maize": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/maize_detector_WorldCerealPixelCatBoost/config.json"
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            return config
        elif ewoc_season == "winter":
            models = {
                "winterwheat": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/winterwheat_detector_WorldCerealPixelCatBoost/config.json",
                "wintercereals": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/wintercereals_detector_WorldCerealPixelCatBoost/config.json",
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            return config


def update_agera5_bucket(filepath: Path) -> None:
    pod_index = os.getenv("POD_INDEX", 20)
    nb_buckets = os.getenv("NB_BUCKETS", 20)
    b_index = str((int(pod_index) % int(nb_buckets)) + 1)
    # Calculate new agera5 bucket index and replace in bucket name
    ag_bucket = f"s3://ewoc-agera5-{b_index.zfill(2)}/"
    old_bucket = "s3://ewoc-aux-data/"
    # Read agera5 csv
    df = pd.read_csv(filepath)
    # replace old bucket name
    df["path"].replace(old_bucket, ag_bucket, regex=True, inplace=True)
    # remove Unnamed: 0 column
    if "Unnamed: 0" in df.columns:
        df.drop("Unnamed: 0", axis=1, inplace=True)
    # Overwrite existing file
    df.to_csv(filepath)
    logger.info(f"Update Agera5 csv with {ag_bucket}")


def check_outfold(outdir: Path) -> None:
    if outdir.exists():
        dir_content = outdir.iterdir()
        if len(list(dir_content)) != 0:
            return True
    else:
        logger.info(f"Empty or non existing folder {outdir}")
        return False

