
# -*- coding: utf-8 -*-
""" CLI to perform EWoC classification in EWoC processing system
"""
import argparse
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

EWOC_BASE_MODELS_ADRESS = 'https://artifactory.vgt.vito.be/auxdata-public/worldcereal/models/'

# ---- Python API ----
# The functions defined in this section can be imported by users in their
# Python scripts/interactive interpreter, e.g. via
# `from ewoc_classif.cli import ewoc_classif`,
# when using this Python module as a library.


def ewoc_classif(tile_id:str,
                 block_ids:List[int]=None,
                 ewoc_detector:str=EWOC_CROPLAND_DETECTOR,
                 end_season_year:int=2019,
                 ewoc_season:str=EWOC_SUPPORTED_SEASONS[3],
                 aez_id:int = None,
                 out_dirpath:Path=Path(gettempdir()))->None:
    """Perform EWoC classification

    Args:
      n (int): integer

    """

    production_id = '0000_0_09112021223005'


    # Create the config file

    # 1/ Create config file

    ewoc_ard_bucket = EWOCARDBucket()

    ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id)
    ewoc_ard_bucket.optical_to_satio_csv(tile_id,production_id)
    ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id)

    ewoc_aux_data_bucket = EWOCAuxDataBucket()
    ewoc_aux_data_bucket.agera5_to_satio_csv()

    if ewoc_detector == EWOC_CROPLAND_DETECTOR:
        featuressettings=EWOC_CROPLAND_DETECTOR
    elif ewoc_detector == EWOC_IRRIGATION_DETECTOR:
        featuressettings = EWOC_IRRIGATION_DETECTOR
    elif ewoc_detector in EWOC_CROPTYPE_DETECTORS:
        featuressettings = EWOC_CROPTYPE_DETECTOR
    else:
        raise ValueError(f'{ewoc_detector} not supported ({EWOC_DETECTORS}')

    ewoc_config ={
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
		"OPTICAL": str(Path(gettempdir()) / "satio_optical.csv"),
		"SAR": str(Path(gettempdir()) / "satio_sar.csv"),
		"THERMAL": str(Path(gettempdir()) / "satio_tir.csv"),
		"DEM": "s3://ewoc-aux-data/CopDEM_20m",
		"METEO": str(Path(gettempdir()) / "satio_agera5.csv")
	},
	"cropland_mask": "s3://world-cereal/EWOC_OUT",
	"models": {
		"annualcropland": "https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost/v042/cropland_detector_WorldCerealPixelCatBoost/config.json"
	    }
    }

    ewoc_config_filepath= Path(gettempdir())/'ewoc_config.json'
    with open(ewoc_config_filepath, 'w',encoding='UTF-8') as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)


    # Process tile (and optionally select blocks)
    _logger.info('Run inference')
    # TODO: how to override the aez_id detected from the wc function get_matching_aez_id
    run_tile(tile_id, ewoc_config_filepath, out_dirpath,
                  blocks=block_ids)

    # Push the results to the s3 bucket
    ewoc_prd_bucket = EWOCPRDBucket()
    _logger.info('{out_dirpath}')
    ewoc_prd_bucket.upload_ewoc_prd(out_dirpath/'cogs', f'{production_id}')

    # Change the status in the EWoC database

    # Notify the vdm that the product is available

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.

def valid_year(cli_str:str)->int:
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
    parser = argparse.ArgumentParser(description="Just a Fibonacci demonstration")
    parser.add_argument(
        "--version",
        action="version",
        version=f"ewoc_classif {__version__}",
    )
    parser.add_argument(dest="tile_id", help="MGRS S2 tile id", type=str)
    parser.add_argument('-o','--out-dirpath', dest="out_dirpath", help="Output Dirpath", type=Path,
                        default=gettempdir())
    parser.add_argument('--aez-id', dest="aez_id", help="EWoC AEZ ID", type=str)
    parser.add_argument('--block-ids', dest="block_ids", help="List of block id to process",
                        nargs='*', type=int)
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


def setup_logging(loglevel:int)->None:
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    """Wrapper allowing :func:`fib` to be called with string arguments in a CLI fashion

    Instead of returning the value from :func:`fib`, it prints the result to the
    ``stdout`` in a nicely formatted message.

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--verbose", "42"]``).
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    ewoc_classif(args.tile_id,
                 end_season_year=args.end_season_year,
                 ewoc_detector=args.ewoc_detector,
                 ewoc_season=args.ewoc_season,
                 block_ids=args.block_ids,
                 aez_id=args.aez_id,
                 out_dirpath=args.out_dirpath)


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m ewoc_classif.skeleton 42
    #
    run()
