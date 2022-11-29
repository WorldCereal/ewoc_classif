============
EWoC Classification (Cloud version)
============


This python package is a wrapper for `wc-classification <https://github.com/WorldCereal/wc-classification>`_ that enables the integration of the classifier
within the EWoC system


Usage
-----

Before using the CLI you'll need to export some variables: ``EWOC_S3_ACCESS_KEY_ID`` and ``EWOC_S3_SECRET_ACCESS_KEY``.
In dev mode please export ``EWOC_DEV_MODE=True``. For the full list of env vars to use see `classification-docker` readme

.. code-block::

    usage: ewoc_classif [-h] [--version] [--block-ids BLOCK_IDS [BLOCK_IDS ...]] [--optical-csv OPTICAL_CSV] [--sar-csv SAR_CSV] [--tir-csv TIR_CSV] [--agera5-csv AGERA5_CSV] [--data-folder DATA_FOLDER]
                        [--ewoc-detector EWOC_DETECTOR] [--end-season-year END_SEASON_YEAR] [--ewoc-season {winter,summer1,summer2,annual,custom}] [--cropland-model-version CROPLAND_MODEL_VERSION]
                        [--croptype-model-version CROPTYPE_MODEL_VERSION] [--irr-model-version IRR_MODEL_VERSION] [--upload-block UPLOAD_BLOCK] [--postprocess POSTPROCESS] [-o OUT_DIRPATH] [-v] [-vv]
                        tile_id production_id

    EWoC Classification parser

    positional arguments:
      tile_id               MGRS S2 tile id
      production_id         EWoC production id

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      --block-ids BLOCK_IDS [BLOCK_IDS ...]
                            List of block id to process
      --optical-csv OPTICAL_CSV
                            List of OPTICAL products for a given S2 tile
      --sar-csv SAR_CSV     List of SAR products for a given S2 tile
      --tir-csv TIR_CSV     List of TIR products for a given S2 tile
      --agera5-csv AGERA5_CSV
                            Agera5 list
      --data-folder DATA_FOLDER
                            Folder storing CopDEM and Cropland data
      --ewoc-detector EWOC_DETECTOR
                            EWoC detector
      --end-season-year END_SEASON_YEAR
                            Year to use infer season date - format YYYY
      --ewoc-season {winter,summer1,summer2,annual,custom}
                            EWoC season
      --cropland-model-version CROPLAND_MODEL_VERSION
                            Cropland model version
      --croptype-model-version CROPTYPE_MODEL_VERSION
                            Croptype model version
      --irr-model-version IRR_MODEL_VERSION
                            Irrigation model version
      --upload-block UPLOAD_BLOCK
                            True if you want to upload each block, true by default
      --postprocess POSTPROCESS
                            True if you want to do mosaic only
      -o OUT_DIRPATH, --out-dirpath OUT_DIRPATH
                            Output Dirpath
      -v, --verbose         set loglevel to INFO
      -vv, --very-verbose   set loglevel to DEBUG




**Example**

.. code-block::

    ewoc_classif 31TCJ c728b264-5c97-4f4c-81fe-1500d4c4dfbd --end-season-year 2021 --cropland-model-version v512 --croptype-model-version v502 --irr-model-version v420 --block-ids 12 --ewoc-detector croptype --ewoc-season summer1
This CLI will run the summer1 croptype classification for 31TCJ only on block #12. The csv files necessary for the creation of the classifier input config file are created directly from the  s3 bucket

You can set the environment variable EWOC_MODELS_DIR_ROOT with the path where are located models, if this environnement variable is not set, the VITO artifactory is used as source.
