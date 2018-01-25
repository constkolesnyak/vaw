import sys
import requests
from .config import I_ID, BASE_VK_URL
from .my_vk import API, get_api
import logging
from functools import lru_cache
import logging


@lru_cache()
def get_logger(name, level=logging.INFO, file=sys.stdout):
	logger = logging.getLogger(name)
	logger.setLevel(level)
	if isinstance(file, str):
		fh = logging.FileHandler(file)
	else:
		fh = logging.StreamHandler(file)
	formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s (%(asctime)s)')
	fh.setFormatter(formatter)
	logger.addHandler(fh)
	return logger


def url2id(url):
	response = get_api().utils.resolveScreenName(screen_name=url.split('/')[-1])
	return -response['object_id'] if response['type'] == 'group' else response['object_id']


def notice(message='Выполнение скрипта завершено', recourse=True, api_nbr=API.slave):
	if api_nbr == API.slave:
		end = ', мой хозяин!'
	elif api_nbr == API.concubine:
		end = ', мой властелин!'
	else:
		raise ValueError('invalid api_nbr')
	get_api(api_nbr).messages.send(user_id=I_ID, message=message + (end if recourse else ''))


def download_file(url, path):
	with open(path, "wb") as f:
		f.write(requests.get(url).content)
