import os
import shutil
from json import dump
from pathlib import Path
from tempfile import gettempdir
from typing import List
from uuid import uuid4

from ewoc_dag.bucket.eobucket import EOBucket
from ewoc_dag.bucket.ewoc import (EWOCARDBucket, EWOCAuxDataBucket,
                                  EWOCPRDBucket)
from loguru import logger
from worldcereal import SUPPORTED_SEASONS as EWOC_SUPPORTED_SEASONS
from worldcereal.worldcereal_products import run_tile

from ewoc_classif.utils import generate_config_file, remove_tmp_files, update_agera5_bucket, check_outfold

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


def process_blocks(tile_id, ewoc_config_filepath, block_ids, production_id, upload_block, out_dirpath):
    logger.info("Run inference")

    if block_ids is not None:
        logger.info(f'Processing custom ids from CLI {block_ids}')
        ids_range = block_ids
    else:
        if str(os.getenv("EWOC_BLOCKSIZE","512")) == "512":
            total_ids = 483
        elif str(os.getenv("EWOC_BLOCKSIZE","512")) == "1024":
            total_ids = 120
        logger.info(f'Processing {total_ids} blocks')
        ids_range = range(total_ids + 1)
    for block_id in ids_range:
        try:
            logger.info(f"[{block_id}] Start processing")
            out_dirpath.mkdir(exist_ok=True)
            run_tile(tile_id, ewoc_config_filepath, out_dirpath, blocks=[int(block_id)], postprocess=False,
                     process=True)
            if upload_block:
                if check_outfold(out_dirpath / "blocks"):
                    ewoc_prd_bucket = EWOCPRDBucket()
                    logger.info(f"Push block id {block_id} to S3")
                    nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "blocks",
                                                                              production_id + "/blocks")
                    nb_prd_ex, size_of, up_dir_ex = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "exitlogs", production_id+"/exitlogs")
                    nb_prd_pr, size_of, up_dir_pr = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "proclogs", production_id+"/proclogs")
                    shutil.rmtree(out_dirpath / "blocks")
                    # Add Upload print
                    print(f"Uploaded {nb_prd} files to bucket | {up_dir}")
                else:
                    logger.info("Successful processing with empty upload folder")
                    nb_prd_ex, size_of, up_dir_ex = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "exitlogs", production_id+"/exitlogs")
                    nb_prd_pr, size_of, up_dir_pr = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "proclogs", production_id+"/proclogs")
                    shutil.rmtree(out_dirpath / "blocks")
                    # Add Upload print
                    print(f"Uploaded {0} files to bucket | placeholder")
        except:
            logger.error(f"failed for block {block_id}")
    if not upload_block:
        logger.info("Start cog mosaic")
        run_tile(tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False)
        # Push the results to the s3 bucket
        ewoc_prd_bucket = EWOCPRDBucket()
        nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "cogs", production_id)
        nb_prd_ex, size_of, up_dir_ex = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "exitlogs",
                                                                        production_id + "/exitlogs")
        nb_prd_pr, size_of, up_dir_pr = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "proclogs",
                                                                        production_id + "/proclogs")
        # Add Upload print
        print(f"Uploaded {nb_prd} files to bucket | {up_dir}")



def postprocess_mosaic(tile_id, production_id, ewoc_config_filepath, out_dirpath):
    # Download the blocks from S3
    bucket = EOBucket("ewoc-prd", s3_access_key_id=os.getenv("EWOC_S3_ACCESS_KEY_ID"),
                      s3_secret_access_key=os.getenv("EWOC_S3_SECRET_ACCESS_KEY"),
                      endpoint_url="https://s3.waw2-1.cloudferro.com")
    prd_prefix = f"{production_id}/blocks"
    bucket._download_prd(prd_prefix, out_dirpath)
    logger.info("Blocks download successful")
    # Mosaic
    # Setup symlink for gdal translate
    os.symlink("/usr/bin/gdal_translate","/opt/ewoc_classif_venv/bin/gdal_translate")
    logger.info(f"Symbolic link created {'/usr/bin/gdal_translate'} -> {'/opt/ewoc_classif_venv/bin/gdal_translate'}")
    run_tile(tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False)
    logger.info("Mosaic is done!")
    # Push the results to the s3 bucket
    ewoc_prd_bucket = EWOCPRDBucket()
    nb_prd, size_of, up_dir = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "cogs", production_id)
    logger.info(f"Uploaded {out_dirpath}/cogs to {production_id} ")
    nb_prd_ex, size_of, up_dir_ex = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "exitlogs",
                                                                    production_id + "/exitlogs")
    nb_prd_pr, size_of, up_dir_pr = ewoc_prd_bucket.upload_ewoc_prd(out_dirpath / "proclogs",
                                                                    production_id + "/proclogs")
    # Add Upload print
    print(f"Uploaded {nb_prd} files to bucket | {up_dir}")

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
        model_version: str = "v210",
        upload_block: bool = True,
        postprocess: bool = False,
        out_dirpath: Path = Path(gettempdir()),
) -> None:
    """
    Perform EWoC classification
      :param postprocess:
      :param upload_block:
      :param model_version:
      :param agera5_csv:
      :param tir_csv:
      :param optical_csv:
      :param sar_csv:
      :param production_id:
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
    ewoc_ard_bucket = EWOCARDBucket()
    ewoc_aux_data_bucket = EWOCAuxDataBucket()

    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
        out_dirpath.mkdir()
    if sar_csv is None:
        sar_csv = str(out_dirpath/ f"{uid}_satio_sar.csv")
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
        agera5_csv = str(out_dirpath / f"{uid}_satio_agera5.csv")
        ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)
        update_agera5_bucket(agera5_csv)

    csv_dict = {
        "OPTICAL": str(optical_csv),
        "SAR": str(sar_csv),
        "TIR": str(tir_csv),
        "DEM": "s3://ewoc-aux-data/CopDEM_20m",
        "METEO": str(agera5_csv),
    }
    ewoc_config = generate_config_file(ewoc_detector, end_season_year, ewoc_season,production_id, model_version, csv_dict)
    ewoc_config_filepath = out_dirpath / f"{uid}_ewoc_config.json"
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)

    # Process tile (and optionally select blocks)
    if not postprocess:
        process_blocks(tile_id, ewoc_config_filepath, block_ids, production_id, upload_block, out_dirpath)
    else:
        logger.info('Postprocess: only mosaic')
        try:
            postprocess_mosaic(tile_id, production_id, ewoc_config_filepath, out_dirpath)
        except:
            logger.error("Postprocess failed")
    logger.info(f"Cleaning the output folder {out_dirpath}")
    shutil.rmtree(out_dirpath)
    remove_tmp_files(Path.cwd(), f"{tile_id}.tif")