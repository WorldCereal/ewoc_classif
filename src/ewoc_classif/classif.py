import logging
from loguru import logger
from json import dump
from pathlib import Path
from tempfile import gettempdir
from typing import List
from uuid import uuid4

from ewoc_dag.bucket.ewoc import (EWOCARDBucket, EWOCAuxDataBucket,
                                  EWOCPRDBucket)
from worldcereal import SUPPORTED_SEASONS as EWOC_SUPPORTED_SEASONS
from worldcereal.worldcereal_products import run_tile

from ewoc_classif.utils import remove_tmp_files, generate_config_file

EWOC_CROPLAND_DETECTOR = "cropland"
EWOC_CROPTYPE_DETECTOR = "croptype"
EWOC_CROPTYPE_DETECTORS = [
    "cereals",
    "maize",
    "springcereals",
    "springwheat",
    "wheat",
    "wintercereals",
    "winterwheat",
]
EWOC_IRRIGATION_DETECTOR = "irrigation"

EWOC_DETECTORS = [
    EWOC_CROPLAND_DETECTOR,
    EWOC_IRRIGATION_DETECTOR,
].extend(EWOC_CROPTYPE_DETECTORS)

EWOC_MODELS_BASEPATH = (
    "https://artifactory.vgt.vito.be/auxdata-public/worldcereal/models/"
)
EWOC_MODELS_TYPE = "WorldCerealPixelCatBoost"


def run_classif(
        tile_id: str,
        production_id: str,
        block_ids: List[int] = None,
        sar_csv: Path = None,
        optical_csv: Path = None,
        tir_csv: Path = None,
        agera5_csv: Path = None,
        ewoc_detector: str = EWOC_CROPLAND_DETECTOR,
        end_season_year: int = 2019,
        ewoc_season: str = EWOC_SUPPORTED_SEASONS[3],
        model_version: str = "v200",
        out_dirpath: Path = Path(gettempdir()),
) -> None:
    """
    Perform EWoC classification
      :param tile_id: Sentinel-2 MGRS Tile id (ex 31TCJ)
      :param block_ids: Each tile id is divided into blocks, you can specify a list of blocks to process
      :param ewoc_detector: Type of classification applied: cropland, cereals, maize, ...
      :param end_season_year: Season's end year
      :param ewoc_season: Season: winter, summer1, summer2, ...
      :param out_dirpath: Classification output directory, this folder will be uploaded to s3
    """

    uid = uuid4().hex[:6]
    uid = tile_id + "_" + uid

    # Create the config file

    # 1/ Create config file

    ewoc_ard_bucket = EWOCARDBucket()
    ewoc_aux_data_bucket = EWOCAuxDataBucket()

    if sar_csv is None:
        sar_csv = str(Path(gettempdir()) / f"{uid}_satio_sar.csv")
        ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath=sar_csv)
    if optical_csv is None:
        optical_csv = str(Path(gettempdir()) / f"{uid}_satio_optical.csv")
        ewoc_ard_bucket.optical_to_satio_csv(
            tile_id, production_id, filepath=optical_csv
        )
    if tir_csv is None:
        tir_csv = str(Path(gettempdir()) / f"{uid}_satio_tir.csv")
        ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
    if agera5_csv is None:
        agera5_csv = str(Path(gettempdir()) / f"{uid}_satio_agera5.csv")
        ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)

    csv_dict = {
        "OPTICAL": str(optical_csv),
        "SAR": str(sar_csv),
        "TIR": str(tir_csv),
        "DEM": "s3://ewoc-aux-data/CopDEM_20m",
        "METEO": str(agera5_csv),
    }
    ewoc_config = generate_config_file(ewoc_detector, end_season_year, ewoc_season, model_version, csv_dict)
    ewoc_config_filepath = Path(gettempdir()) / f"{uid}_ewoc_config.json"
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)

    # Process tile (and optionally select blocks)
    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
    logger.info("Run inference")
    total_ids = 483
    if block_ids is not None:
        logger.info(f'Processing custom ids from CLI {"-".join(block_ids)}')
        ids_range = block_ids
    else:
        logger.info(f'Processing {total_ids} blocks')
        ids_range = range(total_ids + 1)
    for block_id in ids_range:
        try:
            logger.info(f"[{block_id}/{total_ids}] Start processing")
            run_tile(tile_id, ewoc_config_filepath, out_dirpath, blocks=[block_id], postprocess=False, process=True)
        except:
            logger.error(f"failed for block {block_id}")
    logger.info("Start cog mosaic")
    run_tile(tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False)
    # Push the results to the s3 bucket
    ewoc_prd_bucket = EWOCPRDBucket()
    logger.info(f"{out_dirpath}")
    nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "cogs", production_id)
    # Add Upload print
    print(f"Uploaded {nb_prd} files to bucket | {up_dir}")
    # Remove temporary files created by the classifier in cwd
    remove_tmp_files(Path.cwd(), f"{tile_id}.tif")
    remove_tmp_files(Path.cwd(), "features.zarr")

    # Change the status in the EWoC database

    # Notify the vdm that the product is available
