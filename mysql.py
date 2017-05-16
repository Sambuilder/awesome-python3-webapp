#!/bin/bash env python3
# -*- coding: utf-8 -*-

import orm
import asyncio
from models import User, Blog, Comment

# u = User(id=1, name='Test')
# print(u.id)
# print(u['id'])


async def test(loop):
    await orm.create_pool(loop, user='www-data', host='10.0.0.2', password='www-data', db='awesome')
    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')
    await u.save()
    # r = await User.find(1)
    # r1 = await u.findAll(2)
    # r2 = await u.findNumber()
    # await u.remove()
    # print(r1, r2)

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))

# # 创建实例
# user = User(id=123, name='sam')
# # 存入数据库
# user.insert()
# # 查询所有User对象
# users = User.findAll()
