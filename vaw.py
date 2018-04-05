import vk_api
from funcy import rpartial, compose, str_join
from attrdict import AttrDict
from .config import *
from collections import namedtuple
from functools import lru_cache, partial
from itertools import chain
from contextlib import contextmanager


@lru_cache()
def get_user_session(login, password):
	session = vk_api.VkApi(login, password)
	session.auth()
	return session


@lru_cache()
def get_group_session(token):
	return vk_api.VkApi(token=token)


_main_session = None


def set_main_session(session):
	global _main_session
	_main_session = session


get_main_session = lambda: _main_session


def log_in(login=None, password=None, token=None):
	if token is None:
		session = get_user_session(login, password)
	else:
		session = get_group_session(token)
	set_main_session(session)


@contextmanager
def change_main_session(session):
	orig_session = get_main_session()
	set_main_session(session)
	try:
		yield
	except:
		raise
	finally:
		set_main_session(orig_session)


def get_api(session=None):
	return get_main_session().get_api() if session is None else session.get_api()


def _get_all_tool(method, count, **params):
	return vk_api.VkTools(get_main_session()).get_all_iter(method, count, params)


def temp_func_creator(*t):
	return partial(_get_all_tool, *t)


raw_get_posts = temp_func_creator('wall.get', MAX_POST_COUNT_PER_REQUEST)
raw_get_comments = temp_func_creator('wall.getComments', MAX_COMMENT_COUNT_PER_REQUEST)
raw_get_groups = temp_func_creator('groups.get', MAX_GROUP_COUNT_PER_REQUEST)
raw_get_friends = temp_func_creator('friends.get', MAX_FRIENDS_COUNT_PER_REQUEST)
raw_get_subscr_users = compose(
	partial(filter, lambda info: info['type'] == 'profile'),
	temp_func_creator('users.getSubscriptions', MAX_SUBSCRS_COUNT_PER_REQUEST)
)
raw_get_followers = temp_func_creator('users.getFollowers', MAX_FOLLOWERS_COUNT_PER_REQUEST)
raw_get_message_history = temp_func_creator('messages.getHistory', MAX_MESSAGES_COUNT_PER_REQUEST)
raw_get_group_members = temp_func_creator('groups.getMembers', MAX_GROUP_MEMBERS_COUNT_PER_REQUEST)
raw_get_likers = temp_func_creator('likes.getList', MAX_LIKERS_COUNT_PER_REQUEST)

del temp_func_creator


class VkObject:
	def __init__(self, info):
		info = AttrDict(info)

		self.id = info.id
		self.url = info.url

	def __eq__(self, other):
		return self.id == other.id and type(self) == type(other)


class Message:
	def __init__(self, info):
		self.info = AttrDict(info)
		self.text = self.info.body

	def __repr__(self):
		return f'Message ({self.text[:5]}...)'


def make_attachment(type, owner_id, item_id):
	return f'{type}{owner_id}_{item_id}'


class Peer(VkObject):
	def __init__(self, info, peer_id=None):
		super().__init__(info)
		self.peer_id = self.id if peer_id is None else peer_id

	def send_message(self, message='', attachments=(), forward_messages=()):
		return get_api().messages.send(
			peer_id=self.peer_id,
			message=message,
			attachment=','.join(attachments),
			forward_messages=str_join(',', forward_messages)
		)

	def get_message_history(self):
		return map(Message, raw_get_message_history(peer_id=self.peer_id))

	def set_typing(self):
		get_api().messages.setActivity(
			peer_id=self.peer_id,
			type='typing'
		)


class Member(Peer):
	def __init__(self, info):
		info = AttrDict(info)

		self.name = info.name
		self.screen_name = info.screen_name
		self.deactivated = info.deactivated  # str or False

		super().__init__(dict(
			id=info.id,
			url=BASE_VK_URL + self.screen_name
		))

	def __lt__(self, other):
		return self.name < other.name

	def __hash__(self):
		return abs(self.id)

	def __repr__(self):
		return '{} ({})'.format(self.name, self.url)

	def post(self, message='', attachments=(), friends_only=False, from_group=False, signed=False):
		return get_api().wall.post(
			owner_id=self.id,
			message=message,
			attachments=','.join(attachments),
			friends_only=int(friends_only),
			from_group=int(from_group),
			signed=int(signed)
		)['post_id']

	def get_posts(self, fields=''):
		return map(Post, raw_get_posts(
			owner_id=self.id,
			fields=fields
		))

	def get_posts_by_ids(self, post_ids, fields=''):
		prefix = str(self.id) + '_'
		return map(Post, get_api().wall.getById(
			posts=','.join(prefix + str(post_id) for post_id in post_ids),
			fields=fields
		))

	def get_post_by_id(self, post_id, fields=''):
		return next(self.get_posts_by_ids((post_id,), fields))


def member_id_by_url(url):
	resp = get_api().utils.resolveScreenName(screen_name=url.split('/')[-1])
	return -resp['object_id'] if resp['type'] == 'group' else resp['object_id']


def _to_member_info(info, screen_name_prefix):
	info = AttrDict(info)

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


class Group(Member):
	def __init__(self, info):
		self.info = AttrDict(info)
		super().__init__(_to_member_info(info, 'club'))

	def get_members(self, fields=''):
		return map(User, raw_get_group_members(
			group_id=-self.id,
			fields='screen_name,' + fields
		))


def get_group_info(group_id, fields=''):
	return get_api().groups.getById(
		group_id=-group_id,
		fields=fields
	)[0]


group_by_id = compose(Group, get_group_info)


def group_by_url(url, fields=''):
	return group_by_id(member_id_by_url(url), fields)


