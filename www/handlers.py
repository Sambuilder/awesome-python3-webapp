#!/bin/bash env python3
# -*- coding: utf-8 -*-

from coroweb import get, post
from aiohttp import web
from models import User


@get('/')
async def handler_url_index(request):
    users = await User.findAll()
    user_count = await User.findNumber('id')
    return {
        '__template__': 'test.html',
        'users': users,
        'user_count': user_count
    }