from .config import I_ID
from .my_vk import get_api, user_by_id, group_by_id
from funcy import compose


def id_by_url(url):
	resp = get_api().utils.resolveScreenName(screen_name=url.split('/')[-1])
	return -resp['object_id'] if resp['type'] == 'group' else resp['object_id']


user_by_url = compose(user_by_id, id_by_url)
group_by_url = compose(group_by_id, id_by_url)


def notify(api, message='Выполнение скрипта завершено', user_id=I_ID):
	api.messages.send(user_id=user_id, message=message)
