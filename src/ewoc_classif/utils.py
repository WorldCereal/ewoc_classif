import logging

import requests

_logger = logging.getLogger(__name__)


def notify_vdm(stac_json, endpoint_url ="endpoint_url"):
    """
    Notify the VDM that a new ewoc product is available
    This function will send a post request to the VDM REST API
    :param stac_json: Json file or dictionary, output of the classifier
    :param url: VDM REST API endpoint url
    :return: REST API status code, 200: all good
    """
    response = requests.post(url = endpoint_url, json=stac_json)
    status_code = response.status_code
    if  status_code == 200:
        _logger.info('Successful notification to VDM, well done!')
    else:
        _logger.error(f'Error for VDM notification. Error code: {status_code}')
    return status_code