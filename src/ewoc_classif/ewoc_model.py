import argparse
import json
import logging
from pathlib import Path
import shutil
import sys
from typing import List

from bs4 import BeautifulSoup
import requests

from ewoc_classif import __version__
from ewoc_classif.utils import setup_logging

__author__ = "Mickael Savinaud"
__copyright__ = "CS Group France"
__license__ = "Unlicense"

_logger = logging.getLogger(__name__)

def parse_args(args):
    """Parse command line parameters

    Args:
      args (List[str]): command line parameters as list of strings
          (for example  ``["--help"]``).

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(description="EWoC Classification parser")
    parser.add_argument(
        "--version",
        action="version",
        version=f"ewoc_classif {__version__}",
    )

    parser.add_argument(
        dest="models_dir_root",
        help="Folder storing EWoC models",
        default=None,
        type=Path,
    )

    parser.add_argument(
        "--cropland-models-version",
        dest="cropland_models_version",
        help="Cropland models version",
        type=str,
        default="700",
    )
    parser.add_argument(
        "--croptype-models-version",
        dest="croptype_models_version",
        help="Croptype models version",
        type=str,
        default="720",
    )
    parser.add_argument(
        "--irr-models-version",
        dest="irr_models_version",
        help="Irrigation models version",
        type=str,
        default="420",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)

def download_file(dwnl_url: str, out_dirpath:Path )->Path:
    out_filename = dwnl_url.split("/")[-1]
    response = requests.get(dwnl_url)
    # pylint: disable=no-member
    if response.status_code != requests.codes.ok:
        _logger.error(
            "No downloaded (error_code: %s) for %s!",
            response.status_code,
            dwnl_url,
        )
    out_filepath = out_dirpath / out_filename
    with open(out_filepath, "wb") as dwnled_file:
        dwnled_file.write(response.content)

    _logger.info("Sucess to download %s from %s!", out_filepath, dwnl_url)

    return out_filepath


def get_links(url: str)->List:
    """
    Get urls from a web page
    :param url: web page url
    :return: a list of urls from the web page
    """
    res = requests.get(url)
    try:
        body_text = res.text
        links = []
        soup = BeautifulSoup(body_text, 'html.parser')
        for link_ in soup.find_all('a'):
            link_href = link_.get('href')
            if not ".." in link_href:
                links.append(url+link_href)
        return links
    except:
        _logger.error(res.status_code)

def down_models(cp_url: str,model_dirpath: Path)-> None:
    """
    Download models and update config.json files
    the paths are /models/...
    :param cp_url: VITO's artifactory url
    :param out_dir: Folder to store the models
    :param root_dir: the root dir for the config.json files,
     this need to be the dir where the models will be stored in the container (ex /models/), leave it to None
    :return: None
    """
    cp_links = get_links(cp_url)
    outdir = model_dirpath / "/".join(Path(cp_url).parts[-3:])
    outdir.mkdir(parents=True,exist_ok=True)
    for link in cp_links:
        last_link_elt=link.split("/")[-1]
        if link[-1] == "/":
            area_id = Path(link).parts[-1]
            outdir_area = outdir/area_id
            outdir_area.mkdir(parents=True,exist_ok=True)
            cp_models_links = get_links(link)
            for file in cp_models_links:
                out_filepath = download_file(file, outdir_area)
                if out_filepath.name == "config.json":
                    update_config(out_filepath, model_dirpath)
        elif last_link_elt == "config.json":
            out_filepath = download_file(link, outdir)
            update_config(out_filepath, model_dirpath)
        elif "CatBoost" in link:
            download_file(link, outdir)
        else:
            _logger.warning(f' {link} is not downloaded')
            

def update_config(config_path: Path, root_dir: Path) -> None:
    """
    Update config files. This function will update model paths in the config files
     to match the new relative directories
    :param config_path: Path fo config.json file
    :param root_dir: the base folder where the models are stored, leave to default=None (to get /models)
    :return: None
    """
    with open(config_path,'r') as f:
        data = json.load(f)
    
    data['paths']["modelfile"] = data['paths']["modelfile"].replace("https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models",str(root_dir))
    if data['paths']["parentmodel"] is not None:
        data['paths']["parentmodel"] = data['paths']["parentmodel"].replace("https://artifactory.vgt.vito.be:443/auxdata-public/worldcereal/models",str(root_dir))
    
    with open(config_path, "w") as out:
        json.dump(data, out)
    
    _logger.debug(f"Updated: {config_path}")

def main(args):
    """
    Downlaod VITO's models and create an archive
    :param crop_land_version: AI Model version for cropland (will be the same for OPTICAL only crop models)
    :param croptype_version: AI Model version for croptype
    :param irr_version: AI Model version for irrigation
    :param work_dir: Folder for downloading the models, a "models" folder will be created inside it
    :param outfold: Where the tar.gz will be stored
    :param keep_models: True if you want to keep the uncompressed models, default to False
    :param root_dir: the base folder where the models are stored, leave to default=None (to get /models)
    :return: None
    """

    args = parse_args(args)
    setup_logging(args.loglevel)

    ewoc_model_dirpath = args.models_dir_root / "models"
    if ewoc_model_dirpath.exists():
        shutil.rmtree(ewoc_model_dirpath)
    ewoc_model_dirpath.mkdir(parents=True,exist_ok=True)

    cropland_models_version=args.cropland_models_version
    croptype_models_version=args.croptype_models_version
    irr_models_version=args.irr_models_version

    base_url= "https://artifactory.vgt.vito.be/auxdata-public/worldcereal/models/WorldCerealPixelCatBoost"

    crop_url = f"{base_url}/v{cropland_models_version}/cropland_detector_WorldCerealPixelCatBoost_v{cropland_models_version}-realms/"
    crop_optical_url = f"{base_url}/v{cropland_models_version}/cropland_detector_WorldCerealPixelCatBoost_v{cropland_models_version}-realms-OPTICAL/"
    maize_url = f"{base_url}/v{croptype_models_version}/maize_detector_WorldCerealPixelCatBoost_v{croptype_models_version}/"
    maize_optical_url = f"{base_url}/v{croptype_models_version}/maize_detector_WorldCerealPixelCatBoost_v{croptype_models_version}-OPTICAL/"
    springcereals_url =f"{base_url}/v{croptype_models_version}/springcereals_detector_WorldCerealPixelCatBoost_v{croptype_models_version}/"
    springcereals_optical_url =f"{base_url}/v{croptype_models_version}/springcereals_detector_WorldCerealPixelCatBoost_v{croptype_models_version}-OPTICAL/"
    wintercereals_url = f"{base_url}/v{croptype_models_version}/wintercereals_detector_WorldCerealPixelCatBoost_v{croptype_models_version}/"
    wintercereals_optical_url = f"{base_url}/v{croptype_models_version}/wintercereals_detector_WorldCerealPixelCatBoost_v{croptype_models_version}-OPTICAL/"
    irr_url = f"{base_url}/v{irr_models_version}/irrigation_detector_WorldCerealPixelCatBoost_v{irr_models_version}/"

    urls = [maize_url, maize_optical_url,
            crop_url,crop_optical_url,
            springcereals_url, springcereals_optical_url,
            wintercereals_url,wintercereals_optical_url,
            irr_url]
    for i,url in enumerate(urls):
        _logger.info(f"[{i+1}/{len(urls)}] Downloading models from {url}")
        down_models(url, ewoc_model_dirpath)

def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])

if __name__ == "__main__":
    run()