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
from satio import layers
from satio.grid import S2TileBlocks
import pandas as pd

from ewoc_dag.bucket.eobucket import UploadProductError
from ewoc_dag.ewoc_dag import get_blocks
from ewoc_dag.bucket.ewoc import EWOCARDBucket, EWOCAuxDataBucket, EWOCPRDBucket
from loguru import logger
from worldcereal import SUPPORTED_SEASONS as EWOC_SUPPORTED_SEASONS
from worldcereal.worldcereal_products import run_tile
from worldcereal.collections import (WorldCerealSigma0TiledCollection,
                                     WorldCerealThermalTiledCollection)
from worldcereal.seasons import get_processing_dates
from worldcereal.utils.__init__ import get_coll_maxgap

from ewoc_classif.ewoc_model import (EWOC_CL_MODEL_VERSION,
                                     EWOC_CT_MODEL_VERSION,
                                     EWOC_IRR_MODEL_VERSION)
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

def download_features(
    ewoc_prd_bucket,
    tile_id,
    end_season_year,
    ewoc_season,
    block,
    production_id,
    aez_id,
    feature_blocks_dir
    ) -> bool:
    """
    Check if block features exists and if True download features_cropland for cropland when season
    is annual or download features_croptype and features_irrigation when season is summer1, summer2
    or winter
    :param ewoc_prd_bucket: EWOCPRDBucket to use check and download method
    :type ewoc_prd_bucket: object of class EWOCPRDBucket
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param end_season_year: End of season year
    :type end_season_year: int
    :param ewoc_season: Which season are we processing, possible options:
    annual, summer1, summer2 and winter
    :type ewoc_season: str
    :param block: block id to process (blocks= equal area subdivisions of a tile)
    :type block: int
    :param production_id: EWoC production id
    :type production_id: str
    :param features_block_dir: Path where the features are downloaded
    :type features_block_dir: Path
    """
    check_product_irr=True
    if ewoc_season=='annual':
        season_tag='annual/features_cropland'
    else:
        season_tag=f'{ewoc_season}/features_croptype'
        bucket_prefix_irrigation=f'{production_id}/block_features/blocks/{tile_id}/{end_season_year}_{ewoc_season}/features_irrigation/{tile_id}_{aez_id}_{block:03d}_features.tif'
        out_features_dir_irrigation=f'{str(feature_blocks_dir)}/blocks/{tile_id}/{end_season_year}_{ewoc_season}/features_irrigation/'
        check_product_irr = ewoc_prd_bucket._check_product_file(bucket_prefix_irrigation)

        if check_product_irr:
            logger.info('Irrigation features exists')
            os.makedirs(out_features_dir_irrigation, exist_ok=True)
            ewoc_prd_bucket.download_bucket_prefix(
                bucket_prefix_irrigation,
                Path(out_features_dir_irrigation))
            logger.info(f"features {bucket_prefix_irrigation} downloaded with success")
        else:
            logger.warning(f'Features {bucket_prefix_irrigation} does not exist, create features')

    bucket_prefix=f'{production_id}/block_features/blocks/{tile_id}/{end_season_year}_{season_tag}/{tile_id}_{aez_id}_{block:03d}_features.tif'
    out_features_dir=f'{str(feature_blocks_dir)}/blocks/{tile_id}/{end_season_year}_{season_tag}'

    check_product = ewoc_prd_bucket._check_product_file(bucket_prefix)
    if check_product:
        logger.info(f'{season_tag} features exists')
        os.makedirs(out_features_dir, exist_ok=True)
        ewoc_prd_bucket.download_bucket_prefix(bucket_prefix, Path(out_features_dir))
        logger.info(f"features {bucket_prefix} downloaded with success")
    else:
        logger.warning(f'Features {bucket_prefix} does not exist, create features')

    return (check_product and check_product_irr)

