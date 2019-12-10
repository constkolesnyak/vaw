# VAW

VAW (**V**K **A**PI **W**rapper) is a wrapper for a [wrapper](https://github.com/python273/vk_api) for [VK API](https://vk.com/dev/methods).

## Installation

	pip install vaw

## Code example

	from vaw import log_in, user_by_url

	log_in(VK_LOGIN, VK_PASSWORD)
	user = user_by_url('https://vk.com/nickname_or_id')
	user.send('Hi from vaw!')
