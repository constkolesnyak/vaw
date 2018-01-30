import sys
from .config import I_ID
from .my_vk import get_api
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


def id_by_url(url):
	response = get_api().utils.resolveScreenName(screen_name=url.split('/')[-1])
	return -response['object_id'] if response['type'] == 'group' else response['object_id']


def notify(api, message='Выполнение скрипта завершено', user_id=I_ID):
	api.messages.send(user_id=user_id, message=message)
