# -*- coding: utf-8 -*-
""" Test EWoC classif
"""
import os
import unittest
import json
import filecmp

from ewoc_classif.utils import generate_config_file
from ewoc_classif.classif import run_classif, EWOC_SUPPORTED_SEASONS, EWOC_CROPTYPE_DETECTOR, EWOC_CROPLAND_DETECTOR
import worldcereal.resources.exampleconfigs
import importlib_resources as pkg_resources



class Test_Classif(unittest.TestCase):

    def test_generate_config_file_cropland(self):
        """ Nominal cropland test
        """
        data = pkg_resources.open_text(worldcereal.resources.exampleconfigs, 'example_bucketrun_annual_config.json')
        data_js = json.load(data)

        config_file_cropland=generate_config_file(
        featuresettings=EWOC_CROPLAND_DETECTOR,
        end_season_year=2019,
        ewoc_season=EWOC_SUPPORTED_SEASONS[3],
        production_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        cropland_model_version='v700',
        croptype_model_version='v720',
        irr_model_version='v420',
        csv_dict={
		"OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
		"SAR": "/data/worldcereal/s3collections/satio_sar.csv",
		"TIR": "/data/worldcereal/s3collections/satio_tir.csv",
		"DEM": "s3://ewoc-aux-data/CopDEM_20m",
		"METEO": "/data/worldcereal/s3collections/satio_agera5_yearly.csv"
        },
        feature_blocks_dir="/path/for/feature/blocks",
        no_tir_data=False,
        use_existing_features=True)
        for i in data_js.keys():
            print(f"--- for {i} with value of {data_js[i]} \n --- we have {config_file_cropland[i]}")
            print(f"---> {i} equals ? : {config_file_cropland[i]==data_js[i]}")


    def test_generate_config_file_summer1(self):
        """ Nominal summer1 test
        """
        EWOC_MODELS_DIR_ROOT=None
        data = pkg_resources.open_text(worldcereal.resources.exampleconfigs, 'example_bucketrun_summer1_config.json')
        data_js = json.load(data)

        config_file_cropland=generate_config_file(
        featuresettings=EWOC_CROPTYPE_DETECTOR,
        end_season_year=2021,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        production_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        cropland_model_version='v700',
        croptype_model_version='v720',
        irr_model_version='v420',
        csv_dict={
		"OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
		"SAR": "/data/worldcereal/s3collections/satio_sar.csv",
		"TIR": "/data/worldcereal/s3collections/satio_tir.csv",
		"DEM": "s3://ewoc-aux-data/CopDEM_20m",
		"METEO": "/data/worldcereal/s3collections/satio_agera5_yearly.csv",
        },
        feature_blocks_dir="/path/for/feature/blocks",
        no_tir_data=False,
        use_existing_features=True)
        for i in data_js.keys():
            print(f"--- for {i} with value of {data_js[i]} \n --- we have {config_file_cropland[i]}")
            print(f"---> {i} equals ? : {config_file_cropland[i]==data_js[i]}")

    def test_generate_config_file_summer2(self):
        """ Nominal summer2 test
        """
        EWOC_MODELS_DIR_ROOT=None
        data = pkg_resources.open_text(worldcereal.resources.exampleconfigs, 'example_bucketrun_summer2_config.json')
        data_js = json.load(data)

        config_file_cropland=generate_config_file(
        featuresettings=EWOC_CROPTYPE_DETECTOR,
        end_season_year=2021,
        ewoc_season=EWOC_SUPPORTED_SEASONS[2],
        production_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        cropland_model_version='v700',
        croptype_model_version='v720',
        irr_model_version='v420',
        csv_dict={
		"OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
		"SAR": "/data/worldcereal/s3collections/satio_sar.csv",
		"TIR": "/data/worldcereal/s3collections/satio_tir.csv",
		"DEM": "s3://ewoc-aux-data/CopDEM_20m",
		"METEO": "/data/worldcereal/s3collections/satio_agera5_yearly.csv",
        },
        feature_blocks_dir="/path/for/feature/blocks",
        no_tir_data=False,
        use_existing_features=True)
        for i in data_js.keys():
            print(f"--- for {i} with value of {data_js[i]} \n --- we have {config_file_cropland[i]}")
            print(f"---> {i} equals ? : {config_file_cropland[i]==data_js[i]}")

    def test_generate_config_file_winter(self):
        """ Nominal winter test
        """
        EWOC_MODELS_DIR_ROOT=None
        data = pkg_resources.open_text(worldcereal.resources.exampleconfigs, 'example_bucketrun_winter_config.json')
        data_js = json.load(data)

        config_file_cropland=generate_config_file(
        featuresettings=EWOC_CROPTYPE_DETECTOR,
        end_season_year=2021,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0],
        production_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        cropland_model_version='v700',
        croptype_model_version='v720',
        irr_model_version='v420',
        csv_dict={
		"OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
		"SAR": "/data/worldcereal/s3collections/satio_sar.csv",
		"TIR": "/data/worldcereal/s3collections/satio_tir.csv",
		"DEM": "s3://ewoc-aux-data/CopDEM_20m",
		"METEO": "/data/worldcereal/s3collections/satio_agera5_yearly.csv",
        },
        feature_blocks_dir="/path/for/feature/blocks",
        no_tir_data=False,
        use_existing_features=True)
        for i in data_js.keys():
            print(f"--- for {i} with value of {data_js[i]} \n --- we have {config_file_cropland[i]}")
            print(f"---> {i} equals ? : {config_file_cropland[i]==data_js[i]}")