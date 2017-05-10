#!/bin/bash env python3
# -*- coding: utf-8 -*-

import orm
import asyncio
from models import User

# u = User(id=1, name='Test')
# print(u.id)
# print(u['id'])


async def test(loop):
    await orm.create_pool(loop, user='root', host='10.0.0.2', password='root@nse', db='test')
    u = User(id=1, name='Test')
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
