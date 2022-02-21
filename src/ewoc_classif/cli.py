# -*- coding: utf-8 -*-
""" CLI to perform EWoC classification in EWoC processing system
"""
import argparse
from uuid import uuid4
from datetime import datetime
from json import dump
import logging
from pathlib import Path
import sys
from tempfile import gettempdir
from typing import List

from ewoc_dag.bucket.ewoc import EWOCARDBucket, EWOCAuxDataBucket, EWOCPRDBucket
from worldcereal.worldcereal_products import run_tile
from worldcereal import SUPPORTED_SEASONS as EWOC_SUPPORTED_SEASONS

from ewoc_classif import __version__

__author__ = "Mickael Savinaud"
__copyright__ = "Mickael Savinaud"
__license__ = "Unlicense"

_logger = logging.getLogger(__name__)

EWOC_CROPLAND_DETECTOR = 'cropland'
EWOC_CROPTYPE_DETECTOR = 'croptype'
EWOC_CROPTYPE_DETECTORS = ['cereals',
                           'maize',
                           'springcereals',
                           'springwheat',
                           'wheat',
                           'wintercereals',
                           'winterwheat']
EWOC_IRRIGATION_DETECTOR = 'irrigation'

EWOC_DETECTORS = [EWOC_CROPLAND_DETECTOR,
                  EWOC_IRRIGATION_DETECTOR,
                  ].extend(EWOC_CROPTYPE_DETECTORS)

EWOC_MODELS_BASEPATH = 'https://artifactory.vgt.vito.be/auxdata-public/worldcereal/models/'
EWOC_MODELS_TYPE = 'WorldCerealPixelCatBoost'
EWOC_MODELS_VERSION_ID = 'v042'


def ewoc_classif(tile_id: str,
                 block_ids: List[int] = None,
                 sar_csv: Path = None,
                 optical_csv: Path = None,
                 tir_csv: Path = None,
                 agera5_csv: Path = None,
                 ewoc_detector: str = EWOC_CROPLAND_DETECTOR,
                 end_season_year: int = 2019,
                 ewoc_season: str = EWOC_SUPPORTED_SEASONS[3],
                 out_dirpath: Path = Path(gettempdir())) -> None:
    """
    Perform EWoC classification
      :param tile_id: Sentinel-2 MGRS Tile id (ex 31TCJ)
      :param block_ids: Each tile id is divided into blocks, you can specify a list of blocks to process
      :param ewoc_detector: Type of classification applied: cropland, cereals, maize, ...
      :param end_season_year: Season's end year
      :param ewoc_season: Season: winter, summer1, summer2, ...
      :param out_dirpath: Classification output directory, this folder will be uploaded to s3
    """

    production_id = '0000_0_09112021223005' # For 31TCJ
    #production_id = '0000_0_10112021004505'  # For 36MUB, l8_sr case
    # Add some uniqueness to this code
    uid = uuid4().hex[:6]
    uid = tile_id + "_" +uid


    # Create the config file

    # 1/ Create config file

    ewoc_ard_bucket = EWOCARDBucket()
    ewoc_aux_data_bucket = EWOCAuxDataBucket()

    if sar_csv is None:
        sar_csv = str(Path(gettempdir()) / f"{uid}_satio_sar.csv")
        ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath= sar_csv)
    if optical_csv is None:
        optical_csv = str(Path(gettempdir()) / f"{uid}_satio_optical.csv")
        ewoc_ard_bucket.optical_to_satio_csv(tile_id, production_id, filepath=optical_csv)
    if tir_csv is None:
        tir_csv = str(Path(gettempdir()) / f"{uid}_satio_tir.csv")
        ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
    if agera5_csv is None:
        agera5_csv = str(Path(gettempdir()) / f"{uid}_satio_agera5.csv")
        ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)

    if ewoc_detector == EWOC_CROPLAND_DETECTOR:
        featuressettings = EWOC_CROPLAND_DETECTOR
        ewoc_model_key = 'annualcropland'
        ewoc_model_name = f'{EWOC_CROPLAND_DETECTOR}_detector_{EWOC_MODELS_TYPE}'
        ewoc_model_path = f'{EWOC_MODELS_BASEPATH}{EWOC_MODELS_TYPE}/{EWOC_MODELS_VERSION_ID}/{ewoc_model_name}/config.json'
    elif ewoc_detector == EWOC_IRRIGATION_DETECTOR:
        featuressettings = EWOC_IRRIGATION_DETECTOR
    elif ewoc_detector in EWOC_CROPTYPE_DETECTORS:
        featuressettings = EWOC_CROPTYPE_DETECTOR
        ewoc_model_key = ewoc_detector
        ewoc_model_name = f'{ewoc_detector}_detector_{EWOC_MODELS_TYPE}'
        ewoc_model_path = f'{EWOC_MODELS_BASEPATH}{EWOC_MODELS_TYPE}/{EWOC_MODELS_VERSION_ID}/{ewoc_model_name}/config.json'
    else:
        raise ValueError(f'{ewoc_detector} not supported ({EWOC_DETECTORS}')

    ewoc_config = {
        "parameters": {
            "year": end_season_year,
            "season": ewoc_season,
            "featuresettings": featuressettings,
            "save_features": False,
            "localmodels": True,
            "segment": False,
            "filtersettings": {
                "kernelsize": 5,
                "conf_threshold": 0.5
            }
        },
        "inputs": {
            "OPTICAL": optical_csv,
            "SAR": sar_csv,
            "THERMAL": tir_csv,
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": agera5_csv
        },
        "cropland_mask": "s3://world-cereal/EWOC_OUT",
        "models": {
            ewoc_model_key: ewoc_model_path
        }
    }

    ewoc_config_filepath = Path(gettempdir()) / f"{uid}_ewoc_config.json"
    with open(ewoc_config_filepath, 'w', encoding='UTF-8') as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)

    # Process tile (and optionally select blocks)
    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
    _logger.info('Run inference')
    run_tile(tile_id, ewoc_config_filepath, out_dirpath,
             blocks=block_ids)

    # Push the results to the s3 bucket
    ewoc_prd_bucket = EWOCPRDBucket()
    _logger.info('{out_dirpath}')
    ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / 'cogs', production_id)

    # Change the status in the EWoC database

    # Notify the vdm that the product is available


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
        return datetime.strptime(cli_str, "%Y").year()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid year: {cli_str}!") from None


