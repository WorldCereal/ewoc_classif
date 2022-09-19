"""
    Dummy conftest.py for ewoc_classif.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""
import pytest
import json
import worldcereal.resources.exampleconfigs
import importlib_resources as pkg_resources


@pytest.fixture
def config_ref():
    config_list = ["example_bucketrun_annual_config.json","example_bucketrun_summer1_config.json",
                   "example_bucketrun_summer2_config.json","example_bucketrun_winter_config.json"]
    config_ref_list = {}
    for config_file in config_list:
        data = pkg_resources.open_text(worldcereal.resources.exampleconfigs, config_file)
        data_js = json.load(data)
        data_js["parameters"]["year"]=str(data_js["parameters"]["year"])
        config_name = config_file.split("_")[2]
        config_ref_list[config_name]= data_js
    return config_ref_list

