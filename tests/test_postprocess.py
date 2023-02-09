# -*- coding: utf-8 -*-
""" Test EWoC postprocessing
"""
import os
import unittest

from ewoc_classif.blocks_mosaic import generate_ewoc_products


class Test_postprocessing(unittest.TestCase):
    def setUp(self):
        self.clean=True
        if os.getenv("EWOC_TEST_DEBUG_MODE") is not None:
            self.clean=False

    def test_run_postprocessing_cropland_50HQH(self):
        """ Test not functional on Ubuntu 20.04 whitout ubuntugis due to gdal version <3.1
        """
        generate_ewoc_products('50HQH',
        'c728b264-5c97-4f4c-81fe-1500d4c4dfbd_3148_20221223132126',
        upload_prd=False,
        clean=self.clean)
