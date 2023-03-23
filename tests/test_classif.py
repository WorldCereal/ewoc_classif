# -*- coding: utf-8 -*-
""" Test EWoC classif
"""
import os
import unittest

from ewoc_classif.classif import generate_ewoc_block, EWOC_SUPPORTED_SEASONS, EWOC_CROPTYPE_DETECTOR

class TestClassifBase(unittest.TestCase):
    def setUp(self):
        self.clean=True
        if os.getenv("EWOC_TEST_DEBUG_MODE") is not None:
            self.clean=False

class TestClassif50HQH(TestClassifBase):
    def setUp(self):
        super().setUp()
        self.prod_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20221223132126'

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_50HQH_64(self):
        """ Nominal cropland test from ARD
        """
        generate_ewoc_block('50HQH',
        self.prod_id,
        64,
        upload_block=False,
        clean=self.clean,
        use_existing_features=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_croptype_summer1_50HQH_64(self):
        """ Nominal croptype summer1 test from ARD
        """
        generate_ewoc_block('50HQH',
        self.prod_id,
        64,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        upload_block=False,
        clean=self.clean,
        use_existing_features=False)

    def test_generate_ewoc_block_croptype_summer2_50HQH_64(self):
        """ No summer2 for this aez, therefore the block raise an exception
        """
        with self.assertRaises(RuntimeError):
            generate_ewoc_block('50HQH',
            self.prod_id,
            64,
            ewoc_detector=EWOC_CROPTYPE_DETECTOR,
            ewoc_season=EWOC_SUPPORTED_SEASONS[2],
            upload_block=False,
            clean=self.clean,
            use_existing_features=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_croptype_winter_50HQH_64(self):
        """ Nominal croptype winter test from ARD
        """
        generate_ewoc_block('50HQH',
        self.prod_id,
        64,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0],
        upload_block=False,
        clean=self.clean,
        use_existing_features=False)

    def test_generate_ewoc_block_cropland_50HQH_64_from_features(self):
        """ Nominal cropland test from features
        """
        generate_ewoc_block('50HQH',
        self.prod_id,
        64,
        upload_block=False,
        clean=self.clean)

    def test_generate_ewoc_block_croptype_summer1_50HQH_64_from_features(self):
        """ Nominal croptype summer1 test from features
        """
        generate_ewoc_block('50HQH',
        self.prod_id,
        64,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        upload_block=False,
        clean=self.clean,)

    def test_generate_ewoc_block_croptype_summer2_50HQH_64_from_features(self):
        """ No summer2 for this aez, therefore the block raise an exception
        """
        with self.assertRaises(RuntimeError):
            generate_ewoc_block('50HQH',
            self.prod_id,
            64,
            ewoc_detector=EWOC_CROPTYPE_DETECTOR,
            ewoc_season=EWOC_SUPPORTED_SEASONS[2],
            upload_block=False,
            clean=self.clean)

    def test_generate_ewoc_block_croptype_winter_50HQH_64_from_features(self):
        """ Nominal croptype winter test from features
        """
        generate_ewoc_block('50HQH',
        self.prod_id,
        64,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0],
        upload_block=False,
        clean=self.clean)

class TestClassif22NBM(TestClassifBase):
    def setUp(self):
        super().setUp()
        self.prod_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824'

    def test_generate_ewoc_block_cropland_22NBM_13(self):
        """ Less than 3 off-swath acquisitions found, therefore the block is skip
            No features available
        cf. #71
        """
        generate_ewoc_block('22NBM',
        self.prod_id,
        13,
        upload_block=False,
        clean=self.clean)

