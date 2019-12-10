# VAW

VAW (**V**K **A**PI **W**rapper) is a wrapper for a [wrapper](https://github.com/python273/vk_api) for [VK API](https://vk.com/dev/methods).

## Installation

	pip install vaw

## Code example

	from vaw import log_in, user_by_url

	log_in(VK_LOGIN, VK_PASSWORD)
	mrbirdman = user_by_url('https://vk.com/kostyakolesnyak')
	mrbirdman.send('Hi from vaw!')
