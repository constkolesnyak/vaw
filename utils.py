from .config import I_ID
from .my_vk import *
from funcy import compose
from enum import unique, IntEnum


def id_by_url(url):
	resp = get_api().utils.resolveScreenName(screen_name=url.split('/')[-1])
	return -resp['object_id'] if resp['type'] == 'group' else resp['object_id']


@unique
class Openness(IntEnum):
	public, closed, private = range(3)


user_by_url = compose(user_by_id, id_by_url)
group_by_url = compose(group_by_id, id_by_url)
api_by_token = compose(get_api, get_group_session)


chat_by_url = compose(
	chat_by_id,
	lambda url: url.split('c')[-1]
)


def notify(api, message='Выполнение скрипта завершено', user_id=I_ID):
	api.messages.send(user_id=user_id, message=message)
