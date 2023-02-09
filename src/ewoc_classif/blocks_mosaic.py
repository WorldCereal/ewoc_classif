# -*- coding: utf-8 -*-
"""
Blocks mosaic module
"""
import os
import shutil
import traceback
import csv
from json import dump, load
from pathlib import Path
from tempfile import gettempdir
from typing import Optional
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
    update_config,
    update_metajsons,
)

EWOC_CROPLAND_DETECTOR = "cropland"
EWOC_CROPTYPE_DETECTOR = "croptype"

EWOC_DETECTORS = [
    EWOC_CROPLAND_DETECTOR,
    EWOC_CROPTYPE_DETECTOR,]

def blocks_mosaic(
    tile_id: str,
    production_id: str,
    ewoc_config_filepath: Path,
    out_dirpath: Path,
    aez_id: int
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
    :param aez_id : If provided, the AEZ ID will be enforced instead of
    automatically derived from the Sentinel-2 tile ID.
    :type aez_id: int
    :return: None
    """
    # Retrieve some parameters from config file
    with open(ewoc_config_filepath, "r", encoding='UTF-8') as config_file:
        data = load(config_file)
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
        tile_id,
        ewoc_config_filepath,
        out_dirpath,
        postprocess=True,
        process=False,
        aez_id=aez_id
    )

    # Upload data to EWoC product bucket
    logger.info("Start upload")
    if check_outfold(out_dirpath / f"cogs/{tile_id}/{year}_{season}"):
        # Update json stac
        root_s3 = f"s3://ewoc-prd/{production_id}"
        stac_paths = update_metajsons(root_s3, out_dirpath / "cogs")
        # Push the results to the s3 bucket
        ewoc_prd_bucket = EWOCPRDBucket()
        nb_prd, __unused, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
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

def run_block_mosaic(
    tile_id: str,
    production_id: str,
    sar_csv: Optional[Path] = None,
    optical_csv: Optional[Path] = None,
    tir_csv: Optional[Path] = None,
    agera5_csv: Optional[Path] = None,
    data_folder: Optional[Path] = None,
    ewoc_detector: str = EWOC_CROPLAND_DETECTOR,
    end_season_year: int = 2021,
    ewoc_season: str = EWOC_SUPPORTED_SEASONS[3],
    cropland_model_version: str = "v700",
    croptype_model_version: str = "v720",
    irr_model_version: str = "v420",
    out_dirpath: Path = Path(gettempdir()),
    clean:bool=True,
    ) -> None:
    """
    Perform EWoC blocks mosaic
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param production_id: EWoC production id
    :type production_id: str
    :param sar_csv: Path to a csv file with all the detail about all the Sentinel-1
    images to process
    :type sar_csv: Path
    :param optical_csv: Path to a csv file with all the detail about all the Sentinel-2/
    Landsat 8 images to process
    :type optical_csv: Path
    :param tir_csv: Path to a csv file with all the detail about all
    the Landsat 8 TIR images to process
    :type tir_csv: Path
    :param agera5_csv: Path to a csv file with all the detail about all the AgERA5
    images to process
    :type agera5_csv: Path
    :param data_folder: Folder with CopDEM and/or cropland data
    :type data_folder: Path
    :param ewoc_detector: Type of detector to use, possible choices are cropland or croptype
    :type ewoc_detector: str
    :param end_season_year: End of season year
    :type end_season_year: int
    :param ewoc_season: Which season are we processing, possible options:
    annual, summer1, summer2 and winter
    :type ewoc_season: str
    :param cropland_model_version: The version of the AI model used for the cropland prediction
    :type cropland_model_version: str
    :param croptype_model_version: The version of the AI model used for the croptype prediction
    :type croptype_model_version: str
    :param irr_model_version: The version of the AI model used for croptype irrigation
    :type irr_model_version: str
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :return: None
    """
    uid = uuid4().hex[:6]
    uid = tile_id + "_" + uid
    # Create the config file
    ewoc_ard_bucket = EWOCARDBucket()

    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
        out_dirpath.mkdir()
    feature_blocks_dir = out_dirpath / "block_features"
    feature_blocks_dir.mkdir(parents=True,exist_ok=True)

    aez_id=int(production_id.split('_')[-2])

    if sar_csv is None:
        sar_csv = out_dirpath / f"{uid}_satio_sar.csv"
        ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath=sar_csv)
    if optical_csv is None:
        optical_csv = out_dirpath / f"{uid}_satio_optical.csv"
        ewoc_ard_bucket.optical_to_satio_csv(
            tile_id, production_id, filepath=optical_csv)
    no_tir=False
    if tir_csv is None:
        tir_csv = out_dirpath / f"{uid}_satio_tir.csv"
        ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
    else:
        with open(Path(tir_csv), 'r', encoding='utf8') as tir_file:
            tir_dict = list(csv.DictReader(tir_file))
            if len(tir_dict) <= 1:
                logger.warning(f"TIR ARD is empty for the tile {tile_id} => No irrigation computed!")
                no_tir=True

    if agera5_csv is None:
        agera5_csv = out_dirpath / f"{uid}_satio_agera5.csv"
        ewoc_aux_data_bucket = EWOCAuxDataBucket()
        ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)

    add_croptype = False
    if end_season_year == 2022:
        logger.info('Add additional croptype')
        add_croptype = True

    if not no_tir:
        csv_dict = {
            "OPTICAL": str(optical_csv),
            "SAR": str(sar_csv),
            "TIR": str(tir_csv),
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": str(agera5_csv),
        }
    else:
        csv_dict = {
            "OPTICAL": str(optical_csv),
            "SAR": str(sar_csv),
            "DEM": "s3://ewoc-aux-data/CopDEM_20m",
            "METEO": str(agera5_csv),
        }


    ewoc_config = generate_config_file(
        ewoc_detector,
        end_season_year,
        ewoc_season,
        production_id,
        cropland_model_version,
        croptype_model_version,
        irr_model_version,
        csv_dict,
        feature_blocks_dir= feature_blocks_dir,
        no_tir_data=no_tir,
        use_existing_features=False,
        add_croptype = add_croptype
    )

    ewoc_config_filepath = out_dirpath / f"{uid}_ewoc_config.json"
    if data_folder is not None:
        ewoc_config = update_config(ewoc_config, ewoc_detector, data_folder)
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)

    try:
        blocks_mosaic(
            tile_id,
            production_id,
            ewoc_config_filepath,
            out_dirpath,
            aez_id=aez_id
        )
    except Exception:
        
        logger.error("Mosaic failed")
        logger.error(traceback.format_exc())
    finally:
        if clean:
            logger.info(f"Cleaning the output folder {out_dirpath}")
            shutil.rmtree(out_dirpath)
            remove_tmp_files(Path.cwd(), f"{tile_id}.tif")

if __name__ == "__main__":
    pass