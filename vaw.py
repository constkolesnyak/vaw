import vk_api
from funcy import rpartial, compose, str_join
from attrdict import AttrDict
from collections import namedtuple
from functools import lru_cache, partial
from itertools import chain
from contextlib import contextmanager


BASE_VK_URL = 'https://vk.com/'
BIG_NUM_FOR_CHATS_IDS = 2000000000
MAX_POST_COUNT_PER_REQUEST = 100
MAX_COMMENT_COUNT_PER_REQUEST = 100
MAX_GROUP_COUNT_PER_REQUEST = 1000
MAX_FOLLOWERS_COUNT_PER_REQUEST = 1000
MAX_FRIENDS_COUNT_PER_REQUEST = 5000
MAX_SUBSCRS_COUNT_PER_REQUEST = 200
MAX_MESSAGES_COUNT_PER_REQUEST = 200
MAX_GROUP_MEMBERS_COUNT_PER_REQUEST = 1000
MAX_LIKERS_COUNT_PER_REQUEST = 1000


class VkSession:
	def __init__(self, raw_session):
		self.raw_session = raw_session
		self.api = raw_session.get_api()


@lru_cache()
def get_user_session(login, password):
	session = vk_api.VkApi(login, password)
	session.auth()
	return VkSession(session)


@lru_cache()
def get_group_session(token):
	return VkSession(vk_api.VkApi(token=token))


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
def other_main_session(session):
	orig_session = get_main_session()
	set_main_session(session)
	try:
		yield
	except:
		raise
	finally:
		set_main_session(orig_session)


def get_api():
	return _main_session.api


def _get_all_tool(method, count, **params):
	return vk_api.VkTools(get_main_session().raw_session).get_all_iter(method, count, params)


def temp_func_creator(*t):
	return partial(_get_all_tool, *t)


