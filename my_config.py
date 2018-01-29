from json import load


with open('vk_api_wrap/my_data.json') as f:  # you can change path
	data = load(f)

I_LOGIN = data['login']  # your login,
I_PASSWORD = data['password']  # password
I_ID = data['id']  # and id in vk

try:
	SLAVE_ID = data['slave_id']  # your group's id
	SLAVE_TOKEN = data['slave_token']  # and token
except KeyError:
	pass

try:
	CONCUBINE_ID = data['concubine_id']  # your second group's id
	CONCUBINE_TOKEN = data['concubine_token']  # and token
except KeyError:
	pass