class User(Member):
	def __init__(self, info):
		self.info = AttrDict(info)
		super().__init__(_to_member_info(info, 'id'))

	def get_groups(self, fields=''):
		return map(Group, raw_get_groups(
			user_id=self.id,
			extended=1,
			fields=fields
		))

	def get_friends(self, fields=''):
		return map(User, raw_get_friends(
			user_id=self.id,
			fields='screen_name,' + fields
		))

	def get_subscr_users(self, fields=''):
		return map(User, raw_get_subscr_users(
			user_id=self.id,
			extended=1,
			fields='screen_name,' + fields
		))

	def get_subscrs(self, fr_fields='', gr_fields='', susr_fields=''):
		return chain(
			self.get_groups(fields=gr_fields),
			self.get_friends(fields=fr_fields),
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

	def is_friend_of(self, user):
		return user.id in raw_get_friends(user_id=self.id)

	def is_member_of(self, group):
		return bool(get_api().groups.isMember(
			user_id=self.id,
			group_id=-group.id
		))


def get_user_info(user_id, fields=''):
	return get_api().users.get(
		user_ids=user_id,
		fields='screen_name,' + fields
	)[0]


user_by_id = compose(User, get_user_info)


def user_by_url(url, fields=''):
	return user_by_id(member_id_by_url(url), fields)


Marked = namedtuple('Marked', 'is_liked is_reposted')


class Publication(VkObject):
	def __init__(self, info):
		info = AttrDict(info)

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

	def _useful_publ_info(self):
		return dict(
			type=self.type,
			owner_id=self.owner_id,
			item_id=self.id
		)

	def marked_by(self, user):
		marked = get_api().likes.isLiked(
			user_id=user.id,
			**self._useful_publ_info()
		)
		return Marked(bool(marked['liked']), bool(marked['copied']))

	def like(self):
		return get_api().likes.add(**self._useful_publ_info())

	def unlike(self):
		return get_api().likes.delete(**self._useful_publ_info())

	def get_likers_ids(self, friends_only=False):
		return raw_get_likers(
			**self._useful_publ_info(),
			friends_only=int(friends_only)
		)

	def get_reposters_ids(self, friends_only=False):
		return raw_get_likers(
			**self._useful_publ_info(),
			friends_only=int(friends_only),
			filter='copies'
		)

	def repost(self, message='', group=None):
		return get_api().wall.repost(
			object=make_attachment(**self._useful_publ_info()).replace('post', 'wall'),
			message=message,
			group_id='' if group is None else -group.id
		)['post_id']


def _to_publication_info(info, commented_member_id=None, commented_publication_id=None):
	info = AttrDict(info)

	try:
		owner_id = info['to_id']
	except KeyError:
		owner_id = info.get('owner_id', commented_member_id)
	if commented_publication_id is None:
		url_end = info.id
	else:
		url_end = '{}?reply={}'.format(commented_publication_id, info.id)

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
		self.info = AttrDict(info)

		super().__init__(_to_publication_info(info))
		self._to_comment = rpartial(Comment, self.owner_id, self.id)

	def _useful_post_info(self):
		return dict(
			owner_id=self.owner_id,
			post_id=self.id
		)

	def delete(self):
		return get_api().wall.delete(**self._useful_post_info())

	def get_comments(self, fields=''):
		return map(self._to_comment, raw_get_comments(
			**self._useful_post_info(),
			preview_length=0,
			fields=fields
		))

	def comment(self, message='', attachments=()):
		return get_api().wall.createComment(
			**self._useful_post_info(),
			message=message,
			attachments=','.join(attachments)
		)

	def pin(self):
		return get_api().wall.pin(**self._useful_post_info())

	def unpin(self):
		return get_api().wall.unpin(**self._useful_post_info())


def post_by_url(url, fields=''):
	owner, post = url.split('wall')[-1].split('_')
	return Post(get_api().wall.getById(
		posts=owner + '_' + post,
		fields=fields
	)[0])


class Comment(Publication):
	def __init__(self, info, commented_member_id, commented_publication_id):
		self.info = AttrDict(info)

		self.commented_member_id = commented_member_id
		self.commented_publication_id = commented_publication_id

		super().__init__(_to_publication_info(info, commented_member_id, commented_publication_id))

	def __eq__(self, other):
		return super().__eq__(other) and self.commented_publication_id == other.commented_publication_id

	def reply(self, message='', attachments=()):
		return get_api().wall.createComment(
			owner_id=self.commented_member_id,
			post_id=self.commented_publication_id,
			message=message,
			reply_to_comment=self.id,
			attachments=','.join(attachments)
		)

	def delete(self):
		return get_api().wall.deleteComment(
			owner_id=self.commented_member_id,
			comment_id=self.id
		)


class Chat(Peer):
	def __init__(self, info):
		self.info = AttrDict(info)

		super().__init__(
			dict(
				id=self.info.id,
				url=BASE_VK_URL + 'im?sel=c' + str(self.info.id)
			),
			2000000000 + self.info.id
		)

	def retitle(self, new_title):
		return get_api().messages.editChat(
			chat_id=self.id,
			title=new_title
		)

	def get_users(self, fields=''):
		return map(User, get_api().messages.getChatUsers(
			chat_id=self.id,
			fields='screen_name,' + fields
		))


def chat_by_id(chat_id, fields=''):
	return Chat(get_api().messages.getChat(
		chat_id=chat_id,
		fields=fields
	))


def chat_id_by_url(url):
	return int(url.split('c')[-1])


def chat_by_url(url, fields=''):
	return chat_by_id(chat_id_by_url(url), fields)
