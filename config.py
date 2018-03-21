from json import load


with open('vk_api_wrap/account_data.json') as f:  # you can change path
	data = load(f)

I_LOGIN = data['login']  # your login (str),
I_PASSWORD = data['password']  # password (str)
I_ID = data['id']  # and id (int) in vk


BASE_VK_URL = 'https://vk.com/'
MAX_POST_COUNT_PER_REQUEST = MAX_COMMENT_COUNT_PER_REQUEST = 100
MAX_GROUP_COUNT_PER_REQUEST = MAX_FOLLOWERS_COUNT_PER_REQUEST = 1000
MAX_FRIENDS_COUNT_PER_REQUEST = 5000
MAX_SUBSCRS_COUNT_PER_REQUEST = 200
MAX_MESSAGES_COUNT_PER_REQUEST = 200