class TestClassif15STU(TestClassifBase):
    """ Issue with TIR threshold"""
    def setUp(self):
        super().setUp()
        self.prod_id='c728b264-5c97-4f4c-81fe-1500d4c4dfbd_46173_20220823152135'

    def test_generate_ewoc_block_croptype_summer1_15STU_119_from_features(self):
        """ This test succeed due to use of features computed with a threshold to 120"""
        generate_ewoc_block('15STU',
        self.prod_id,
        119,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        upload_block=False,
        clean=self.clean)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_croptype_summer1_15STU_119_with_larger_TIR_gap(self):
        """ This test no more failed due to the increase of the maxgap threshold for TIR
        (120 instead of 60)"""
        os.environ['EWOC_COLL_MAXGAP_TIR']='120'
        print(os.environ['EWOC_COLL_MAXGAP_TIR'])
        generate_ewoc_block('15STU',
        self.prod_id,
        119,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        upload_block=False,
        clean=self.clean,
        use_existing_features=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_croptype_summer1_15STU_119(self):
        """ This test failed due maxgap threshold reached for TIR (64 instead 60)"""
        with self.assertRaises(RuntimeError):
            generate_ewoc_block('15STU',
            self.prod_id,
            119,
            ewoc_detector=EWOC_CROPTYPE_DETECTOR,
            ewoc_season=EWOC_SUPPORTED_SEASONS[1],
            upload_block=False,
            clean=self.clean,
            use_existing_features=False)

class TestClassif(unittest.TestCase):
    def setUp(self):
        self.clean=True
        if os.getenv("EWOC_TEST_DEBUG_MODE") is not None:
            self.clean=False

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_48MYS_1(self):
        """No errors on cropland
        """
        generate_ewoc_block('48MYS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_8023_20220918052243',
        1,
        upload_block=False,
        clean=self.clean)

    def test_generate_ewoc_block_croptype_summer1_45SVC_99(self):
        """ Nominal case: No cropland pixels, therefore block is write with nodata 255 value
        WARNING: No metafeatures write in this case
        """
        generate_ewoc_block('45SVC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_25144_20220921094656',
        99,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        upload_block=False,
        clean=self.clean)

    def test_generate_ewoc_block_croptype_summer1_55LBE_1(self):
        """ No cropland pixels, therefore block is write with nodata 255 value
        """
        generate_ewoc_block('55LBE',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_12046_20220920103952',
        1,
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_01KFS_60(self):
        """ This test failed due to the maxgap issue on SAR (108 instead 60)
        """
        generate_ewoc_block('01KFS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_5049_20220926141536',
        60,
        upload_block=False)

    # TODO: fix the test to succeed
    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_01KFS_60_with_larger_SAR_gap(self):
        """ This test no more failed due to the increase of the maxgap for SAR (120 instead 60)
        """
        os.environ['EWOC_COLL_MAXGAP_SAR']='120'
        generate_ewoc_block('01KFS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_5049_20220926141536',
        60,
        upload_block=False)

    def test_generate_ewoc_block_cropland_15PXR_110(self):
        """ This test failed due to the maxgap issue on OPTICAL (160 instead 60) on this block
        """
        generate_ewoc_block('15PXR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        110,
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_15PXR_1(self):
        """ This test succeed over this block
        """
        generate_ewoc_block('15PXR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_33117_20220823152041',
        1,
        upload_block=False)

    def test_generate_ewoc_block_cropland_54VWM_106(self):
        """ This test failed due to the maxgap issue on OPTICAL (61 instead 60)
        on this block (close to coastal area)
        """
        generate_ewoc_block('54VWM',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17163_20221114214029',
        106,
        upload_block=False)

    def test_generate_ewoc_block_cropland_43PCM_0(self):
        """ This test failed due to the maxgap issue on OPTICAL (237 instead 60)
        on this block (island case)
        """
        generate_ewoc_block('43PCM',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_28107_20220921094801',
        0,
        upload_block=False)

    def test_generate_ewoc_block_cropland_38UPD_120(self):
        """ This test failed due to the maxgap issue on OPTICAL (124 instead 60)
        on this block (land case)
        """
        generate_ewoc_block('38UPD',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22194_20220908152510',
        120,
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_36UVB_120(self):
        """ Nominal case this block is ok

        UKR tile 2021
        """
        generate_ewoc_block('36UVB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220929210524',
        120,
        upload_block=False)

    def test_generate_ewoc_block_cropland_36UVB_43(self):
        """  This test failed due to the maxgap issue on OPTICAL (128 instead 60)
        on this block (land case)

        UKR tile in 2021
        """
        generate_ewoc_block('36UVB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220929210524',
        43,
        upload_block=False)

    def test_generate_ewoc_block_cropland_38UQB_1(self):
        """ This test failed due to the maxgap issue on OPTICAL (68 instead 60)
        on this block (land case)
        """
        generate_ewoc_block('38UQB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22096_20220906224410',
        1,
        upload_block=False)

    def test_generate_ewoc_block_cropland_37UER_3(self):
        """ This test failed due to the maxgap issue on OPTICAL (123 instead 60) on
        this block (land case)

        UKR tile in 2019
        Same apparently for following blocks: 4,5,6,12,13,14,15,16,17,23,27,34,35,37,
        38,63,66,67,77,78,84,90,91,92,100,101,103,108
        """
        generate_ewoc_block('37UER',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22194_20220728095352',
        3,
        end_season_year=2019,
        upload_block=False)

    def test_generate_ewoc_block_cropland_36UWC_72(self):
        """ This test failed due to the maxgap issue on OPTICAL (121 instead 60)
        on this block (land case)

        UKR tile in 2019
        Only this block
        """
        generate_ewoc_block('36UWC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220728095401',
        72,
        end_season_year=2019,
        upload_block=False)

    def test_generate_ewoc_block_cropland_36UWA_4(self):
        """ This test failed due to the maxgap issue on OPTICAL (123 instead 60)
        on this block (land case)

        UKR tile in 2019
        Same for block 47 (123 instead 60)
        """
        generate_ewoc_block('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220728095401',
        4,
        end_season_year=2019,
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_39UXT_60(self):
        """ Must fail but not the case
        """
        generate_ewoc_block('39UXT',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22096_20220906224410',
        60,
        upload_block=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_cropland_43SCB_50(self):
        """ Must fail but not the case
        """
        generate_ewoc_block('43SCB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_25147_20220918052128',
        50,
        upload_block=False)

    def test_generate_ewoc_block_cropland_36UWA_4_2022(self):
        """ Nominal case

        UKR tile in 2022
        """
        generate_ewoc_block('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20221214110523',
        4,
        end_season_year=2022,
        upload_block=False,
        clean=False)

    def test_generate_ewoc_block_croptype_summer1_36UWA_4_2022(self):
        """ Not tested no full cropland currently

        UKR tile in 2022
        """
        generate_ewoc_block('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20221214110523',
        4,
        end_season_year=2022,
        upload_block=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1],
        clean=False)

    def test_generate_ewoc_block_croptype_winter_36UWA_4_2022(self):
        """ Not tested no full cropland currently

        UKR tile in 2022
        """
        generate_ewoc_block('36UWA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20221214110523',
        4,
        end_season_year=2022,
        upload_block=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0],
        clean=False)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_winter_40KEC_71(self):
        """ Nominal case with no tir detected

        Island case (Mauritius)
        """
        generate_ewoc_block('40KEC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535',
        71,
        upload_block=False,
        clean=False,
        tir_csv="./tests/tir_preprocessed_path.csv",
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    #@unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_winter_40KEC_71_no_csv(self):
        """ Tir issue detected: missing B10

        Island case (Mauritius)
        """
        generate_ewoc_block('40KEC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535',
        71,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_summer1_44QPG_11(self):
        """ Nominal case to test new cropcalendar: with new version no more issue
        """
        generate_ewoc_block('44QPG',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_28122_20220916010432',
        11,
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_summer1_45QXF_64(self):
        """ Nominal india case to test new cropcalendar: with new version no more issue

        """
        generate_ewoc_block('45QXF',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_28122_20220916010432',
        64,
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_generate_ewoc_block_summer1_45QVE_72(self):
        """ Nominal india case to test new cropcalendar: with new version no more issue

        """
        generate_ewoc_block('45QVE',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_28122_20220916010432',
        72,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_summer2_45RWH_10(self):
        """ Wrong AEZ detection case: no valid summer2 season found for this tile
        No cropland found due to the new aez id provided by the wrapper => Runtime Error
        """
        generate_ewoc_block('45RWH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_48180_20220916010553',
        10,
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[2])

    def test_generate_ewoc_block_cropland_36TYQ_110_2021_with_features(self):
        """ Using block features cropland case where features exists
        """
        generate_ewoc_block('36TYQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_6136_20220926141543',
        110,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True)

    def test_generate_ewoc_block_summer1_36TYQ_110_2021_with_features(self):
        """ Using block features summer1 when features does not exist
        Log a warning and compute features
        """
        generate_ewoc_block('36TYQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_6136_20220926141543',
        110,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_summer1_36TYQ_14_2021_with_features(self):
        """ Using block features summer1 when features exists
        """
        generate_ewoc_block('36TYQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_6136_20220926141543',
        14,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_summer1_36TYQ_14_2021_with_features_and_upload_block(self):
        """ Using block features summer1 when features exists and
        put upload_block to True to check that features are not uploaded
        """
        generate_ewoc_block('36TYQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_6136_20220926141543',
        14,
        end_season_year=2021,
        upload_block=True,
        clean=True,
        use_existing_features=True,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_summer1_58KHG_71(self):
        """ No cropland available
        """
        generate_ewoc_block('58KHG',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_10033_20220926141527',
        71,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_winter_53UMR_44(self):
        """  No cropland available

        cf. #86 if error
        """
        generate_ewoc_block('53UMR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17169_20220912005510',
        44,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_cropland_01gem_110(self):
        """ Case where there is no SAR data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('01GEM',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3159_20221123011519',
        0,
        end_season_year=2021,
        upload_block=False,
        clean=False,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        tir_csv="/home/rbuguetd/dev/ewoc_classif/tests/tir_preprocessed_path.csv",
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_01gel_110(self):
        """ Case where there is no SAR data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('01GEL',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3159_20221123011519',
        0,
        end_season_year=2021,
        upload_block=False,
        clean=False,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        tir_csv="/home/rbuguetd/dev/ewoc_classif/tests/tir_preprocessed_path.csv",
        use_existing_features=True)


    def test_generate_ewoc_block_cropland_12qvf_109(self):
        """ Case where there are no TIR data (but there are SAR and OPTICAL)
        Incomplete collection `SAR`: got a collection size of 0 which is less
        than the threshold of 2
        blocks 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
        19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
        38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56,
        57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76,
        79, 80, 81, 82, 83, 84, 85, 86, 87, 94, 95, 96, 97, 98, 109
        """
        generate_ewoc_block('12QVF',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_39128_20221123011520',
        98,
        end_season_year=2021,
        upload_block=False,
        clean=False,
        tir_csv="/home/rbuguetd/dev/ewoc_classif/tests/tir_preprocessed_path.csv",
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_12qwf_110(self):
        """Case where there is no SAR data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('12QWF',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_39128_20221123011520',
        0,
        end_season_year=2021,
        upload_block=False,
        clean=False,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        tir_csv="/home/rbuguetd/dev/ewoc_classif/tests/tir_preprocessed_path.csv",
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_27put_110(self):
        """ Case where there is no SAR data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('27PUT',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_42131_20221123011520',
        110,
        end_season_year=2021,
        upload_block=False,
        clean=False,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        tir_csv="/home/rbuguetd/dev/ewoc_classif/tests/tir_preprocessed_path.csv",
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_27vvl_112(self):
        """Incomplete collection `OPTICAL`: got a value of 152 days for `gapend` which
        exceeds the threshold of 60
        blocks 112
        """
        generate_ewoc_block('27VVL',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_37188_20221114214022',
        112,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_28weu_20(self):
        """Incomplete collection `OPTICAL`: got a value of 169 days for `maxgap` which
        exceeds the threshold of 60
        blocks 20
        """
        generate_ewoc_block('28WEU',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_37188_20221114214022',
        20,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_29vnk_15(self):
        """Incomplete collection `OPTICAL`: got a value of 186 days for `gapstart` which
        exceeds the threshold of 60
        blocks 15
        """
        generate_ewoc_block('29VNK',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_37187_20221114214133',
        15,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_29vpk_58(self):
        """Less than 3 off-swath acquisitions found (missing 67 blocks)
        blocks 58
        """
        generate_ewoc_block('29VPK',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_37187_20221114214133',
        58,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_30vuq_71(self):
        """Less than 3 off-swath acquisitions found (missing 68 blocks)
        blocks 71
        """
        generate_ewoc_block('30VUQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_37187_20221114214133',
        71,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_54vuj_110(self):
        """Case where there is no SAR, TIR and OPTICAL data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('54VUJ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17169_20221123011519',
        110,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        use_existing_features=True)
#tir_csv="/home/rbuguetd/dev/ewoc_classif/tests/tir_preprocessed_path.csv",
#optical_csv="/home/rbuguetd/dev/ewoc_classif/tests/optical_preprocessed_path.csv",

    def test_generate_ewoc_block_cropland_54vvj_110(self):
        """Case where there is no SAR, TIR and OPTICAL data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('54VVJ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17169_20221123011519',
        110,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        use_existing_features=True)

    def test_generate_ewoc_block_cropland_54vvk_110(self):
        """Case where there is no SAR, TIR and OPTICAL data at all, raise an error in VITO processor
        on the wc collection because there are 0 data.
        """
        generate_ewoc_block('54VVK',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17169_20221123011519',
        110,
        end_season_year=2021,
        upload_block=False,
        clean=True,
        sar_csv="/home/rbuguetd/dev/ewoc_classif/tests/sar_preprocessed_path.csv",
        use_existing_features=True)

    def test_generate_ewoc_block_summer1_47nla_39(self):
        """Incomplete collection `SAR`: got a collection size of 0 which is less
        than the threshold of 2.
        blocks 3, 4, 5, 6, 7, 15, 16, 17, 18, 27, 28, 38, 39
        """
        generate_ewoc_block('47NLA',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_8023_20220918052243',
        4,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_summer1_53unr_116(self):
        """ Incomplete collection `SAR`: got a value of 124 days for `gapstart` which
        exceeds the threshold of 60.
        blocks 54, 61, 65, 94, 95, 107, 116, 117, 118, 120
        """
        generate_ewoc_block('53UNR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17169_20220912005510',
        116,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_summer2_18mys_37(self):
        """Incomplete collection `TIR`: got a collection size of 1
        which is less than the threshold of 2
        blocks 17, 37, 38, 39, 47, 48, 49, 50, 52, 53, 63, 64
        """
        generate_ewoc_block('18MYS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        37,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[2])

    def test_generate_ewoc_block_summer2_18mzt_82(self):
        """Incomplete collection `TIR`: got a collection size of 1
        which is less than the threshold of 2
        blocks 82
        """
        generate_ewoc_block('18MZT',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        82,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[2])

    def test_generate_ewoc_block_winter_53unr_54(self):
        """Incomplete collection `SAR`: got a collection size of 0 which is less
        than the threshold of 2.
        blocks 54, 61, 65, 94, 95, 107, 116, 117, 118, 120
        """
        generate_ewoc_block('53UNR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_17169_20220912005510',
        54,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_winter_40kec_17(self):
        """ewoc-ard/c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535/TIR/40/K/EC/2021-
        /20210513/LC08_L1T_20210513T235959_15207402T1_40KEC-
        /LC08_L2SP_20210513T235959_15207402T1_40KEC_B10.tif does not exist
        does not exist in the file system, and is not recognized as a supported dataset name.
        """
        generate_ewoc_block('40KEC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535',
        17,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_summer1_40kec_17(self):
        """ewoc-ard/c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535/TIR/40/K/EC/2021-
        /20210206/LC08_L1T_20210206T235959_15207402T1_40KEC-
        /LC08_L2SP_20210206T235959_15207402T1_40KEC_B10.tif'
        does not exist in the file system, and is not recognized as a supported dataset name.

        """
        generate_ewoc_block('40KEC',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_9026_20220926141535',
        17,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    def test_generate_ewoc_block_winter_17mmq_32(self):
        """Incomplete collection `SAR`: got a value of 131 days for `gapend` which
        exceeds the threshold of 60.
        blocks 32, 41, 42, 43, 52, 53 54, 65
        """
        generate_ewoc_block('17MMQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        32,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_winter_17mmr_117(self):
        """Incomplete collection `SAR`: got a value of 131 days for `gapend` which
        exceeds the threshold of 60.
        blocks 117
        """
        generate_ewoc_block('17MMR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        117,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_winter_17mnp_002(self):
        """Incomplete collection `SAR`: got a value of 131 days for `gapend` which
        exceeds the threshold of 60.
        blocks 2, 3, 4, 10, 12, 13, 14, 15, 25, 26, 54, 64, 65, 75, 76, 86, 87, 96, 97, 98, 109
        """
        generate_ewoc_block('17MNP',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        2,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_winter_17mnq_112(self):
        """Incomplete collection `SAR`: got a value of 131 days for `gapend` which
        exceeds the threshold of 60.
        blocks [3;10], [15;22], 24, [26, 59], 62, 63, 64, 65, 69, 70, 73, 74, 75, 76, 79, 80,
        81, 85, 86, 87, 90, 91 92, 97, 98, 100, 101, 102, 103, 108, 109, 112, 113, 114, 120
        """
        generate_ewoc_block('17MNQ',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        112,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_winter_17mnr_004(self):
        """Incomplete collection `SAR`: got a value of 131 days for `gapend` which
        exceeds the threshold of 60.
        blocks 4, 5, 6, 7, 8, 9, 14, 15, 16, 17, 18, 20, 21, 25, 26, 27, 31, 32,
        36, 37, 39, 40, 41, 42, 43, 46, 47, 48, 49, 50, 51, 52, 53, 54, 60, 61, 62,
        63, 64, 65, 71, 72, 73, 74, 75, 76, 80, 81, 82, 83, 84, 85, 86, 87, 88, 91, 92,
        93, 94, 95, 96, 97, 98, 99, 102, 103, 104, 105, 106, 107, 108, 109, 113, 115,
        116, 117, 118, 119, 120
        """
        generate_ewoc_block('17MNR',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824',
        4,
        upload_block=False,
        clean=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

    def test_generate_ewoc_block_cropland_36UVB_43(self):
        """  Test upload_log parameter
        """
        generate_ewoc_block('36UVB',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_22190_20220929210524',
        43,
        upload_block=True,
        upload_log=False)