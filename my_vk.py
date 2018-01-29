from enum import IntEnum, unique
import vk_api
from .my_config import *
from .vk_config import *
from collections import namedtuple
from functools import lru_cache, partial
from itertools import chain
from funcy import rpartial


class ObjDict(dict):  # js-like dict
	def __new__(cls, *args, **kwargs):
		self = dict.__new__(cls, *args, **kwargs)
		self.__dict__ = self
		return self


API = IntEnum('API', 'i slave concubine')


@lru_cache()
def get_user_session(login=I_LOGIN, password=I_PASSWORD):
	session = vk_api.VkApi(login, password)
	session.auth()
	return session


@lru_cache()
def get_group_session(token=SLAVE_TOKEN):
	return vk_api.VkApi(token=token)


@lru_cache()
def get_api(api_nbr=API.i):
	if api_nbr == API.i:
		return get_user_session().get_api()
	elif api_nbr == API.slave:
		token = SLAVE_TOKEN
	elif api_nbr == API.concubine:
		token = CONCUBINE_TOKEN
	else:
		raise ValueError('invalid api_nbr')
	return get_group_session(token).get_api()


def _get_all_tool(method, count, session=get_user_session(), **params):
	return vk_api.VkTools(session).get_all_iter(method, count, params)


rg_creator = lambda *t: partial(_get_all_tool, *t)

raw_get_posts = rg_creator('wall.get', MAX_POST_COUNT_PER_REQUEST)
raw_get_comments = rg_creator('wall.getComments', MAX_COMMENT_COUNT_PER_REQUEST)
raw_get_groups = rg_creator('groups.get', MAX_GROUP_COUNT_PER_REQUEST)
raw_get_friends = rg_creator('friends.get', MAX_FRIENDS_COUNT_PER_REQUEST)

del rg_creator


class VkObject:
	def __init__(self, info):
		info = ObjDict(info)

		self.id = info.id
		self.url = info.url

	def __eq__(self, other):
		if type(self) != type(other):
			return False
		if isinstance(self, Publication):
			return self.id == other.id and self.owner_id == other.owner_id
		return self.id == other.id


class Member(VkObject):
	def __init__(self, info):
		info = ObjDict(info)

		self.name = info.name
		self.screen_name = info.screen_name
		self.deactivated = info.deactivated  # False or str

		super().__init__(dict(
			id=info.id,
			url=BASE_VK_URL + self.screen_name
		))

	def __lt__(self, other):
		return self.name < other.name

	def __repr__(self):
		return '{} ({})'.format(self.name, self.url)

	def delete_post(self, post_id):
		get_api().wall.delete(
			owner_id=self.id,
			post_id=post_id
		)

	def get_posts(self):
		return map(Post, raw_get_posts(owner_id=self.id))


def _converted_member_info(raw_info, screen_name_prefix):
	if hasattr(raw_info, 'name'):
		name = raw_info.name  # group
		raw_info.id = -abs(raw_info.id)
	else:
		name = raw_info.first_name + ' ' + raw_info.last_name  # user

	return dict(
		id=raw_info.id,
		name=name,
		screen_name=raw_info.get('screen_name', raw_info.get('domain', screen_name_prefix + str(raw_info.id))),
		deactivated=raw_info.get('deactivated', False)
	)


@unique
class Openness(IntEnum):
	public, closed, private = range(3)


class Group(Member):
	def __init__(self, raw_info):
		super().__init__(_converted_member_info(ObjDict(raw_info), 'club'))


def group_by_id(group_id):
	return Group(get_api().groups.getById(group_id=-group_id)[0])


class User(Member):
	def __init__(self, raw_info):
		super().__init__(_converted_member_info(ObjDict(raw_info), 'id'))

	def get_groups(self):
		return map(Group, raw_get_groups(user_id=self.id, extended=1))

	def get_friends(self):
		return map(User, raw_get_friends(user_id=self.id, fields='domain'))

	def get_subscr_users(self):
		return map(user_by_id, get_api().users.getSubscriptions(
			user_id=self.id
		)['users']['items'])

	def get_subscrs(self):
		return chain(
			self.get_friends(),
			self.get_groups(),
			self.get_subscr_users()
		)

	def is_online(self):
		return bool(get_api().users.get(
			user_ids=self.id,
			fields='online'
		)[0]['online'])


def user_by_id(user_id):
	return User(get_api().users.get(
		user_ids=user_id,
		fields='screen_name'
	)[0])


Marked = namedtuple('Marked', 'is_liked is_reposted')


class Publication(VkObject):
	def __init__(self, info):
		info = ObjDict(info)

		self.unixtime = info.unixtime
		self.text = info.text
		self.owner_id = info.owner_id
		self.type = info.type

		super().__init__(dict(
			id=info.id,
			url=info.url
		))

	def __repr__(self):
		return '{} ({})'.format(self.type, self.url)

	def marked_by(self, user_id):
		marked = get_api().likes.isLiked(
			user_id=user_id,
			type=self.type,
			owner_id=self.owner_id,
			item_id=self.id
		)
		return Marked(bool(marked['liked']), bool(marked['copied']))


class Post(Publication):
	def __init__(self, raw_info):
		raw_info = ObjDict(raw_info)

		super().__init__(dict(
			id=raw_info.id,
			url=BASE_VK_URL + 'wall{}_{}'.format(raw_info.owner_id, raw_info.id),
			owner_id=raw_info.owner_id,
			unixtime=raw_info.date,
			text=raw_info.text,
			type=raw_info.post_type
		))

		self._to_comment = rpartial(Comment, self.owner_id, self.id)

	def get_comments(self):
		return map(self._to_comment, raw_get_comments(
			owner_id=self.owner_id,
			post_id=self.id,
			preview_length=0
		))


class Comment(Publication):
	def __init__(self, raw_info, commented_member_id, commented_publication_id):
		raw_info = ObjDict(raw_info)

		self.commented_member_id = commented_member_id
		self.commented_publication_id = commented_publication_id

		super().__init__(dict(
			id=raw_info.id,
			url=BASE_VK_URL + 'wall{}_{}?reply={}'.format(commented_member_id, commented_publication_id, raw_info.id),
			owner_id=commented_member_id,
			unixtime=raw_info.date,
			text=raw_info.text,
			type='comment'
		))
