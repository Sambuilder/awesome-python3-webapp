#!/bin/bash env python3
# -*- coding: utf-8 -*-

import orm
from config import configs
import logging
logging.basicConfig(level=logging.info)
from models import User, Blog
import asyncio


async def init(loop):
    await orm.create_pool(loop=loop, **configs.db)
    # blog = Blog(blog_id='1', user_id='0014944031930000a44b832abe74c2bb2194a36cab06e9c000',
    #             user_name='Test', user_image='00000',
    #             name='Test Blog', summary='Lorem ipsum dolor sit amet,consectetur adipisicing elit,sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
    #             content='I love first blog!')
    user = User(email='test@example3.com', passwd='123456', admin=0, name='test003', image='about:blank')
    await user.save()
    # await blog.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
