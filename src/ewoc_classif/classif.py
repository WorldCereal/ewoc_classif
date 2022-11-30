# -*- coding: utf-8 -*-
"""
Classification and postprocessing tools
"""
import os
import shutil
import traceback
from json import dump, load
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, List
from uuid import uuid4

from ewoc_dag.ewoc_dag import get_blocks
from ewoc_dag.bucket.ewoc import EWOCARDBucket, EWOCAuxDataBucket, EWOCPRDBucket
from loguru import logger
from worldcereal import SUPPORTED_SEASONS as EWOC_SUPPORTED_SEASONS
from worldcereal.worldcereal_products import run_tile

from ewoc_classif.utils import (
    check_outfold,
    generate_config_file,
    ingest_into_vdm,
    remove_tmp_files,
    update_agera5_bucket,
    update_config,
    update_metajsons,
)

EWOC_CROPLAND_DETECTOR = "cropland"
EWOC_CROPTYPE_DETECTOR = "croptype"

EWOC_DETECTORS = [
    EWOC_CROPLAND_DETECTOR,
    EWOC_CROPTYPE_DETECTOR,]

EWOC_MODELS_BASEPATH = (
    "https://artifactory.vgt.vito.be/auxdata-public/worldcereal/models/"
)
EWOC_MODELS_TYPE = "WorldCerealPixelCatBoost"


def process_blocks(
    tile_id: str,
    ewoc_config_filepath: Path,
    block_ids: Optional[List[int]],
    production_id: str,
    upload_block: bool,
    out_dirpath: Path,
) -> None:
    """
    Process a single block, cropland/croptype prediction
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param ewoc_config_filepath: Path to the config file generated previously
    :type ewoc_config_filepath: Path
    :param block_ids: List of block ids to process (blocks= equal area subdivisions of a tile)
    :type block_ids: List[int]
    :param production_id: EWoC production id
    :type production_id: str
    :param upload_block: True if you want to upload each block and skip the mosaic. If False, multiple blocks can be
     processed and merged into a mosaic within the same process (or command)
    :type upload_block: bool
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :return: None
    """
    logger.info("Run inference")

    if block_ids is not None:
        logger.info(f"Processing custom ids from CLI {block_ids}")
        ids_range = block_ids
    else:
        if str(os.getenv("EWOC_BLOCKSIZE", "512")) == "512":
            total_ids = 483
        elif str(os.getenv("EWOC_BLOCKSIZE", "512")) == "1024":
            total_ids = 120
        logger.info(f"Processing {total_ids} blocks")
        ids_range = range(total_ids + 1)

    with open(ewoc_config_filepath) as json_file:
        data = load(json_file)
        blocks_feature_dir = Path(data["parameters"]["features_dir"])

    for block_id in ids_range:
        try:
            logger.info(f"[{block_id}] Start processing")
            out_dirpath.mkdir(exist_ok=True)
            ret = run_tile(
                tile_id,
                ewoc_config_filepath,
                out_dirpath,
                blocks=[int(block_id)],
                postprocess=False,
                process=True,
            )
            if ret == 0:
                logger.info(f"Block finished with code {ret}")
                ewoc_prd_bucket = EWOCPRDBucket()
                if os.getenv("PRD_BUCKET") is not None:
                    ewoc_prd_bucket._bucket_name = os.getenv("PRD_BUCKET")
                    logger.info(f"Output bucket set to: {ewoc_prd_bucket._bucket_name}")
                logger.info(f"Pushing block id {block_id} to S3")
                nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
                    out_dirpath / "blocks", production_id + "/blocks"
                )
                ewoc_prd_bucket.upload_ewoc_prd(
                    out_dirpath / "exitlogs", production_id + "/exitlogs"
                )
                ewoc_prd_bucket.upload_ewoc_prd(
                    out_dirpath / "proclogs", production_id + "/proclogs"
                )
                if any(blocks_feature_dir.iterdir()):
                    ewoc_prd_bucket.upload_ewoc_prd(
                        blocks_feature_dir, production_id + "/block_features"
                    )
                shutil.rmtree(out_dirpath / "blocks")
                # Add Upload print
                print(f"Uploaded {nb_prd} files to bucket | {up_dir}")
            elif ret == 1:
                logger.info(f"Skipped block, return code: {ret}")
                shutil.rmtree(out_dirpath / "blocks", ignore_errors=True)
                # Add Upload print
                print(f"Uploaded {0} files to bucket | placeholder")
        except Exception:
            logger.error(f"failed for block {block_id}")
            logger.error(traceback.format_exc())

    if not upload_block:
        logger.info("Start cog mosaic")
        run_tile(
            tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False
        )
        # Push the results to the s3 bucket
        ewoc_prd_bucket = EWOCPRDBucket()
        if os.getenv("PRD_BUCKET") is not None:
            ewoc_prd_bucket._bucket_name = os.getenv("PRD_BUCKET")
            logger.info(f"Output bucket set to: {ewoc_prd_bucket._bucket_name}")
        nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
            out_dirpath / "cogs", production_id
        )
        ewoc_prd_bucket.upload_ewoc_prd(
            out_dirpath / "exitlogs", production_id + "/exitlogs"
        )
        ewoc_prd_bucket.upload_ewoc_prd(
            out_dirpath / "proclogs", production_id + "/proclogs"
        )
        # Add Upload print
        print(f"Uploaded {nb_prd} files to bucket | {up_dir}")


