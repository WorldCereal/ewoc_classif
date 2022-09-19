# -*- coding: utf-8 -*-
"""
Helpful functions for the classification process
"""
import argparse
import json
import logging
import os
import shutil
import sys
import traceback
from datetime import datetime
from distutils.util import strtobool
from pathlib import Path
from typing import Dict

import pandas as pd
from ewoc_dag.bucket.eobucket import EOBucket
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

    Returs:
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
    cropland_model_version: str,
    croptype_model_version: str,
    irr_model_version: str,
    csv_dict: Dict,
) -> Dict:
    """
    Automatic generation of worldcereal config files
    :param featuresettings: cropland or croptype
    :type featuresettings: str
    :param end_season_year: End of season year
    :type end_season_year: str
    :param ewoc_season: The season to process: annual, summer1, summer2 or winter
    :type ewoc_season: str
    :param production_id: EWoC production ID
    :type production_id: str
    :param cropland_model_version: The AI model version used for the cropland predictions
    :type cropland_model_version: str
    :param croptype_model_version: The AI model version used for the croptype predictions
    :type croptype_model_version: str
    :param irr_model_version: The AI model version used for the irrigation
    :type irr_model_version: str
    :param csv_dict: A dictionary with the initial params of the config file
    :type csv_dict: Dict
    :return: Dict
    """
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
    # Support the switch between local models and use of artifactory
    use_local_models = os.getenv("LOCAL_MODELS", None)
    if use_local_models is None:
        model_prefix = "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal"
        logger.info(f"[Artifactory Mode] using artifactory for the models. URL: {model_prefix}")
    else:
        model_prefix = ""
        logger.info(f"[Local Models] using local models from /models {model_prefix}")
    if featuresettings == "cropland":
        logger.info("Updating config file for cropland")
        models = {
            "annualcropland": f"{model_prefix}/models/WorldCerealPixelCatBoost/{cropland_model_version}/cropland_detector_WorldCerealPixelCatBoost_{cropland_model_version}/config.json"
        }
        logger.info(f"[{featuresettings}] - Using model version: {cropland_model_version}")
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
                    "irrigation": f"{model_prefix}/models/WorldCerealPixelCatBoost/{irr_model_version}/irrigation_detector_WorldCerealPixelCatBoost_{irr_model_version}/config.json"
                },
            }
        )
        logger.info(
            f"[{featuresettings}] - Using Irrigation model version: {irr_model_version}"
        )
        if ewoc_season == "summer1":
            models = {
                "maize": f"{model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/maize_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json",
                "springcereals": f"{model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/springcereals_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json",
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            logger.info(f"[{ewoc_season}] - Using model version: {croptype_model_version}")
            return config
        elif ewoc_season == "summer2":
            models = {
                "maize": f"{model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/maize_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json"
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            logger.info(f"[{ewoc_season}] - Using model version: {croptype_model_version}")
            return config
        elif ewoc_season == "winter":
            models = {
                "wintercereals": f"{model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/wintercereals_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json"
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            logger.info(f"[{ewoc_season}] - Using model version: {croptype_model_version}")
            return config


def update_agera5_bucket(filepath: Path) -> None:
    """
    Update stac json files
    :param filepath: Json file path
    :type filepath: Path
    :return: None
    """
    if os.getenv("AGERA5_BUCKET") is None:
        logger.info("Using pod index to update bucket name")
        pod_index = os.getenv("POD_INDEX", 20)
        nb_buckets = os.getenv("NB_BUCKETS", 20)
        b_index = str((int(pod_index) % int(nb_buckets)) + 1)
        # Calculate new agera5 bucket index and replace in bucket name
        ag_bucket = f"s3://ewoc-agera5-{b_index.zfill(2)}/"
    else:
        b_name = os.getenv("AGERA5_BUCKET")
        logger.info(f"Using {b_name} to update bucket name")
        ag_bucket = f"s3://{b_name}/"
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


def check_outfold(outdir: Path) -> bool:
    """
    Check if folder is (really) empty
    :param outdir: Folder to check
    :return: bool
    """
    check = False
    if outdir.exists():
        for root, dirs, files in os.walk(outdir):
            if len(files) > 0:
                check = True
                break
    else:
        logger.info(f"Non existing folder: {outdir}")
    return check


def update_metajsons(root_path: str, out_dir_folder: Path) -> None:
    """
    Update all stac json files in a folder
    :param root_path: Root path in s3 bucket, will be used to replace local folders
    :type root_path: str
    :param out_dir_folder: Folder to scan and update
    :type out_dir_folder: Path
    :return: None
    """
    if root_path.endswith("/"):
        user_id_tmp = root_path.split("/")[-2]
    else:
        user_id_tmp = root_path.split("/")[-1]
    user_id_tmp = user_id_tmp.split("_")[:-2]
    if len(user_id_tmp) == 1:
        user_id = user_id_tmp[0]
    else:
        user_id = "_".join(user_id_tmp)
    # Find all json metadata files
    metajsons = list(out_dir_folder.rglob("*metadata_*.json"))
    if metajsons:
        for meta in metajsons:
            with open(out_dir_folder / meta, "r") as f:
                data = json.load(f)
            # Update links
            for link in data["links"]:
                if link["rel"] == "self":
                    link["href"] = link["href"].replace(str(out_dir_folder), root_path)
            # Update assets
            for asset in data["assets"]:
                prd = data["assets"][asset]
                prd["href"] = prd["href"].replace(str(out_dir_folder), root_path)
            # Update visibility
            if data["properties"]["public"] == "false":
                data["properties"]["public"] = "true"
                logger.info(f"Updated public for {meta} with to true")
            # Update users
            if data["properties"]["users"] == ["0000"]:
                data["properties"]["users"] = [user_id]
                logger.info(f"Updated user id for {meta} with {user_id}")
            # Update user id
            if data["properties"]["tile_collection_id"].split("_")[-1] == "0000":
                tmp_coll_id = (
                    "_".join(data["properties"]["tile_collection_id"].split("_")[:-1])
                    + "_"
                    + user_id
                )
                data["properties"]["tile_collection_id"] = tmp_coll_id
                logger.info(f"Updated tile collection id to {tmp_coll_id}")
            with open(out_dir_folder / meta, "w") as out:
                json.dump(data, out)
            logger.info(f"Updated {meta} with {root_path}")
    else:
        logger.warning("No json file found using **metadata_*.json wildcard")


def update_config(config_dict: Dict, ewoc_detector: str, data_folder: Path) -> Dict:
    """
    Update CopDEM and/or cropland path
    :param config_dict: worldcereal config dictionary
    :param ewoc_detector: cropland of croptype
    :param data_folder: the folder where CopDEM and/or Cropland data is stored
    :return: Dict
    """

    # Update only CopDEM path to local
    old_dem_path = config_dict["inputs"]["DEM"]
    config_dict["inputs"]["DEM"] = old_dem_path.replace(
        "s3://ewoc-aux-data", str(data_folder)
    )
    logger.info(
        f"Updated CopDEM path from {old_dem_path} to {config_dict['inputs']['DEM']}"
    )
    if ewoc_detector == "croptype":
        # Update cropland mask path
        old_crop_path = config_dict["parameters"]["cropland_mask"]
        config_dict["parameters"]["cropland_mask"] = str(
            data_folder / old_crop_path.split("/")[-1]
        )
        logger.info(
            f"Updated CopDEM path from {old_crop_path} to {config_dict['parameters']['cropland_mask']}"
        )
    return config_dict


def paginated_download(bucket: EOBucket, prd_prefix: str, out_dirpath: Path) -> None:
    """
    Download files (recursively) from s3 bucket
    :param bucket: EOBucket
    :type bucket: EOBucket
    :param prd_prefix: Prefix in s3 bucket
    :type prd_prefix: str
    :param out_dirpath: Folder where the files will be written
    :type out_dirpath: Path
    :return: None
    """
    client = bucket._s3_client
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket._bucket_name, Prefix=prd_prefix)
    counter = 0
    for i, page in enumerate(pages):
        page_counter = 0
        logger.info(f"Paginated download: page {i + 1}")
        try:
            for obj in page["Contents"]:
                if not obj["Key"].endswith("/"):
                    filename = obj["Key"].split(
                        sep="/", maxsplit=len(prd_prefix.split("/")) - 1
                    )[-1]
                    output_filepath = out_dirpath / filename
                    (output_filepath.parent).mkdir(parents=True, exist_ok=True)
                    if not output_filepath.exists():
                        bucket._s3_client.download_file(
                            Bucket=bucket._bucket_name,
                            Key=obj["Key"],
                            Filename=str(output_filepath),
                        )
                        counter += 1
                        page_counter += 1
                    else:
                        logger.info(
                            f"{output_filepath} already available, skip downloading!"
                        )
            logger.info(f"Downloaded {page_counter} files from page {i + 1}")
        except Exception:
            logger.error("No files were downloaded, check if the bucket is empty")
            logger.error(traceback.format_exc())
            raise
    if counter == 0:
        logger.error(f"Downloaded a total of {counter} files to {out_dirpath}")
    else:
        logger.info(f"Downloaded a total of {counter} files to {out_dirpath}")


if __name__ == "__main__":
    from pathlib import Path

    from pprint import pprint

    test_dict = {
        "parameters": {
            "year": 2019,
            "season": "annual",
            "featuresettings": "cropland",
            "save_confidence": True,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {"kernelsize": 3, "conf_threshold": 0.85},
        },
        "inputs": {
            "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
            "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
            "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": "/data/worldcereal/s3collections/satio_agera5_yearly.csv",
        },
        "models": {
            "annualcropland": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v502/cropland_detector_WorldCerealPixelCatBoost_v502/config.json"
        },
    }
    test_dict_croptype = {
        "parameters": {
            "year": 2019,
            "season": "summer1",
            "featuresettings": "croptype",
            "save_confidence": True,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {"kernelsize": 7, "conf_threshold": 0.75},
            "active_marker": True,
            "cropland_mask": "s3://world-cereal/EWOC_OUT",
            "irrigation": True,
            "irrparameters": "irrigation",
            "irrmodels": {
                "irrigation": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v420/irrigation_detector_WorldCerealPixelCatBoost_v420/config.json"
            },
        },
        "inputs": {
            "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
            "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
            "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": "/data/worldcereal/s3collections/satio_agera5_yearly.csv",
        },
        "models": {
            "maize": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v502/maize_detector_WorldCerealPixelCatBoost_v502/config.json",
            "springcereals": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v502/springcereals_detector_WorldCerealPixelCatBoost_v502/config.json",
        },
    }
    update_config(test_dict, "cropland", Path("/tmp/data_folder/"))
    config_dict = update_config(
        test_dict_croptype, "croptype", Path("/tmp/data_folder/")
    )
    pprint(config_dict, indent=4)