raw_get_posts = temp_func_creator('wall.get', MAX_POST_COUNT_PER_REQUEST)
raw_get_comments = temp_func_creator('wall.getComments', MAX_COMMENT_COUNT_PER_REQUEST)
raw_get_groups = temp_func_creator('groups.get', MAX_GROUP_COUNT_PER_REQUEST)
raw_get_friends = temp_func_creator('friends.get', MAX_FRIENDS_COUNT_PER_REQUEST)
raw_get_subscr_users = compose(  # get raw users who user is subscribed to
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


class VkMessage:
	def __init__(self, info):
		self.info = AttrDict(info)
		self.text = self.info.body
		self.unixtime = self.info.date

	def __repr__(self):
		return f'Message ({self.text[:5]}...)'


def make_attachment(type, owner_id, item_id):
	return f'{type}{owner_id}_{item_id}'


class VkPeer(VkObject):
	def __init__(self, info, spec_peer_id=None):
		super().__init__(info)
		self.peer_id = self.id if spec_peer_id is None else spec_peer_id

	def send(self, message='', attachments=(), forward_messages_ids=()):
		return get_api().messages.send(
			peer_id=self.peer_id,
			message=message,
			attachment=','.join(attachments),
			forward_messages=str_join(',', forward_messages_ids)
		)

	def get_message_history(self, rev=True):
		return map(VkMessage, raw_get_message_history(
			peer_id=self.peer_id,
			rev=not rev
		))

	def set_typing(self):
		get_api().messages.setActivity(
			peer_id=self.peer_id,
			type='typing'
		)


class VkMember(VkPeer):
	def __init__(self, info):
		info = AttrDict(info)

		self.name = info.name
		self.screen_name = info.screen_name
		self.deactivated = info.deactivated

		super().__init__(dict(
			id=info.id,
			url=BASE_VK_URL + self.screen_name
		))

	def __repr__(self):
		return f'{self.name} ({self.url})'

	def post(self, message='', attachments=()):
		return get_api().wall.post(
			owner_id=self.id,
			message=message,
			attachments=','.join(attachments)
		)['post_id']

	def get_posts(self, filter=''):
		return map(VkPost, raw_get_posts(
			owner_id=self.id,
			filter=filter
		))

	def get_posts_by_ids(self, posts_ids):
		return map(VkPost, get_api().wall.getById(
			posts=','.join(f'{self.id}_{post_id}' for post_id in posts_ids)
		))

	def get_post_by_id(self, post_id):
		return next(self.get_posts_by_ids((post_id,)))


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


class VkGroup(VkMember):
	def __init__(self, info):
		super().__init__(_to_member_info(info, 'club'))
		self.info = AttrDict(info)

	def get_members(self, fields='', filter=''):
		return map(VkUser, raw_get_group_members(
			group_id=-self.id,
			fields='screen_name,' + fields,
			filter=filter
		))


def get_group_info(group_id, fields=''):
	return get_api().groups.getById(
		group_id=-group_id,
		fields=fields
	)[0]


group_by_id = compose(VkGroup, get_group_info)


def group_by_url(url, fields=''):
	return group_by_id(member_id_by_url(url), fields)


class VkUser(VkMember):
	def __init__(self, info):
		super().__init__(_to_member_info(info, 'id'))
		self.info = AttrDict(info)

	def get_groups(self, filter='', fields=''):
		return map(VkGroup, raw_get_groups(
			user_id=self.id,
			extended=1,
			filter=filter,
			fields=fields
		))

	def get_friends(self, fields=''):
		return map(VkUser, raw_get_friends(
			user_id=self.id,
			fields='screen_name,' + fields
		))

	def get_subscr_users(self, fields=''):  # get users who user is subscribed to
		return map(VkUser, raw_get_subscr_users(
			user_id=self.id,
			extended=1,
			fields='screen_name,' + fields
		))

	def get_subscrs(self, friends_fields='', groups_fields='', subscr_users_fields=''):
		return chain(
			self.get_groups(fields=groups_fields),
			self.get_friends(fields=friends_fields),
			self.get_subscr_users(fields=subscr_users_fields)
		)

	def get_followers(self, fields=''):
		return map(VkUser, raw_get_followers(
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


user_by_id = compose(VkUser, get_user_info)


def user_by_url(url, fields=''):
	return user_by_id(member_id_by_url(url), fields)


Marked = namedtuple('Marked', 'liked reposted')


class VkPublication(VkObject):
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
		return f'{self.type} ({self.url})'

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
		return get_api().likes.add(**self._useful_publ_info())['likes']

	def unlike(self):
		return get_api().likes.delete(**self._useful_publ_info())['likes']

	def get_likers_ids(self, filter='', friends_only=False):
		return raw_get_likers(
			**self._useful_publ_info(),
			filter=filter,
			friends_only=friends_only
		)

	def repost(self, message='', group=None):
		return get_api().wall.repost(
			object=make_attachment(**self._useful_publ_info()).replace('post', 'wall'),
			message=message,
			group_id='' if group is None else -group.id
		)['post_id']


def _to_publication_info(info, commented_member_id=None, commented_publication_id=None):
	info = AttrDict(info)

	owner_id = info.get('owner_id', commented_member_id)

	if commented_publication_id is None:
		url_end = info.id
	else:
		url_end = f'{commented_publication_id}?reply={info.id}'

	return dict(
		id=info.id,
		url=f'{BASE_VK_URL}wall{owner_id}_{url_end}',
		unixtime=info.date,
		text=info.text,
		owner_id=owner_id,
		type=info.get('post_type', 'comment')
	)


class VkPost(VkPublication):
	def __init__(self, info):
		super().__init__(_to_publication_info(info))

		self.info = AttrDict(info)
		self._to_comment = rpartial(VkComment, self.owner_id, self.id)

	def _useful_post_info(self):
		return dict(
			owner_id=self.owner_id,
			post_id=self.id
		)

	def delete(self):
		return get_api().wall.delete(**self._useful_post_info())

	def get_comments(self, rev=False, need_likes=False):
		return map(self._to_comment, raw_get_comments(
			**self._useful_post_info(),
			preview_length=0,
			sort='desc' if rev else '',
			need_likes=need_likes
		))

	def comment(self, message='', attachments=()):
		return get_api().wall.createComment(
			**self._useful_post_info(),
			message=message,
			attachments=','.join(attachments)
		)['comment_id']

	def pin(self):
		return get_api().wall.pin(**self._useful_post_info())

	def unpin(self):
		return get_api().wall.unpin(**self._useful_post_info())


def post_by_ids(owner_id, post_id):
	return VkPost(get_api().wall.getById(
		posts=f'{owner_id}_{post_id}',
	)[0])


def post_by_url(url):
	return post_by_ids(*map(int, url.split('wall')[-1].split('_')))


class VkComment(VkPublication):
	def __init__(self, info, commented_member_id, commented_publication_id):
		super().__init__(_to_publication_info(info, commented_member_id, commented_publication_id))

		self.info = AttrDict(info)
		self.author_id = self.info.from_id
		self.commented_publication_id = commented_publication_id

	def __eq__(self, other):
		return super().__eq__(other) and self.commented_publication_id == other.commented_publication_id

	def reply(self, message='', attachments=()):
		return get_api().wall.createComment(
			owner_id=self.owner_id,
			post_id=self.commented_publication_id,
			message=message,
			reply_to_comment=self.id,
			attachments=','.join(attachments)
		)['comment_id']

	def delete(self):
		return get_api().wall.deleteComment(
			owner_id=self.owner_id,
			comment_id=self.id
		)


class VkChat(VkPeer):
	def __init__(self, info):
		self.info = AttrDict(info)
		self.title = self.info.title

		super().__init__(
			dict(
				id=self.info.id,
				url=BASE_VK_URL + 'im?sel=c' + str(self.info.id)
			),
			BIG_NUM_FOR_CHATS_IDS + self.info.id
		)

	def retitle(self, title):
		return get_api().messages.editChat(
			chat_id=self.id,
			title=title
		)

	def get_members(self, fields=''):
		return map(VkUser, get_api().messages.getChatUsers(
			chat_id=self.id,
			fields='screen_name,' + fields
		))


def chat_by_id(chat_id):
	return VkChat(get_api().messages.getChat(
		chat_id=chat_id,
	))


def chat_id_by_url(url):
	return int(url.split('c')[-1])


chat_by_url = compose(chat_by_id, chat_id_by_url)