def check_collection(collection, name,
                     start_date, end_date, tile_id, block, fail_threshold=1000,
                     min_size=2):
    """Helper function to check collection completeness
    and report gap lengths

    Args:
        collection (BaseCollection): a satio collection
        name (str): name of the collection used for reporting
        start_date (str): processing start date (Y-m-d)
        end_date (str): processing end date (Y-m-d)
        fail_threshold (int): amount of days beyond which
                        an error is raised that the collection is
                        incomplete.
        min_size (int): minimum amount of products to be present
                        in collection before failing anyway.
    """
    processingblocks = S2TileBlocks(1024, s2grid=layers.load('s2grid')).blocks(*tile_id)

    processingblocks = processingblocks.loc[block]
    collection = collection.filter_bounds(processingblocks['bounds'][block[0]],
                                          processingblocks['epsg'][block[0]])
    collstart = (pd.to_datetime(start_date) -
                     pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    collend = (pd.to_datetime(end_date) +
                   pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    collection.df = collection.df[(collection.df.date >= collstart)
            & (collection.df.date < collend)]

    if name=='TIR':
        collection=collection.filter_nodata()

    opt_only=False

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    collstart = pd.to_datetime(collection.df.date.min())
    collend = pd.to_datetime(collection.df.date.max())

    # Check whether we have the minimum amount of
    # products to not run into a pure processing issue
    collsize = collection.df.shape[0]
    if collsize < min_size:
        logger.warning(f"Incomplete collection {name} : {collsize} less than {min_size}")
        opt_only=True

    # Check collection start
    gapstart = collstart - start_date
    gapstart = gapstart.days
    gapstart = max(gapstart, 0)

    # Check collection end
    gapend = end_date - collend
    gapend = gapend.days
    gapend = max(gapend, 0)

    maxgap = pd.to_datetime(collection.df.date).diff().max().days

    # Report on collection
    logger.info('-' * 50)
    logger.info(f'{name} first image: {collstart}')
    logger.info(f'{name} last image: {collend}')
    logger.info(f'{name} largest gap: {maxgap}')
    # Fail processing if collection is incomplete
    if gapstart > fail_threshold:
        logger.warning(f"Incomplete collection {name}: {gapstart} exceeds {fail_threshold}")
        opt_only=True
    if gapend > fail_threshold:
        logger.warning(f"Incomplete collection {name}: {gapend} exceeds {fail_threshold}")
        opt_only=True
    if maxgap > fail_threshold:
        logger.warning(f"Incomplete collection {name}: {maxgap} exceeds {fail_threshold}")
        opt_only=True

    return opt_only


def process_blocks(
    tile_id: str,
    ewoc_config_filepath: Path,
    production_id: str,
    out_dirpath: Path,
    aez_id: int,
    block_ids: Optional[List[int]]=None,
    upload_block: bool=True,
    clean:bool=True,
    upload_log:bool=False
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
    :param upload_block: True if you want to upload each block and skip the mosaic.
     If False, multiple blocks can be
     processed and merged into a mosaic within the same process (or command)
    :type upload_block: bool
    :param aez_id : If provided, the AEZ ID will be enforced instead of automatically
    derived from the Sentinel-2 tile ID.
    :type aez_id: int
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :param upload_log : If true, upload exitlog and proclog with the block at the end of processing
    :type upload_log : bool
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
        use_exisiting_features=data["parameters"]["use_existing_features"]

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
                aez_id=aez_id
            )
            if ret == 0:
                logger.info(f"{tile_id}_{block_id} finished with success!")
                return_codes.append(True)
                if upload_block:
                    ewoc_prd_bucket = EWOCPRDBucket()
                    nb_prd, __unused, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
                        out_dirpath / "blocks", production_id + "/blocks"
                    )
                    if upload_log:
                        ewoc_prd_bucket.upload_ewoc_prd(
                            out_dirpath / "exitlogs", production_id + "/exitlogs"
                        )
                        ewoc_prd_bucket.upload_ewoc_prd(
                            out_dirpath / "proclogs", production_id + "/proclogs"
                        )
                    if any(blocks_feature_dir.iterdir()) and not use_exisiting_features:
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
            tile_id,
            ewoc_config_filepath,
            out_dirpath,
            postprocess=True,
            process=False,
            aez_id=aez_id
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
        tile_id, ewoc_config_filepath, out_dirpath, postprocess=True, process=False, aez_id=aez_id
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
    use_existing_features: bool = True,
    upload_log:bool=False
    ) -> None:
    """
    Perform EWoC classification
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param production_id: EWoC production id
    :type production_id: str
    :param block_ids: List of block ids to process
    (blocks= equal area subdivisions of a tile)
    :type block_ids: List[int]
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
    :param upload_block: True if you want to upload each block and skip the mosaic.
    If False, multiple blocks can be
     processed and merged into a mosaic within the same process (or command)
    :type upload_block: bool
    :param postprocess: If True only the postprocessing (aka mosaic) will be performed,
    default to False
    :type postprocess: bool
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :param no_tir: Boolean specifying if the csv file containing details on ARD TIR is empty or not
    :type no_tir: bool
    :param use_existing_features: If true, is going to download existing features, otherwise
    computes it as usual
    :param use_existing_features: bool
    :param upload_log : If true, upload exitlog and proclog with the block at the end of processing
    :type upload_log : bool
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
    no_sar=False
    no_tir=False
    add_croptype = False
    csv_dict={}

    ewoc_prd_bucket  = EWOCPRDBucket()
    if use_existing_features and block_ids is not None:
        for block in block_ids:
            check_features=download_features(
                ewoc_prd_bucket,
                tile_id,
                end_season_year,
                ewoc_season,
                block,
                production_id,
                aez_id,
                feature_blocks_dir)

        use_existing_features=check_features
    else:
        if sar_csv is None:
            sar_csv = out_dirpath / f"{uid}_satio_sar.csv"
            ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath=sar_csv)
        else:
            with open(Path(sar_csv), 'r', encoding='utf8') as sar_file:
                sar_dict = list(csv.DictReader(sar_file))
                if len(sar_dict) <= 1:
                    logger.warning(f"SAR ARD is empty for the tile {tile_id}")
                    no_sar=True
        if optical_csv is None:
            optical_csv = out_dirpath / f"{uid}_satio_optical.csv"
            ewoc_ard_bucket.optical_to_satio_csv(
                tile_id, production_id, filepath=optical_csv)
        if tir_csv is None:
            tir_csv = out_dirpath / f"{uid}_satio_tir.csv"
            ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
        else:
            with open(Path(tir_csv), 'r', encoding='utf8') as tir_file:
                tir_dict = list(csv.DictReader(tir_file))
                if len(tir_dict) <= 1:
                    logger.warning(f"TIR ARD is empty for {tile_id}: No irrigation computed!")
                    no_tir=True

        if agera5_csv is None:
            agera5_csv = out_dirpath / f"{uid}_satio_agera5.csv"
            ewoc_aux_data_bucket = EWOCAuxDataBucket()
            ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)

        if end_season_year == 2022:
            logger.info('Add additional croptype')
            add_croptype = True

        sar_ard_coll = WorldCerealSigma0TiledCollection.from_path(sar_csv)
        tir_ard_coll = WorldCerealThermalTiledCollection.from_path(tir_csv)

        start_date, end_date = get_processing_dates(ewoc_season, aez_id, end_season_year)
        logger.info("Checking collection of SAR")
        no_sar=check_collection(sar_ard_coll, 'SAR', start_date, end_date,
                                [tile_id], block_ids, fail_threshold=get_coll_maxgap('SAR'))
        logger.info("Checking collection of TIR")
        no_tir=check_collection(tir_ard_coll, 'TIR', start_date, end_date,
                                [tile_id], block_ids, fail_threshold=get_coll_maxgap('TIR'))

        if not no_tir and not no_sar:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "SAR": str(sar_csv),
                "TIR": str(tir_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }
        elif not no_sar and no_tir:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "SAR": str(sar_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }
        elif not no_tir and no_sar:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "TIR": str(tir_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }
        else:
            csv_dict = {
                "OPTICAL": str(optical_csv),
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
        use_existing_features=use_existing_features,
        add_croptype = add_croptype
    )

    ewoc_config_filepath = out_dirpath / f"{uid}_ewoc_config.json"
    if data_folder is not None:
        ewoc_config = update_config(ewoc_config, ewoc_detector, data_folder)
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)
    # Process tile (and optionally select blocks)
    try:
        aez_id=int(production_id.split('_')[-2])
        if not postprocess:
            process_status = process_blocks(
                tile_id,
                ewoc_config_filepath,
                production_id,
                out_dirpath,
                aez_id,
                block_ids,
                upload_block=upload_block,
                clean=clean,
                upload_log=upload_log
            )
            if not process_status:
                raise RuntimeError(f"Processing of {tile_id}_{block_ids} failed with error!")
        else:
            postprocess_mosaic(
                tile_id, production_id, ewoc_config_filepath, out_dirpath, aez_id=aez_id
            )
    except Exception:
        logger.error("Processing failed")
        logger.error(traceback.format_exc())
    finally:
        if clean:
            logger.info(f"Cleaning the output folder {out_dirpath}")
            shutil.rmtree(out_dirpath)
            remove_tmp_files(Path.cwd(), f"{tile_id}.tif")

def classify_block(
    tile_id: str,
    ewoc_config_filepath: Path,
    out_dirpath: Path,
    aez_id: int,
    block_id: int,
) -> int:
    """
    Process a single block, cropland/croptype prediction
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param ewoc_config_filepath: Path to the config file generated previously
    :type ewoc_config_filepath: Path
    :param block_id: Block id to process
    :type block_id: int
    :param aez_id : If provided, the AEZ ID will be enforced instead of automatically
    derived from the Sentinel-2 tile ID.
    :type aez_id: int
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :return: int
    """
    # Retrieve some parameters from config file
    with open(ewoc_config_filepath, encoding="UTF-8") as json_file:
        data = load(json_file)
    year = data["parameters"]["year"]
    season = data["parameters"]["season"]

    # Expected dirpath where the block files are generated
    out_dirpath.mkdir(exist_ok=True)

    block_id_msg = f'{tile_id}_{block_id}-{season}-{year}'

    # Use VITO code to block classification
    logger.info(f"Start classification of {block_id_msg}")
    try:
        ret = run_tile(
            tile_id,
            ewoc_config_filepath,
            out_dirpath,
            blocks=[block_id],
            postprocess=False,
            process=True,
            aez_id=aez_id
        )
    except Exception:
        msg = f"Classification of {block_id_msg} failed with exception: {traceback.format_exc()}"
        logger.critical(msg)
        # TODO: remove this message used by Alex
        # print(f"Error: {msg}")
        return 2

    if ret == 0:
        logger.info(f"Classification of {block_id_msg} finished with success!")
        return ret

    if ret == 1:
        logger.warning(f"{block_id_msg} classification is skip due to return code: {ret}")
        return ret

    msg = f"{block_id_msg} classification failed with return code: {ret}"
    logger.error(msg)
    # TODO: remove this message used by Alex
    # print(f"Error: {msg}")
    return ret


def generate_ewoc_block(
    tile_id: str,
    production_id: str,
    block_id: int,
    sar_csv: Optional[Path] = None,
    optical_csv: Optional[Path] = None,
    tir_csv: Optional[Path] = None,
    agera5_csv: Optional[Path] = None,
    data_folder: Optional[Path] = None,
    ewoc_detector: str = EWOC_CROPLAND_DETECTOR,
    end_season_year: int = 2021,
    ewoc_season: str = EWOC_SUPPORTED_SEASONS[3],
    cropland_model_version: str = EWOC_CL_MODEL_VERSION,
    croptype_model_version: str = EWOC_CT_MODEL_VERSION,
    irr_model_version: str = EWOC_IRR_MODEL_VERSION,
    upload_block: bool = True,
    out_dirpath: Path = Path(gettempdir()),
    clean:bool=True,
    ignore_existing_features:bool = False,
    upload_log: bool=False
    ) -> None:
    """
    Perform EWoC classification
    :param tile_id: Sentinel-2 MGRS tile id ex 31TCJ
    :type tile_id: str
    :param production_id: EWoC production id
    :type production_id: str
    :param block_ids: List of block ids to process
    (blocks= equal area subdivisions of a tile)
    :type block_ids: List[int]
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
    :param upload_block: True if you want to upload each block and skip the mosaic.
    If False, multiple blocks can be
     processed and merged into a mosaic within the same process (or command)
    :type upload_block: bool
    :param postprocess: If True only the postprocessing (aka mosaic) will be performed,
    default to False
    :type postprocess: bool
    :param out_dirpath: Output directory path
    :type out_dirpath: Path
    :param no_tir: Boolean specifying if the csv file containing details on ARD TIR is empty or not
    :type no_tir: bool
    :param ignore_existing_features: If true, is going to ignore the existing features, otherwise
    computes we will use it
    :param ignore_existing_features : bool
    :return: None
    :param upload_log : If true, upload exitlog and proclog with the block at the end of processing
    :type upload_log : bool
    :return None
    """
    uid = uuid4().hex[:6]
    tile_uid = tile_id + "_" + uid
    tile_id_msg = f"{tile_id}_{block_id}-{end_season_year}-{ewoc_season}"

    if out_dirpath == Path(gettempdir()):
        out_dirpath = out_dirpath / f'{tile_id_msg}_{uid}'
        out_dirpath.mkdir()
    feature_blocks_dir = out_dirpath / "block_features"
    feature_blocks_dir.mkdir(parents=True,exist_ok=True)

    aez_id=int(production_id.split('_')[-2])
    no_sar=False
    no_tir=False
    add_croptype = False
    csv_dict={}

    ewoc_prd_bucket  = EWOCPRDBucket()

    use_existing_features = False
    if not ignore_existing_features:
        use_existing_features=download_features(
            ewoc_prd_bucket,
            tile_id,
            end_season_year,
            ewoc_season,
            block_id,
            production_id,
            aez_id,
            feature_blocks_dir)

    if not use_existing_features:
        # Use ARD if block features are not found
        ewoc_ard_bucket = EWOCARDBucket()
        start_date, end_date = get_processing_dates(ewoc_season, aez_id, end_season_year)

        # SAR ARD collection
        if sar_csv is None:
            sar_csv = out_dirpath / f"{tile_uid}_satio_sar.csv"
            ewoc_ard_bucket.sar_to_satio_csv(tile_id, production_id, filepath=sar_csv)
        else:
            with open(Path(sar_csv), 'r', encoding='utf8') as sar_file:
                sar_dict = list(csv.DictReader(sar_file))
                if len(sar_dict) <= 1:
                    logger.warning(f"SAR ARD is empty for {tile_id}: Use optical only model!")
                    no_sar=True

        logger.info("Checking SAR ARD collection completeness.")
        no_sar=check_collection(WorldCerealSigma0TiledCollection.from_path(sar_csv),
                                'SAR', start_date, end_date,
                                [tile_id], [block_id], fail_threshold=get_coll_maxgap('SAR'))

        # Optical ARD collection
        if optical_csv is None:
            optical_csv = out_dirpath / f"{tile_uid}_satio_optical.csv"
            ewoc_ard_bucket.optical_to_satio_csv(
                tile_id, production_id, filepath=optical_csv)

        # TIR ARD collection
        if tir_csv is None:
            tir_csv = out_dirpath / f"{tile_uid}_satio_tir.csv"
            ewoc_ard_bucket.tir_to_satio_csv(tile_id, production_id, filepath=tir_csv)
        else:
            with open(Path(tir_csv), 'r', encoding='utf8') as tir_file:
                tir_dict = list(csv.DictReader(tir_file))
                if len(tir_dict) <= 1:
                    logger.warning(f"TIR ARD is empty for {tile_id}: No irrigation computed!")
                    no_tir=True

        logger.info("Checking TIR ARD collection completeness.")
        l8coll = WorldCerealThermalTiledCollection.from_path(tir_csv)
        no_tir=check_collection(l8coll, 'TIR', start_date, end_date,
                                [tile_id], [block_id], fail_threshold=get_coll_maxgap('TIR'))

        if agera5_csv is None:
            agera5_csv = out_dirpath / f"{tile_uid}_satio_agera5.csv"
            ewoc_aux_data_bucket = EWOCAuxDataBucket()
            ewoc_aux_data_bucket.agera5_to_satio_csv(filepath=agera5_csv)

        if not no_tir and not no_sar:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "SAR": str(sar_csv),
                "TIR": str(tir_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }
        elif not no_sar and no_tir:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "SAR": str(sar_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }
        elif not no_tir and no_sar:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "TIR": str(tir_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }
        else:
            csv_dict = {
                "OPTICAL": str(optical_csv),
                "DEM": "s3://ewoc-aux-data/CopDEM_20m",
                "METEO": str(agera5_csv),
            }

    if end_season_year == 2022 and croptype_model_version=='v720':
        logger.info('Add additional croptype')
        add_croptype = True

    # Create the config file
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
        use_existing_features=use_existing_features,
        add_croptype = add_croptype
    )

    ewoc_config_filepath = out_dirpath / f"{tile_uid}_ewoc_config.json"
    if data_folder is not None:
        ewoc_config = update_config(ewoc_config, ewoc_detector, data_folder)
    with open(ewoc_config_filepath, "w", encoding="UTF-8") as ewoc_config_fp:
        dump(ewoc_config, ewoc_config_fp, indent=2)

    # Perform block classification with VITO code
    ret = classify_block(
        tile_id,
        ewoc_config_filepath,
        out_dirpath,
        aez_id,
        block_id,
    )
    if ret > 1:
        raise RuntimeError(f"Processing of {tile_id_msg} failed with error or exception!")

    if ret == 1:
        # Block skip no need to upload
        # TODO: remove this message used by Alex
        print(f"Uploaded {0} files to bucket | placeholder")
    else:
        if upload_block:
            root_s3 = f"s3://ewoc-prd/{production_id}"
            try:
                nb_prd, __unused, up_dir = ewoc_prd_bucket.upload_ewoc_prd(
                    out_dirpath / "blocks", production_id + "/blocks"
                )
                if upload_log:
                    ewoc_prd_bucket.upload_ewoc_prd(
                        out_dirpath / "exitlogs", production_id + "/exitlogs"
                    )
                    ewoc_prd_bucket.upload_ewoc_prd(
                        out_dirpath / "proclogs", production_id + "/proclogs"
                    )
                if any(feature_blocks_dir.iterdir()) and not use_existing_features:
                    ewoc_prd_bucket.upload_ewoc_prd(
                        feature_blocks_dir, production_id + "/block_features"
                    )
            except UploadProductError as exc:
                msg= f'Upload from {out_dirpath} to {root_s3} failed for {tile_id_msg}!'
                logger.error(msg)
                # TODO: remove this message used by Alex
                #print(f"Error: {msg}")
                raise RuntimeError(msg) from exc

            logger.info(f"Uploaded {out_dirpath} to {up_dir} ")
            # TODO: remove this message used by Alex
            print(f"Uploaded {nb_prd} files to bucket | {up_dir}")
        else:
            logger.info('No block uploaded as requested.')

    if clean:
        logger.info(f"Cleaning the output folder {out_dirpath}")
        shutil.rmtree(out_dirpath)
        remove_tmp_files(Path.cwd(), f"{tile_id}.tif")

if __name__ == "__main__":
    pass
