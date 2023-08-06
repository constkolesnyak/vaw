# VAW


## About

VAW (**V**K **A**PI **W**rapper) is a wrapper for a [wrapper](https://github.com/python273/vk_api) for [VK API](https://vk.com/dev/methods).

I made this mess in high school. It was a lot of fun! Over the years, I've lost all of the cool bots I've made with vaw. Unfortunately, nowadays VK is a "musorskaya kontora", so VK bot is a thing of the past.

The code is pretty bad. I was too much into Haskell at the time and didn't care about cohesion, coupling, SOLID, etc.


## Installation

	pip install vaw


## Usage

	from vaw import log_in, user_by_url

	log_in(VK_LOGIN, VK_PASSWORD)
	user = user_by_url('https://vk.com/nickname_or_id')
	user.send('Hi from vaw!')
