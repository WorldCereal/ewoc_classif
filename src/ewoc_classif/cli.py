"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
``[options.entry_points]`` section in ``setup.cfg``::

    console_scripts =
         fibonacci = ewoc_classif.skeleton:run

Then run ``pip install .`` (or ``pip install -e .`` for editable mode)
which will install the command ``fibonacci`` inside your current environment.

Besides console scripts, the header (i.e. until ``_logger``...) of this file can
also be used as template for Python modules.

Note:
    This skeleton file can be safely removed if not needed!

References:
    - https://setuptools.readthedocs.io/en/latest/userguide/entry_point.html
    - https://pip.pypa.io/en/stable/reference/pip_install
"""

import argparse
from json import dump
import logging
from pathlib import Path
import sys
from tempfile import gettempdir
from typing import List


from ewoc_dag.bucket.ewoc import EWOCARDBucket, EWOCAuxDataBucket, EWOCPRDBucket
from worldcereal.worldcereal_products import run_tile


from ewoc_classif import __version__


__author__ = "Mickael Savinaud"
__copyright__ = "Mickael Savinaud"
__license__ = "Unlicense"

_logger = logging.getLogger(__name__)


# ---- Python API ----
# The functions defined in this section can be imported by users in their
# Python scripts/interactive interpreter, e.g. via
# `from ewoc_classif.skeleton import fib`,
# when using this Python module as a library.


def ewoc_classif(tile_id:str,
                 block_ids:List[int]=None,
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

    season_year= 2019
    season_period= 'annual'
    season_type = "cropland"


    ewoc_config ={
	"parameters": {
		"year": season_year,
		"season": season_period,
		"featuresettings": season_type,
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

    ewoc_config_filepath= Path(gettempdir())/'ewoc_onfig.json'
    with open(ewoc_config_filepath, 'w',encoding='UTF-8') as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)


    # Process tile (and optionally select blocks)
    _logger.info('Run inteference')
    run_tile(tile_id, ewoc_config_filepath, out_dirpath,
                  blocks=block_ids)

    # Push the results to the s3 bucket
    ewoc_prd_bucket = EWOCPRDBucket()
    ewoc_prd_bucket.upload_ewoc_prd(out_dirpath/'cogs', f'{production_id}')

    # Change the status in the EWoC database

    # Notify the vdm that the product is available

# ---- CLI ----
# The functions defined in this section are wrappers around the main Python
# API allowing them to be called directly from the terminal as a CLI
# executable/script.


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
    parser.add_argument('--aez_id', dest="aez_id", help="AEZ ID", type=Path)
    parser.add_argument('--block-ids', dest="block_ids", help="List of block id to process",
                        nargs='*', type=int)
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


def setup_logging(loglevel):
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
    ewoc_classif(args.tile_id, block_ids=args.block_ids, out_dirpath=args.out_dirpath)


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