def postprocess_mosaic(
    tile_id: str, production_id: str, ewoc_config_filepath: Path, out_dirpath: Path
) -> None:
    """
    Postprocessing (mosaic)
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param production_id: EWoC production id
    :type production_id: str
    :param ewoc_config_filepath: Path to the config file generated previously
    :type ewoc_config_filepath: Path
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :return: None
    """
    # Retrieve some parameters from config file
    with open(ewoc_config_filepath, "r") as f:
        data = load(f)
    year = data["parameters"]["year"]
    season = data["parameters"]["season"]

    # Retrieve blocks data from EWoC products bucket
    logger.info(f"Getting blocks from EWoC products bucket on {os.getenv('EWOC_CLOUD_PROVIDER')}")
    get_blocks(production_id, tile_id, season, year, out_dirpath)

    # Mosaic
    # Setup symlink for gdal translate
    if not os.path.islink("/opt/ewoc_classif_venv/bin/gdal_translate"):
        os.symlink(
            "/usr/bin/gdal_translate", "/opt/ewoc_classif_venv/bin/gdal_translate"
        )
        logger.info(
            f"Symbolic link created {'/usr/bin/gdal_translate'} -> {'/opt/ewoc_classif_venv/bin/gdal_translate'}"
        )
    # Use VITO code to perform mosaic
    run_tile(
        tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False
    )

    # Upload data to EWoC product bucket
    logger.info("Start upload")
    if check_outfold(out_dirpath / f"cogs/{tile_id}/{year}_{season}"):
        # Update json stac
        root_s3 = f"s3://ewoc-prd/{production_id}"
        stac_paths = update_metajsons(root_s3, out_dirpath / "cogs")
        # Push the results to the s3 bucket
        ewoc_prd_bucket = EWOCPRDBucket()
        if os.getenv("PRD_BUCKET") is not None:
            ewoc_prd_bucket._bucket_name = os.getenv("PRD_BUCKET")
            logger.info(f"Output bucket set to: {ewoc_prd_bucket._bucket_name}")
        nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
            out_dirpath / "cogs", production_id
        )
        logger.info(f"Uploaded {out_dirpath}/cogs to {production_id} ")
        # Add Upload print
        print(f"Uploaded {nb_prd} files to bucket | {up_dir}")

        # Starting ingestion of products in the VDM
        if stac_paths:
            logger.info("Notifying the VDM of new products to ingest")
            for stac in stac_paths:
                if not ingest_into_vdm(stac):
                    logger.error(f'VDM ingestion error for tile: "{tile_id}" ({year}, {season})')
        else:
            logger.warning('No STAC files were found to start ingestion')
    else:
        raise Exception("Upload folder must be empty, the mosaic failed")


