# -*- coding: utf-8 -*-
""" Test EWoC classif
"""
import os
import unittest

from ewoc_classif.classif import run_classif, EWOC_SUPPORTED_SEASONS, EWOC_CROPTYPE_DETECTOR

class Test_classif(unittest.TestCase):
    def setUp(self):
        self.clean=True
        if os.getenv("EWOC_TEST_DEBUG_MODE") is not None:
            self.clean=False

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_cropland_50HQH_64(self):
        run_classif('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20220920095058',
        block_ids=[64],
        upload_block=False,)

    @unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_summer1_50HQH_64(self):
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
        run_classif('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20220920095058',
        block_ids=[64],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[0])

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

    def test_run_classif_cropland_48MYS_110(self):
        """ Less than 3 off-swath acquisitions found, therefore the block is skip
        """
        run_classif('48MYS',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_8023_20220918052243',
        block_ids=[110],
        upload_block=False)

    def test_run_classif_croptype_summer1_45SVC_99(self):
        """ No cropland pixels, therefore block is write with nodata 255 value
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

    #@unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_summer1_15STU_119_extra_TIR_gap(self):
        """ This test no more failed due to the increase of the maxgap for TIR (300 instead 60)"""
        os.environ['EWOC_COLL_MAXGAP_TIR']='300'
        print(os.environ['EWOC_COLL_MAXGAP_TIR'])
        run_classif('15STU',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_46173_20220823152135',
        block_ids=[119],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

    #@unittest.skipIf(os.getenv("EWOC_TEST_VAL_TEST") is None,"env variable not set")
    def test_run_classif_croptype_summer1_55LBE_1(self):
        """ No cropland pixels, therefore block is write with nodata 255 value
        """
        run_classif('55LBE',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_12046_20220920103952',
        block_ids=[1],
        upload_block=False,
        ewoc_detector=EWOC_CROPTYPE_DETECTOR,
        ewoc_season=EWOC_SUPPORTED_SEASONS[1])

     # EWOC_COLL_MAXGAP_TIR=300 18MYT c728b264-5c97-4f4c-81fe-1500d4c4dfbd_20090_20221027083824 --block-ids 108 --ewoc-detector croptype --ewoc-season summer2