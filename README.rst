============
EWoC Classification (Cloud version)
============


This python package is a wrapper for `wc-classification <https://github.com/WorldCereal/wc-classification>`_ that enables the integration of the classifier
within the EWoC system


Usage
-----

Before using the CLI you'll need to export some variables: ``EWOC_S3_ACCESS_KEY_ID`` and ``EWOC_S3_SECRET_ACCESS_KEY``.
In dev mode please export ``EWOC_DEV_MODE=True``.

.. code-block::

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
      --ewoc-detector EWOC_DETECTOR
                            EWoC detector
      --end-season-year END_SEASON_YEAR
                            Year to use infer season date - format YYYY
      --ewoc-season {winter,summer1,summer2,annual,custom}
                            EWoC season
      --model-version MODEL_VERSION
                            Model version
      --upload-block UPLOAD_BLOCK
                            True if you want to upload each block
      --postprocess POSTPROCESS
                            True if you want to do mosaic only
      -o OUT_DIRPATH, --out-dirpath OUT_DIRPATH
                            Output Dirpath
      -v, --verbose         set loglevel to INFO
      -vv, --very-verbose   set loglevel to DEBUG


**Example**

.. code-block::

    ewoc_classif 31TCJ --block-ids 12
This CLI will run the cropland classification for 31TCJ only on block #12. The csv files necessary for the creation of the classifier input config file are created directly from the  s3 bucket

