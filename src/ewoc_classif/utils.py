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
from datetime import datetime
from distutils.util import strtobool
from pathlib import Path
from typing import Dict

from loguru import logger

import requests

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
    try:
        elem_to_del = list(folder.rglob(f"*{suffix}"))
        for elem in elem_to_del:
            if elem.is_dir():
                shutil.rmtree(elem)
                logger.info(f"Deleted tmp file: {elem}")
            elif elem.is_file():
                elem.unlink()
                logger.info(f"Deleted tmp file: {elem}")
    except:
        logger.warning("Could not delete all tmp files")

def generate_config_file(
    featuresettings: str,
    end_season_year: int,
    ewoc_season: str,
    production_id: str,
    cropland_model_version: str,
    croptype_model_version: str,
    irr_model_version: str,
    csv_dict: Dict,
    feature_blocks_dir: Path,
    no_tir_data: bool,
    use_existing_features: bool,
    add_croptype:bool = False
) -> Dict:
    """
    Automatic generation of worldcereal config files

    The environment variable EWOC_MODELS_DIR_ROOT need to be set to define the local
    path to the models. If not specified, it use artifactory a source

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
    :param feature_blocks_dir: Block features dir
    :type feature_blocks_dir: Path
    :param no_tir: Boolean specifying if the csv file containing details on ARD TIR is empty or not
    :type no_tir: bool
    :param use_existing_features: If true, is going to download existing features, otherwise
    computes it as usual
    :param use_existing_features: bool
    :param add_croptype: Additional croptype
    :type add_croptype: bool
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
        "decision_threshold": 0.7,
        "filtersettings": {"kernelsize": 3, "conf_threshold": 0.85},
    }
    # Support the switch between local models and use of artifactory
    ewoc_model_prefix = os.getenv("EWOC_MODELS_DIR_ROOT",
        "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal")
    logger.info(f"Using model from {ewoc_model_prefix}")

    if featuresettings == "cropland":
        logger.info("Updating config file for cropland")
        parameters["localmodels"]=False
        parameters["save_features"]= True
        parameters["features_dir"]=str(feature_blocks_dir)
        parameters["use_existing_features"]=use_existing_features
        models = {
            "annualcropland": f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{cropland_model_version}/cropland_detector_WorldCerealPixelCatBoost_{cropland_model_version}-realms"
        }

        logger.info(f"[{featuresettings}] - Using model version: {cropland_model_version}")
        config = {"parameters": parameters, "inputs": csv_dict, "models": models}
    elif featuresettings == "croptype":
        is_dev = strtobool(os.getenv("EWOC_DEV_MODE", "False"))
        if is_dev:
            cropland_mask_bucket = f"s3://ewoc-prd-dev/{production_id}"
        else:
            cropland_mask_bucket = f"s3://ewoc-prd/{production_id}"

        logger.info("Updating config file for croptype")
        parameters["filtersettings"] = {"kernelsize": 7, "conf_threshold": 0.75}
        parameters["save_features"]= True
        parameters["features_dir"]=str(feature_blocks_dir)
        parameters["use_existing_features"]=use_existing_features
        if not no_tir_data:
            parameters.update(
                {
                    "active_marker": True,
                    "cropland_mask": cropland_mask_bucket,
                    "irrigation": True,
                    "irrparameters": "irrigation",
                    "irrmodels": {
                        "irrigation": f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{irr_model_version}/irrigation_detector_WorldCerealPixelCatBoost_{irr_model_version}/config.json"
                    },
                }
            )
            logger.info(
                f"[{featuresettings}] - Using Irrigation model version: {irr_model_version}"
            )
        else:
            parameters.update(
                {
                    "active_marker": True,
                    "cropland_mask": cropland_mask_bucket,
                    "irrigation" : False
                }
            )
        if ewoc_season == "summer1":
            models = {
                "maize": f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/maize_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json",
                "springcereals": f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/springcereals_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json",
            }
            if add_croptype:
                models["sunflower"] = f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/sunflower_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json"
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            logger.info(f"[{ewoc_season}] - Using model version: {croptype_model_version}")
        elif ewoc_season == "summer2":
            models = {
                "maize": f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/maize_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json"
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            logger.info(f"[{ewoc_season}] - Using model version: {croptype_model_version}")
        elif ewoc_season == "winter":
            models = {
                "wintercereals": f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/wintercereals_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json"
            }
            if add_croptype:
                models["rapeseed"] = f"{ewoc_model_prefix}/models/WorldCerealPixelCatBoost/{croptype_model_version}/rapeseed_detector_WorldCerealPixelCatBoost_{croptype_model_version}/config.json"

            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            logger.info(f"[{ewoc_season}] - Using model version: {croptype_model_version}")
    else:
        logger.error(f'{featuresettings} not accepeted as value!')
        config={}

    return config

def check_outfold(outdir: Path) -> bool:
    """
    Check if folder is (really) empty
    :param outdir: Folder to check
    :return: bool
    """
    check = False
    if outdir.exists():
        for __unused, __unused_list, files in os.walk(outdir):
            if len(files) > 0:
                check = True
                break
    else:
        logger.info(f"Non existing folder: {outdir}")
    return check


def update_metajsons(root_path: str, out_dir_folder: Path) -> list:
    """
    Update all stac json files in a folder
    :param root_path: Root path in s3 bucket, will be used to replace local folders
    :type root_path: str
    :param out_dir_folder: Folder to scan and update
    :type out_dir_folder: Path
    :return: list of json stac file paths
    """
    if root_path.endswith("/"):
        user_id_tmp = root_path.split("/")[-2]
    else:
        user_id_tmp = root_path.split("/")[-1]
    user_id_tmp2 = user_id_tmp.split("_")[:-2]
    if len(user_id_tmp2) == 1:
        user_id = user_id_tmp2[0]
    else:
        user_id = "_".join(user_id_tmp2)
    # Find all json metadata files
    metajsons = list(out_dir_folder.rglob("*metadata_*.json"))
    if metajsons:
        for meta in metajsons:
            with open(out_dir_folder / meta, "r", encoding='UTF-8') as stac_file:
                data = json.load(stac_file)
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
            with open(out_dir_folder / meta, "w", encoding="UTF-8") as out:
                json.dump(data, out)
            logger.info(f"Updated {meta} with {root_path}")
    else:
        logger.warning("No json file found using **metadata_*.json wildcard")

    return metajsons


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

def ingest_into_vdm(stac_path) -> bool:
    if not os.path.isfile(stac_path):
        logger.error(f'JSON STAC file not found: "{stac_path}"')
        return False

    vdm_host = os.environ.get('VDM_HOST')
    if not vdm_host:
        logger.error('VDM host required ; environment variable "VDM_HOST" not set')
        return False
    vdm_endpoint = f'http://{vdm_host}/rest/project/worldCereal/product'

    vdm_auth = os.environ.get('VDM_USERINFO')
    if not vdm_auth:
        logger.error('VDM user info missing ; environment variable "VDM_USERINFO" not set')
        return False
    headers = {'x-userinfo': vdm_auth}

    with open(stac_path, 'r', encoding='UTF-8') as fh:
        try:
            payload = json.load(fh)
            # 5 sec connection timeout, 10 sec timeout to receive data
            resp = requests.post(vdm_endpoint, headers=headers, json=payload, timeout=(5, 15))
            resp.raise_for_status()
            print('VDM-Ingestion Response code:', resp.status_code)
            return resp.status_code == 200
        except requests.ConnectTimeout:
            logger.error(f'VDM Connection timeout for endpoint {vdm_endpoint}')
            return False
        except requests.ReadTimeout:
            logger.error(f'VDM Read timeout (no data received) from endpoint {vdm_endpoint}')
            return False
        except Exception as x:
            logger.error(f'VDM ingestion failed (status code: {resp.status_code}): {x}')
            return False


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
