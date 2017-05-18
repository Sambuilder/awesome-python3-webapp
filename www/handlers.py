#!/bin/bash env python3
# -*- coding: utf-8 -*-

from coroweb import get, post
from aiohttp import web
from models import User, Blog


@get('/')
async def handler_url_index(request):
    users = await User.findAll()
    user_count = await User.findNumber('id')
    return {
        '__template__': 'test.html',
        'users': users,
        'user_count': user_count
    }


@get('/test')
async def handler_url_test(request):
    return {
        '__template__': 'test.html'
    }


@get('/blog')
async def handler_url_blog(request):
    blogs = await Blog.findAll()
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/api/users')
async def handler_api_users(request):
    # page_index = get_page_index(page)
    num = await User.findNumber('id')
    # p = Page(num, page_index)
    if num == 0:
        return dict(users=())
    users = await User.findAll(orderBy='created at desc')
    return dict(users=users)