# -*- coding: utf-8 -*-
""" Test EWoC classif
"""
import os
import unittest

from ewoc_classif.classif import run_classif, EWOC_SUPPORTED_SEASONS, EWOC_CROPTYPE_DETECTOR

class TestClassif(unittest.TestCase):
    """Class for unittest cases
    """
    def setUp(self):
        self.clean=True
        if os.getenv("EWOC_TEST_DEBUG_MODE") is not None:
            self.clean=False

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_50HQH_64(self):
        """ Nominal cropland test
        """
        run_classif('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20220920095058',
        block_ids=[64],
        upload_block=False,)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_summer1_50HQH_64(self):
        """ Nominal croptype summer 1 test
        """
        run_classif('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20220920095058',
        block_ids=[64],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    # TODO: see with VITO to return an exception in this case or return_code = 2
    def test_run_classif_croptype_summer2_50HQH_64(self):
        """ No summer2 for this aez, therefore the block is skip
        """
        run_classif('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20220920095058',
        block_ids=[64],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[2])

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_winter_50HQH_64(self):
        """ Nominal croptype winter test
        """
        run_classif('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20220920095058',
        block_ids=[64],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    # TODO see with VITO to write a empty block in this case with warning message and return success
    def test_run_classif_cropland_22NBM_13(self):
        """ Less than 3 off-swath acquisitions found, therefore the block is skip
        """
        run_classif('22NBM',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        block_ids=[13],
        upload_block=False,
        clean=self.clean)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_48MYS_1(self):
        run_classif('48MYS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_8023_20220918052243',
        block_ids=[1],
        upload_block=False)

    # TODO see with VITO to write a empty block in this case with warning message and return success
    def test_run_classif_cropland_48MYS_110(self):
        """ Less than 3 off-swath acquisitions found, therefore the block is skip
        """
        run_classif('48MYS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_8023_20220918052243',
        block_ids=[110],
        upload_block=False)

    def test_run_classif_croptype_summer1_45SVC_99(self):
        """ Nominal error: No cropland pixels, therefore block is write with nodata 255 value
        """
        run_classif('45SVC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_25144_20220921094656',
        block_ids=[99],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_summer1_15STU_119(self):
        """ This test failed due to the maxgap issue on TIR (64 instead 60)"""
        run_classif('15STU',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_46173_20220823152135',
        block_ids=[119],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    # TODO: fix the test to succeed
    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_summer1_15STU_119_with_larger_TIR_gap(self):
        """ This test no more failed due to the increase of the maxgap for TIR (300 instead 60)"""
        os.environ['EWOC_COLL_MAXGAP_TIR']='300'
        print(os.environ['EWOC_COLL_MAXGAP_TIR'])
        run_classif('15STU',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_46173_20220823152135',
        block_ids=[119],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_run_classif_croptype_summer1_55LBE_1(self):
        """ No cropland pixels, therefore block is write with nodata 255 value
        """
        run_classif('55LBE',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_12046_20220920103952',
        block_ids=[1],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

     # EWOC_COLL_MAXGAP_TIR=300 18MYT
     # c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824
     # --block-ids 108
     # --ewoc-detector croptype
     # --ewoc-season summer2

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_01KFS_60(self):
        """ This test failed due to the maxgap issue on SAR (108 instead 60)
        """
        run_classif('01KFS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_5049_20220926141536',
        block_ids=[60],
        upload_block=False)

    # TODO: fix the test to succeed
    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_01KFS_60_with_larger_SAR_gap(self):
        """ This test no more failed due to the increase of the maxgap for SAR (120 instead 60)
        """
        os.environ['EWOC_COLL_MAXGAP_SAR']='120'
        run_classif('01KFS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_5049_20220926141536',
        block_ids=[60],
        upload_block=False)

    def test_run_classif_cropland_15PXR_110(self):
        """ This test failed due to the maxgap issue on OPTICAL (160 instead 60) on this block
        """
        run_classif('15PXR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        block_ids=[110],
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_15PXR_1(self):
        """ This test succeed over this block
        """
        run_classif('15PXR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        block_ids=[1],
        upload_block=False)

    def test_run_classif_cropland_54VWM_106(self):
        """ This test failed due to the maxgap issue on OPTICAL (61 instead 60)
        on this block (close to coastal area)
        """
        run_classif('54VWM',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17163_20221114214029',
        block_ids=[106],
        upload_block=False)

    def test_run_classif_cropland_43PCM_0(self):
        """ This test failed due to the maxgap issue on OPTICAL (237 instead 60)
        on this block (island case)
        """
        run_classif('43PCM',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_28107_20220921094801',
        block_ids=[0],
        upload_block=False)

    def test_run_classif_cropland_38UPD_120(self):
        """ This test failed due to the maxgap issue on OPTICAL (124 instead 60)
        on this block (land case)
        """
        run_classif('38UPD',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22194_20220908152510',
        block_ids=[120],
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_36UVB_120(self):
        """ Nominal case this block is ok

        UKR tile 2021
        """
        run_classif('36UVB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220929210524',
        block_ids=[120],
        upload_block=False)

    def test_run_classif_cropland_36UVB_43(self):
        """  This test failed due to the maxgap issue on OPTICAL (128 instead 60)
        on this block (land case)

        UKR tile in 2021
        """
        run_classif('36UVB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220929210524',
        block_ids=[43],
        upload_block=False)

    def test_run_classif_cropland_38UQB_1(self):
        """ This test failed due to the maxgap issue on OPTICAL (68 instead 60)
        on this block (land case)
        """
        run_classif('38UQB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22096_20220906224410',
        block_ids=[1],
        upload_block=False)

    def test_run_classif_cropland_37UER_3(self):
        """ This test failed due to the maxgap issue on OPTICAL (123 instead 60)
        on this block (land case)

        UKR tile in 2019
        Same apparently for following blocks: 4,5,6,12,13,14,15,16,17,23,
        27,34,35,37,38,63,66,67,77,78,84,90,91,92,100,101,103,108
        """
        run_classif('37UER',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22194_20220728095352',
        block_ids=[3],
        end_season_year=2019,
        upload_block=False)

    def test_run_classif_cropland_36UWC_72(self):
        """ This test failed due to the maxgap issue on OPTICAL (121 instead 60)
        on this block (land case)

        UKR tile in 2019
        Only this block
        """
        run_classif('36UWC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220728095401',
        block_ids=[72],
        end_season_year=2019,
        upload_block=False)

    def test_run_classif_cropland_36UWA_4(self):
        """ This test failed due to the maxgap issue on OPTICAL (123 instead 60)
        on this block (land case)

        UKR tile in 2019
        Same for block 47 (123 instead 60)
        """
        run_classif('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220728095401',
        block_ids=[4],
        end_season_year=2019,
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_39UXT_60(self):
        """ Must fail but not the case
        """
        run_classif('39UXT',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22096_20220906224410',
        block_ids=[60],
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_43SCB_50(self):
        """ Must fail but not the case
        """
        run_classif('43SCB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_25147_20220918052128',
        block_ids=[50],
        upload_block=False)

    def test_run_classif_cropland_36UWA_4_2022(self):
        """ Nominal case

        UKR tile in 2022
        """
        run_classif('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20221214110523',
        block_ids=[4],
        end_season_year=2022,
        upload_block=False,
        clean=False)

    def test_run_classif_croptype_summer1_36UWA_4_2022(self):
        """ Not tested no full cropland currently

        UKR tile in 2022
        """
        run_classif('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20221214110523',
        block_ids=[4],
        end_season_year=2022,
        upload_block=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        clean=False)

    def test_run_classif_croptype_winter_36UWA_4_2022(self):
        """ Not tested no full cropland currently

        UKR tile in 2022
        """
        run_classif('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20221214110523',
        block_ids=[4],
        end_season_year=2022,
        upload_block=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0],
        clean=False)


    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_winter_40KEC_71(self):
        """ Nominal case with no tir detected

        Island case (Mauritius)
        """
        run_classif('40KEC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535',
        block_ids=[71],
        upload_block=False,
        clean=False,
        tir_csv="./tests/tir_preprocessed_path.csv",
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_run_classif_winter_40KEC_71_no_csv(self):
        """ Nominal case with no tir detected

        Island case (Mauritius)
        """
        run_classif('40KEC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535',
        block_ids=[71],
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])
