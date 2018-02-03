from enum import IntEnum, unique
import vk_api
from .config import *
from collections import namedtuple
from functools import lru_cache, partial
from itertools import chain
from funcy import rpartial, compose


class ObjDict(dict):  # js-like dict
	def __new__(cls, *args, **kwargs):
		self = dict.__new__(cls, *args, **kwargs)
		self.__dict__ = self
		return self


@lru_cache()
def get_user_session(login=I_LOGIN, password=I_PASSWORD):
	session = vk_api.VkApi(login, password)
	session.auth()
	return session


@lru_cache()
def get_group_session(token):
	return vk_api.VkApi(token=token)


@lru_cache()
def get_api(session=get_user_session()):
	return session.get_api()


def _get_all_tool(method, count, session=get_user_session(), **params):
	return vk_api.VkTools(session).get_all_iter(method, count, params)


rg_creator = lambda *t: partial(_get_all_tool, *t)

raw_get_posts = rg_creator('wall.get', MAX_POST_COUNT_PER_REQUEST)
raw_get_comments = rg_creator('wall.getComments', MAX_COMMENT_COUNT_PER_REQUEST)
raw_get_groups = rg_creator('groups.get', MAX_GROUP_COUNT_PER_REQUEST)
raw_get_friends = rg_creator('friends.get', MAX_FRIENDS_COUNT_PER_REQUEST)
_raw_get_subscrs = rg_creator('users.getSubscriptions', MAX_SUBSCRS_COUNT_PER_REQUEST)  # don't use it
_is_user = lambda info: info['type'] == 'profile'  # don't use it
_only_users = partial(filter, _is_user)  # don't use it
raw_get_subscr_users = compose(_only_users, _raw_get_subscrs)
raw_get_followers = rg_creator('users.getFollowers', MAX_FOLLOWERS_COUNT_PER_REQUEST)

del rg_creator


class VkObject:
	def __init__(self, info):
		info = ObjDict(info)

		self.id = info.id
		self.url = info.url

	def __eq__(self, other):
		return self.id == other.id and type(self) == type(other)


class Member(VkObject):
	def __init__(self, info):
		info = ObjDict(info)

		self.name = info.name
		self.screen_name = info.screen_name
		self.deactivated = info.deactivated  # str or False

		super().__init__(dict(
			id=info.id,
			url=BASE_VK_URL + self.screen_name
		))

	def __lt__(self, other):
		return self.name < other.name

	def __repr__(self):
		return '{} ({})'.format(self.name, self.url)

	def get_posts(self, fields=''):
		return map(Post, raw_get_posts(
			owner_id=self.id,
			fields=fields
		))


def _converted_to_member_info(info, screen_name_prefix):
	info = ObjDict(info)

	if screen_name_prefix == 'club':
		info.id = -abs(info.id)
	else:
		info.name = info.first_name + ' ' + info.last_name

	return dict(
		id=info.id,
		name=info.name,
		screen_name=info.get('screen_name', screen_name_prefix + str(info.id)),
		deactivated=info.get('deactivated', False)
	)


@unique
class Openness(IntEnum):
	public, closed, private = range(3)


class Group(Member):
	def __init__(self, info):
		self.info = ObjDict(info)
		super().__init__(_converted_to_member_info(info, 'club'))


def group_by_id(group_id, fields=''):
	return Group(get_api().groups.getById(
		group_id=-group_id,
		fields=fields
	)[0])


class User(Member):
	def __init__(self, info):
		self.info = ObjDict(info)
		super().__init__(_converted_to_member_info(info, 'id'))

	def get_friends(self, fields=''):
		return map(User, raw_get_friends(
			user_id=self.id,
			fields='screen_name,' + fields
		))

	def get_groups(self, fields=''):
		return map(Group, raw_get_groups(
			user_id=self.id,
			extended=1,
			fields=fields
		))

	def get_subscr_users(self, fields=''):
		return map(User, raw_get_subscr_users(
			user_id=self.id,
			extended=1,  # important!
			fields='screen_name,' + fields
		))

	def get_subscrs(self, fr_fields='', gr_fields='', susr_fields=''):
		return chain(
			self.get_friends(fields=fr_fields),
			self.get_groups(fields=gr_fields),
			self.get_subscr_users(fields=susr_fields)
		)

	def get_followers(self, fields=''):
		return map(User, raw_get_followers(
			user_id=self.id,
			fields='screen_name,' + fields
		))

	def is_online(self):
		return bool(get_api().users.get(
			user_ids=self.id,
			fields='online'
		)[0]['online'])

	def is_app_user(self):
		return bool(get_api().users.isAppUser(user_id=self.id))


def user_by_id(user_id, fields=''):
	return User(get_api().users.get(
		user_ids=user_id,
		fields='screen_name,' + fields
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

	def __eq__(self, other):
		return super().__eq__(other) and self.owner_id == other.owner_id

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


def _converted_to_publication_info(info, commented_member_id=None, commented_publication_id=None):
	info = ObjDict(info)

	owner_id = info.get('owner_id', commented_member_id)
	if commented_publication_id is None:
		url_end = info.id
	else:
		url_end = '{}?reply={}'.format(commented_publication_id, info.id),

	return dict(
		id=info.id,
		url='{}wall{}_{}'.format(BASE_VK_URL, owner_id, url_end),
		unixtime=info.date,
		text=info.text,
		owner_id=owner_id,
		type=info.get('post_type', 'comment')
	)


class Post(Publication):
	def __init__(self, info):
		self.info = ObjDict(info)

		super().__init__(_converted_to_publication_info(info))
		self._to_comment = rpartial(Comment, self.owner_id, self.id)

	def get_comments(self, fields=''):
		return map(self._to_comment, raw_get_comments(
			owner_id=self.owner_id,
			post_id=self.id,
			preview_length=0,
			fields=fields
		))

	def delete(self):
		return get_api().wall.delete(
			owner_id=self.owner_id,
			post_id=self.id
		)


class Comment(Publication):
	def __init__(self, info, commented_member_id, commented_publication_id):
		self.info = ObjDict(info)

		self.commented_member_id = commented_member_id
		self.commented_publication_id = commented_publication_id

		super().__init__(_converted_to_publication_info(info, commented_member_id, commented_publication_id))

	def __eq__(self, other):
		return super().__eq__(other) and self.commented_publication_id == other.commented_publication_id
