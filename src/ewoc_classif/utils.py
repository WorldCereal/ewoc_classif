import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

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


def generate_config_file(featuresettings, end_season_year, ewoc_season, model_version, csv_dict):
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
            "annualcropland": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/cropland_detector_WorldCerealPixelCatBoost/config.json"}
        config = {"parameters": parameters, "inputs": csv_dict, "models": models}
        return config
    elif featuresettings == "croptype":
        logger.info("Updating config file for croptype")
        parameters["filtersettings"] = {"kernelsize": 7, "conf_threshold": 0.75}
        parameters.update({"active_marker": True,
                           "cropland_mask": "s3://world-cereal/EWOC_OUT",
                           "irrigation": True,
                           "irrparameters": "irrigation",
                           "irrmodels":
                               {
                                   "irrigation": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/irrigation_detector_WorldCerealPixelCatBoost/config.json"
                               }
                           })
        if ewoc_season == "summer1":
            models = {
                "maize": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/maize_detector_WorldCerealPixelCatBoost/config.json",
                "springcereals": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/springcereals_detector_WorldCerealPixelCatBoost/config.json",
                "springwheat": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/springwheat_detector_WorldCerealPixelCatBoost/config.json"
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
                "wintercereals": f"https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/{model_version}/wintercereals_detector_WorldCerealPixelCatBoost/config.json"
            }
            config = {"parameters": parameters, "inputs": csv_dict, "models": models}
            return config


if __name__ == "__main__":
    import pprint

    csv_dict = {
        "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
        "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
        "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
        "DEM": "s3://ewoc-aux-data/CopDEM_20m",
        "METEO": "/data/worldcereal/s3collections/satio_agera5.csv"
    }
    cropland_config_ref = {
        "parameters": {
            "year": "2019",
            "season": "annual",
            "featuresettings": "cropland",
            "save_confidence": True,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {
                "kernelsize": 3,
                "conf_threshold": 0.85
            }
        },
        "inputs": {
            "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
            "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
            "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": "/data/worldcereal/s3collections/satio_agera5.csv"
        },
        "models": {
            "annualcropland": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/cropland_detector_WorldCerealPixelCatBoost/config.json"
        }
    }
    summer1_config_ref = {
        "parameters": {
            "year": "2019",
            "season": "summer1",
            "featuresettings": "croptype",
            "save_confidence": True,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {
                "kernelsize": 7,
                "conf_threshold": 0.75
            },
            "active_marker": True,
            "cropland_mask": "s3://world-cereal/EWOC_OUT",
            "irrigation": True,
            "irrparameters": "irrigation",
            "irrmodels": {
                "irrigation": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/irrigation_detector_WorldCerealPixelCatBoost/config.json"
            }
        },
        "inputs": {
            "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
            "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
            "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": "/data/worldcereal/s3collections/satio_agera5.csv"
        },
        "models": {
            "maize": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/maize_detector_WorldCerealPixelCatBoost/config.json",
            "springcereals": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/springcereals_detector_WorldCerealPixelCatBoost/config.json",
            "springwheat": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/springwheat_detector_WorldCerealPixelCatBoost/config.json"
        }
    }
    summer2_config_ref = {
        "parameters": {
            "year": "2019",
            "season": "summer2",
            "featuresettings": "croptype",
            "save_confidence": True,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {
                "kernelsize": 7,
                "conf_threshold": 0.75
            },
            "active_marker": True,
            "cropland_mask": "s3://world-cereal/EWOC_OUT",
            "irrigation": True,
            "irrparameters": "irrigation",
            "irrmodels": {
                "irrigation": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/irrigation_detector_WorldCerealPixelCatBoost/config.json"
            }
        },
        "inputs": {
            "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
            "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
            "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": "/data/worldcereal/s3collections/satio_agera5.csv"
        },
        "models": {
            "maize": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/maize_detector_WorldCerealPixelCatBoost/config.json"
        }
    }
    winter_config_ref = {
        "parameters": {
            "year": "2019",
            "season": "winter",
            "featuresettings": "croptype",
            "save_confidence": True,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {
                "kernelsize": 7,
                "conf_threshold": 0.75
            },
            "active_marker": True,
            "cropland_mask": "s3://world-cereal/EWOC_OUT",
            "irrigation": True,
            "irrparameters": "irrigation",
            "irrmodels": {
                "irrigation": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/irrigation_detector_WorldCerealPixelCatBoost/config.json"
            }
        },
        "inputs": {
            "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
            "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
            "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": "/data/worldcereal/s3collections/satio_agera5.csv"
        },
        "models": {
            "winterwheat": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/winterwheat_detector_WorldCerealPixelCatBoost/config.json",
            "wintercereals": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v200/wintercereals_detector_WorldCerealPixelCatBoost/config.json"
        }
    }

    cropland_ = generate_config_file("cropland", "2019", "annual", "v200", csv_dict)
    summer1_ = generate_config_file("croptype", "2019", "summer1", "v200", csv_dict)
    summer2_ = generate_config_file("croptype", "2019", "summer2", "v200", csv_dict)
    winter_ = generate_config_file("croptype", "2019", "winter", "v200", csv_dict)

    if not cropland_ == cropland_config_ref:
        logger.error("test for cropland failed")
    else:
        logger.info("Cropland OK")
    if not summer1_ == summer1_config_ref:
        logger.error("test for summer1 failed")
    else:
        logger.info("Summer 1 OK")
    if not summer2_ == summer2_config_ref:
        logger.error("test for summer2 failed")
    else:
        logger.info("Summer 2 OK")
    if not winter_ == winter_config_ref:
        logger.error("test for winter failed")
    else:
        logger.info("Winter OK")
