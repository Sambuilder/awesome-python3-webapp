#!/bin/bash env python3
# -*- coding: utf-8 -*-

from aiohttp import web
from urllib import parse
from apis import APIError
import functools
import asyncio
import os
import inspect
import logging
logging.basicConfig(level=logging.INFO)

# # 要把一个函数映射为一个URL处理函数，我们先定义@get()


def get(path):
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator


def post(path):
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator


def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY
                      and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError(
                'request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found


# 这样，一个函数通过@get()的装饰就附带了URL信息

# @post('/beijing')   # => urlRequest = post('/beijing')(urlRequest)
# def urlRequest():
#     print(urlRequest.__method__, urlRequest.__route__)

# 定义RequestHandler
# URL处理函数不一定是一个coroutine，因此我们用RequestHandler()来封装一个URL处理函数;
# RequestHandler是一个类，由于定义了__call__()方法，因此可以将其实例视为函数;
# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数;
# 然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求


class RequestHandler(object):

    def __init__(self, app, fn):
        self.__app = app
        self.__func = fn
        self.__has_request_arg = has_request_arg(fn)
        self.__has_var_kw_arg = has_var_kw_arg(fn)
        self.__has_named_kw_args = has_named_kw_args(fn)
        self.__named_kw_args = get_named_kw_args(fn)
        self.__required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None
        # 获取参数
        if self.__has_var_kw_arg or self.__has_named_kw_args or self.__required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self.__has_var_kw_arg and self.__named_kw_args:
                # remove all unnamed kw
                copy = dict()
                for name in self.__named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warn('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self.__has_request_arg:
            kw['request'] = request
        # check required kw
        if self.__required_kw_args:
            for name in self.__required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self.__func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

# 再编写一个add_route函数，用来注册一个URL处理函数


def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__,
                                                ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

# 自动注册handler模块的所有符合条件的函数
# add_route(app, handlers.index) => add_routes(app, 'handlers')
# add_route(app, handlers.blog) => add_routes(app, 'handlers')
# ...


def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())  # import module_name
    else:
        name = module_name[n + 1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)