def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="EWoC Classification parser")
    parser.add_argument(
        "--version",
        action="version",
        version=f"ewoc_classif {__version__}",
    )
    parser.add_argument(dest="tile_id", help="MGRS S2 tile id", type=str)
    parser.add_argument('--block-ids', dest="block_ids", help="List of block id to process",
                        nargs='*', type=int)
    parser.add_argument('--optical-csv', dest="optical_csv", help="List of OPTICAL products for a given S2 tile", type=Path, default=None)
    parser.add_argument('--sar-csv', dest="sar_csv", help="List of SAR products for a given S2 tile", default=None, type=Path)
    parser.add_argument('--tir-csv', dest="tir_csv", help="List of TIR products for a given S2 tile", default=None, type=Path)
    parser.add_argument('--agera5-csv', dest="agera5_csv", help="Agera5 list", default=None, type=Path)
    parser.add_argument('--ewoc-detector', dest="ewoc_detector", help="EWoC detector",
                        type=str,
                        choices=EWOC_DETECTORS,
                        default=EWOC_CROPLAND_DETECTOR)
    parser.add_argument('--end-season-year', dest="end_season_year",
                        help="Year to use infer season date - format YYYY",
                        type=valid_year,
                        default=2019)
    parser.add_argument('--ewoc-season', dest="ewoc_season",
                        help="EWoC season",
                        type=str,
                        default="annual",
                        choices=EWOC_SUPPORTED_SEASONS)
    parser.add_argument('-o', '--out-dirpath', dest="out_dirpath", help="Output Dirpath", type=Path,
                        default=gettempdir())
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)


def setup_logging(loglevel: int) -> None:
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    """
    Run EWoC Classification
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    ewoc_classif(args.tile_id,
                 end_season_year=args.end_season_year,
                 ewoc_detector=args.ewoc_detector,
                 ewoc_season=args.ewoc_season,
                 block_ids=args.block_ids,
                 out_dirpath=args.out_dirpath)


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
