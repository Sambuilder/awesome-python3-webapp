#!/bin/bash env python3
# -*- coding: utf-8 -*-

from coroweb import get, post
from aiohttp import web


@get('/index')
async def handler_url_index(request):
    body = b'Hello, Index'
    return body
