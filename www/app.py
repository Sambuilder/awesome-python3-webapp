#!/bin/bahs env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
import time
from datetime import datetime

from aiohttp import web

from coroweb import add_routes, add_static

logging.basicConfig(level=logging.INFO)


# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理;
# 一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回;
# middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方;
# 例如，一个记录URL日志的logger可以简单定义如下


async def logger_factory(app, handler):
    async def logger(request):
        # 记录日志
        logging.info('Request: %s %s' % (request.method, request.path))
        # 继续处理请求
        return (await handler(request))
    return logger

# response这个middleware把返回值转换为web.Response对象再返回，以保证满足aiohttp的要求


async def response_factory(app, handler):
    async def response(request):
        # 处理结果
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.conten_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response()
    return response


async def init(loop):
    app = web.Application(loop=loop, middlewares=(logger_factory, response_factory))
    # init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    # app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000....')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
