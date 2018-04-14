#!/usr/bin/env python3
from setuptools import setup


setup(
	name='vaw',
	version='1.2',
	py_modules=['vaw'],
	install_requires=[
		'vk-api==9.3',
		'funcy==1.10',
		'attrdict==2.0.0',
		'setuptools==39.0.1'
	],
	platforms=['any'],
	python_requires='>=3.6',
	description='This is a high-level wrapper for VK API',
	url='https://github.com/mrbirdman2000/vaw',
	author='mrbirdman2000',
	author_email='kostya.kolesnyak@yandex.ru',
	license='GPL',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Programming Language :: Python :: 3.6',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: GNU General Public License (GPL)',
		'Operating System :: OS Independent',
		'Topic :: Software Development :: Libraries :: Python Modules'
	]
)