def run_classif(
    tile_id: str,
    production_id: str,
    block_ids: Optional[List[int]] = None,
    sar_csv: Optional[Path] = None,
    optical_csv: Optional[Path] = None,
    tir_csv: Optional[Path] = None,
    agera5_csv: Optional[Path] = None,
    data_folder: Optional[Path] = None,
    ewoc_detector: str = EWOC_CROPLAND_DETECTOR,
    end_season_year: int = 2019,
    ewoc_season: str = EWOC_SUPPORTED_SEASONS[3],
    cropland_model_version: str = "v605",
    croptype_model_version: str = "v502",
    irr_model_version: str = "v420",
    upload_block: bool = True,
    postprocess: bool = False,
    out_dirpath: Path = Path(gettempdir()),
) -> None:
    """
    Perform EWoC classification
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param production_id: EWoC production id
    :type production_id: str
    :param block_ids: List of block ids to process (blocks= equal area subdivisions of a tile)
    :type block_ids: List[int]
    :param sar_csv: Path to a csv file with all the detail about all the Sentinel-1 images to process
    :type sar_csv: Path
    :param optical_csv: Path to a csv file with all the detail about all the Sentinel-2/ Landsat 8 images to process
    :type optical_csv: Path
    :param tir_csv: Path to a csv file with all the detail about all the Landsat 8 TIR images to process
    :type tir_csv: Path
    :param agera5_csv: Path to a csv file with all the detail about all the AgERA5 images to process
    :type agera5_csv: Path
    :param data_folder: Folder with CopDEM and/or cropland data
    :type data_folder: Path
    :param ewoc_detector: Type of detector to use, possible choices are cropland or croptype
    :type ewoc_detector: str
    :param end_season_year: End of season year
    :type end_season_year: int
    :param ewoc_season: Which season are we processing, possible options: annual, summer1, summer2 and winter
    :type ewoc_season: str
    :param cropland_model_version: The version of the AI model used for the cropland prediction
    :type cropland_model_version: str
    :param croptype_model_version: The version of the AI model used for the croptype prediction
    :type croptype_model_version: str
    :param irr_model_version: The version of the AI model used for croptype irrigation
    :type irr_model_version: str
    :param upload_block: True if you want to upload each block and skip the mosaic. If False, multiple blocks can be
     processed and merged into a mosaic within the same process (or command)
    :type upload_block: bool
    :param postprocess: If True only the postprocessing (aka mosaic) will be performed, default to False
    :type postprocess: bool
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :return: None
    """
    uid = uuid4().hex[:6]
    uid = tile_id + "_" + uid
    agera5_bucket = os.getenv("AGERA5_BUCKET", "ewoc-aux-data")
    # Create the config file
    ewoc_ard_bucket = EWOCARDBucket()

    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
        out_dirpath.mkdir()
    feature_blocks_dir = out_dirpath / "block_features"
    feature_blocks_dir.mkdir(parents=True,exist_ok=True)
    if sar_csv is None:
        sar_csv = out_dirpath / f"{uid}_satio_sar.csv"
        ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath=sar_csv)
    if optical_csv is None:
        optical_csv = out_dirpath / f"{uid}_satio_optical.csv"
        ewoc_ard_bucket.optical_to_satio_csv(
            tile_id, production_id, filepath=optical_csv
        )
    if tir_csv is None:
        tir_csv = out_dirpath / f"{uid}_satio_tir.csv"
        ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
    if agera5_csv is None:
        agera5_csv = out_dirpath / f"{uid}_satio_agera5.csv"
        ewoc_aux_data_bucket = EWOCAuxDataBucket()
        ewoc_aux_data_bucket._bucket_name = agera5_bucket
        logger.info(f"Using bucket {agera5_bucket}")
        ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)
        update_agera5_bucket(agera5_csv)

    csv_dict = {
        "OPTICAL": str(optical_csv),
        "SAR": str(sar_csv),
        "TIR": str(tir_csv),
        "DEM": "s3://ewoc-aux-data/CopDEM_20m",
        "METEO": str(agera5_csv),
    }
    ewoc_config = generate_config_file(
        ewoc_detector,
        str(end_season_year),
        ewoc_season,
        production_id,
        cropland_model_version,
        croptype_model_version,
        irr_model_version,
        csv_dict,
        feature_blocks_dir= feature_blocks_dir
    )
    ewoc_config_filepath = out_dirpath / f"{uid}_ewoc_config.json"
    if data_folder is not None:
        ewoc_config = update_config(ewoc_config, ewoc_detector, data_folder)
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)
    # Process tile (and optionally select blocks)
    try:
        if not postprocess:
            process_blocks(
                tile_id,
                ewoc_config_filepath,
                block_ids,
                production_id,
                upload_block,
                out_dirpath,
            )
        else:
            postprocess_mosaic(
                tile_id, production_id, ewoc_config_filepath, out_dirpath
            )
    except Exception:
        logger.error("Processing failed")
        logger.error(traceback.format_exc())
    finally:
        logger.info(f"Cleaning the output folder {out_dirpath}")
        shutil.rmtree(out_dirpath)
        remove_tmp_files(Path.cwd(), f"{tile_id}.tif")


