from ewoc_classif.utils import generate_config_file
from distutils.util import strtobool
import os


def test_generate_config_file(config_ref):
    csv_dict = {
        "OPTICAL": "/data/worldcereal/s3collections/satio_optical.csv",
        "SAR": "/data/worldcereal/s3collections/satio_sar.csv",
        "TIR": "/data/worldcereal/s3collections/satio_tir.csv",
        "DEM": "s3://ewoc-aux-data/CopDEM_20m",
        "METEO": "/data/worldcereal/s3collections/satio_agera5.csv"
    }
    production_id = "EWoC_admin_12048_20220302203007"
    is_dev = strtobool(os.getenv("EWOC_DEV_MODE", "False"))
    if is_dev:
        cropland_mask_bucket = f"s3://ewoc-prd-dev/{production_id}"
    else:
        cropland_mask_bucket = f"s3://ewoc-prd/{production_id}"
    # Update to cropland mask bucket in reference config
    for config in config_ref:
        if config != "annual":
            config_ref[config]["parameters"]["cropland_mask"] = cropland_mask_bucket

    assert generate_config_file("cropland", "2019", "annual",production_id, "v200", csv_dict) == config_ref["annual"]
    assert generate_config_file("croptype", "2019", "summer1",production_id,"v200", csv_dict) == config_ref["summer1"]
    assert generate_config_file("croptype", "2019", "summer2",production_id, "v200", csv_dict) == config_ref["summer2"]
    assert generate_config_file("croptype", "2019", "winter",production_id, "v200", csv_dict) == config_ref["winter"]