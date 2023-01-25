# -*- coding: utf-8 -*-
"""
Classification and postprocessing tools
"""
import os
import shutil
import traceback
import csv
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
    production_id: str,
    out_dirpath: Path,
    block_ids: Optional[List[int]]=None,
    upload_block: bool=True,
    clean:bool=True
) -> bool:
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
    logger.info("Running EWoC inference")

    if block_ids is not None:
        logger.info(f"Processing custom ids from CLI {block_ids}")
        ids_range = block_ids
    else:
        ewoc_block_size = str(os.getenv("EWOC_BLOCKSIZE", "512"))
        if ewoc_block_size == "512":
            total_ids = 483
        elif ewoc_block_size == "1024":
            total_ids = 120
        else:
            logger.error(f'Block size {ewoc_block_size} is not supported!')
            return False
        logger.info(f"Processing {total_ids} blocks")
        ids_range = list(range(total_ids + 1))

    with open(ewoc_config_filepath, encoding="UTF-8") as json_file:
        data = load(json_file)
        blocks_feature_dir = Path(data["parameters"]["features_dir"])

    return_codes=[]
    for block_id in ids_range:
        try:
            logger.info(f"[Start processing of {tile_id}_{block_id}] ")
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
                logger.info(f"{tile_id}_{block_id} finished with success!")
                return_codes.append(True)
                if upload_block:
                    ewoc_prd_bucket = EWOCPRDBucket()
                    nb_prd, __unused, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
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
                    # Add Upload print for Alex TODO: remove it
                    print(f"Uploaded {nb_prd} files to bucket | {up_dir}")
                else:
                    logger.info('No block uploaded as requested.')
            elif ret == 1:
                return_codes.append(True)
                logger.warning(f"{tile_id}_{block_id} is skip due to return code: {ret}")
                # Add Upload print for Alex TODO: remove it
                print(f"Uploaded {0} files to bucket | placeholder")
            else:
                return_codes.append(False)
                logger.error(f"{tile_id}_{block_id} failed with return code: {ret}")
                # Add Upload print for Alex TODO: remove it
                print(f"Uploaded {0} files to bucket | error")
        except Exception:
            logger.error(f"Block {block_id} failed with exception!")
            logger.error(traceback.format_exc())
            return_codes.append(False)
            break
        finally:
            if clean:
                shutil.rmtree(out_dirpath / "blocks", ignore_errors=True)

    if not all(return_codes):
        logger.error('One of the block failed with an unexpected return code')
        return False

    # If we process all the tile, generate the cogs and upload if requested
    # TODO manage the fact that we clean the block after upload!
    if block_ids is None:
        upload_product=False
        raise NotImplementedError('Not currently correctly implemented!')
        logger.info("Start cog mosaic")
        run_tile(
            tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False
        )
        if upload_product:
        # Push the results to the s3 bucket
            ewoc_prd_bucket = EWOCPRDBucket()
            nb_prd, __unused, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
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
        else:
            logger.info('No product uploaded as requested.')
        if clean:
            logger.warning('Clean nothing!')

    return True

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
    end_season_year: int = 2021,
    ewoc_season: str = EWOC_SUPPORTED_SEASONS[3],
    cropland_model_version: str = "v700",
    croptype_model_version: str = "v720",
    irr_model_version: str = "v420",
    upload_block: bool = True,
    postprocess: bool = False,
    out_dirpath: Path = Path(gettempdir()),
    clean:bool=True, 
    no_tir:bool=False,
    use_existing_features: bool = False
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
    :param no_tir: Boolean specifying if the csv file containing details on ARD TIR is empty or not
    :type no_tir: bool
    :return: None
    """
    uid = uuid4().hex[:6]
    uid = tile_id + "_" + uid
    # Create the config file
    ewoc_ard_bucket = EWOCARDBucket()
    ewoc_prd_bucket  = EWOCPRDBucket()

    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / uid
        out_dirpath.mkdir()
    feature_blocks_dir = out_dirpath / "block_features"
    feature_blocks_dir.mkdir(parents=True,exist_ok=True)

    aez_id=int(production_id.split('_')[-2])
    if use_existing_features:
        for block in block_ids:
            bucket_prefix=f'{production_id}/block_features/blocks/{tile_id}/{end_season_year}_annual/features_cropland/{tile_id}_{aez_id}_{block:03d}_features.tif'
            logger.info(f"Trying to download blocks features : {bucket_prefix} to {feature_blocks_dir}")
            out_features_dir=f'{str(feature_blocks_dir)}/blocks/{tile_id}/{end_season_year}_annual/features_cropland/'
            os.makedirs(out_features_dir, exist_ok=True)
            ewoc_prd_bucket.download_bucket_prefix(bucket_prefix, Path(out_features_dir))
            logger.info("features {bucket_prefix} downloaded with success")


    if use_existing_features:
        bucket_prefix=f'{production_id}/block_features/'
        ewoc_prd_bucket.download_bucket_prefix(bucket_prefix, feature_blocks_dir)
        logger.info("Trying to download blocks: {bucket_prefix} to {feature_blocks_dir}")

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
    else:
        with open(Path(tir_csv), 'r', encoding='utf8') as tir_file:
            tir_dict = [row for row in csv.DictReader(tir_file)]
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
        add_croptype = add_croptype
    )

    ewoc_config_filepath = out_dirpath / f"{uid}_ewoc_config.json"
    if data_folder is not None:
        ewoc_config = update_config(ewoc_config, ewoc_detector, data_folder)
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)
    # Process tile (and optionally select blocks)
    try:
        if not postprocess:
            process_status = process_blocks(
                tile_id,
                ewoc_config_filepath,
                production_id,
                out_dirpath,
                block_ids,
                upload_block=upload_block,
                clean=clean
            )
            if not process_status:
                raise RuntimeError(f"Processing of {tile_id}_{block_ids} failed with error!")
        else:
            postprocess_mosaic(
                tile_id, production_id, ewoc_config_filepath, out_dirpath
            )
    except Exception:
        logger.error("Processing failed")
        logger.error(traceback.format_exc())
    finally:
        if clean:
            logger.info(f"Cleaning the output folder {out_dirpath}")
            shutil.rmtree(out_dirpath)
            remove_tmp_files(Path.cwd(), f"{tile_id}.tif")


if __name__ == "__main__":
    pass