if __name__ == "__main__":

    import logging
    import sys

    LOG_FORMAT = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


    out_dirpath=Path(gettempdir())
    tile_id= '50QLL'
    sar_csv=None
    optical_csv=None
    tir_csv=None
    agera5_csv=None
    production_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_26178_20221025141020'
    ewoc_detector= EWOC_CROPLAND_DETECTOR
    end_season_year = 2021
    cropland_model_version = 'v700'
    croptype_model_version = 'toto'
    irr_model_version = 'toto'
    ewoc_season='annual'
    data_folder=Path('/tmp')

    uid = uuid4().hex[:6]
    uid = tile_id + "_" + uid
    agera5_bucket = os.getenv("AGERA5_BUCKET", "ewoc-aux-data")
    # Create the config file
    ewoc_ard_bucket = EWOCARDBucket()

    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
        out_dirpath.mkdir()
    feature_blocks_dir = out_dirpath / "block_features"
    feature_blocks_dir.mkdir(parents=True,exist_ok=True)
    if sar_csv is None:
        sar_csv = str(out_dirpath / f"{uid}_satio_sar.csv")
        ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath=sar_csv)
    if optical_csv is None:
        optical_csv = str(out_dirpath / f"{uid}_satio_optical.csv")
        ewoc_ard_bucket.optical_to_satio_csv(
            tile_id, production_id, filepath=optical_csv
        )
    if tir_csv is None:
        tir_csv = str(out_dirpath / f"{uid}_satio_tir.csv")
        ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
    if agera5_csv is None:
        agera5_csv = out_dirpath / f"{uid}_satio_agera5.csv"
        ewoc_aux_data_bucket = EWOCAuxDataBucket()
        ewoc_aux_data_bucket._bucket_name = agera5_bucket
        logger.info(f"Using bucket {agera5_bucket}")
        ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)
        update_agera5_bucket(agera5_csv)

    csv_dict = {
        "OPTICAL": str(optical_csv),
        "SAR": str(sar_csv),
        "TIR": str(tir_csv),
        "DEM": "s3://ewoc-aux-data/CopDEM_20m",
        "METEO": str(agera5_csv),
    }
    ewoc_config = generate_config_file(
        ewoc_detector,
        str(end_season_year),
        ewoc_season,
        production_id,
        cropland_model_version,
        croptype_model_version,
        irr_model_version,
        csv_dict,
        feature_blocks_dir= feature_blocks_dir
    )
    ewoc_config_filepath = out_dirpath / f"{uid}_ewoc_config.json"
    if data_folder is not None:
        ewoc_config = update_config(ewoc_config, ewoc_detector, data_folder)
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)

    postprocess_mosaic(tile_id,production_id,ewoc_config_filepath, out_dirpath)