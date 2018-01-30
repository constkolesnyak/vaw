from json import load


with open('vk_api_wrap/my_data.json') as f:  # you can change path
	data = load(f)

I_LOGIN = data['login']  # your login,
I_PASSWORD = data['password']  # password
I_ID = data['id']  # and id in vk


BASE_VK_URL = 'https://vk.com/'
MAX_POST_COUNT_PER_REQUEST = MAX_COMMENT_COUNT_PER_REQUEST = 100
MAX_GROUP_COUNT_PER_REQUEST = 1000
MAX_FRIENDS_COUNT_PER_REQUEST = 5000
MAX_SUBSCRS_COUNT_PER_REQUEST = 200
