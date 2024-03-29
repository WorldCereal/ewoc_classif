# -*- coding: utf-8 -*-
""" CLI to perform EWoC classification in EWoC processing system
"""
import argparse
import logging
import sys
from pathlib import Path
from tempfile import gettempdir

from worldcereal import SUPPORTED_SEASONS as EWOC_SUPPORTED_SEASONS

from ewoc_classif import __version__
from ewoc_classif.classif import EWOC_CROPLAND_DETECTOR, EWOC_DETECTORS, generate_ewoc_block
from ewoc_classif.ewoc_model import (EWOC_CT_MODEL_VERSION,
                                     EWOC_CL_MODEL_VERSION,
                                     EWOC_IRR_MODEL_VERSION)
from ewoc_classif.utils import setup_logging, valid_year

__author__ = "Mickael Savinaud"
__copyright__ = "Mickael Savinaud"
__license__ = "Unlicense"

_logger = logging.getLogger(__name__)


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
        version=f"ewoc_generate_block {__version__}",
    )
    parser.add_argument(dest="tile_id", help="MGRS S2 tile id", type=str)
    parser.add_argument(dest="block_id", help="Block id to process", type=int)
    parser.add_argument(dest="production_id", help="EWoC production id", type=str)
    parser.add_argument(
        "--optical-csv",
        dest="optical_csv",
        help="List of OPTICAL products for a given S2 tile",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--sar-csv",
        dest="sar_csv",
        help="List of SAR products for a given S2 tile",
        default=None,
        type=Path,
    )
    parser.add_argument(
        "--tir-csv",
        dest="tir_csv",
        help="List of TIR products for a given S2 tile",
        default=None,
        type=Path,
    )
    parser.add_argument(
        "--agera5-csv", dest="agera5_csv", help="Agera5 list", default=None, type=Path
    )
    parser.add_argument(
        "--data-folder",
        dest="data_folder",
        help="Folder storing CopDEM and Cropland data",
        default=None,
        type=Path,
    )
    parser.add_argument(
        "--ewoc-detector",
        dest="ewoc_detector",
        help="EWoC detector",
        choices=EWOC_DETECTORS,
        default=EWOC_CROPLAND_DETECTOR,
    )
    parser.add_argument(
        "--end-season-year",
        dest="end_season_year",
        help="Year to use infer season date - format YYYY",
        type=valid_year,
        default=2021,
    )
    parser.add_argument(
        "--ewoc-season",
        dest="ewoc_season",
        help="EWoC season",
        type=str,
        default="annual",
        choices=EWOC_SUPPORTED_SEASONS,
    )
    parser.add_argument(
        "--cropland-model-version",
        dest="cropland_model_version",
        help="Cropland model version",
        type=str,
        default=EWOC_CL_MODEL_VERSION,
    )
    parser.add_argument(
        "--croptype-model-version",
        dest="croptype_model_version",
        help="Croptype model version",
        type=str,
        default=EWOC_CT_MODEL_VERSION,
    )
    parser.add_argument(
        "--irr-model-version",
        dest="irr_model_version",
        help="Irrigation model version",
        type=str,
        default=EWOC_IRR_MODEL_VERSION,
    )
    parser.add_argument("--no-upload",
        action='store_false',
        help= 'Skip the upload of block files to s3 bucket')

    parser.add_argument("--no-clean",
        action='store_false',
        help= 'Avoid to clean all dirs and files')

    parser.add_argument(
        "-o",
        "--out-dirpath",
        dest="out_dirpath",
        help="Output Dirpath",
        type=Path,
        default=gettempdir(),
    )
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


def main(args):
    """
    Run EWoC Classification
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    # This print is here on purpose!
    print("Start of processing")

    generate_ewoc_block(
        args.tile_id,
        args.production_id,
        args.block_id,
        sar_csv=args.sar_csv,
        optical_csv=args.optical_csv,
        tir_csv=args.tir_csv,
        agera5_csv=args.agera5_csv,
        data_folder=args.data_folder,
        end_season_year=args.end_season_year,
        ewoc_detector=args.ewoc_detector,
        ewoc_season=args.ewoc_season,
        cropland_model_version=args.cropland_model_version,
        croptype_model_version=args.croptype_model_version,
        irr_model_version=args.irr_model_version,
        upload_block=args.no_upload,
        out_dirpath=args.out_dirpath,
    )


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
