#!/bin/bash env python3
# -*- coding: utf-8 -*-

from coroweb import get, post
from aiohttp import web
from models import User, Blog, Comment, next_id
from apis import APIError, APIPermissionError, APIResourceNotFoundError, APIValueError
from aiohttp import web
from config import configs
import time
import json
import hashlib
import re
import logging
logging.basicConfig(level=logging.INFO)


_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


# 计算加密cookie


def user2cookie(user, max_age):
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''

    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError('operation not authorized.')


@get('/')
async def handler_url_index():
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
    users = await User.findAll(orderBy='created_at desc')
    return dict(users=users)


@get('/register')
async def handler_url_register(request):
    return {
        '__template__': 'register.html'
    }


@get('/signin')
async def handler_url_signin(request):
    return {
        '__template__': 'signin.html'
    }


@get('/manage/blogs/create')
async def hanldler_url_manage_blogs_crteate(request):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


@get('/api/blogs/{id}')
async def handler_api_blogid(*, id):
    blog = await Blog.find(id)
    return blog


@get('/blogs/{id}')
async def handler_url_blogid(request, *, id):
    blog = await Blog.find(id)
    comments = await Comment.findAll(where='blog_id=?', args=[id], orderBy='created_at desc')
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

# 密码三次加密，含前端js一次


@post('/api/users')
async def handeler_post_api_users(request, *, email, name, passwd):
    'passwd => sha1(email:123456)'
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIError('passwd')
    users = await User.findAll(where='email=?', args=[email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email,
                passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120'
                % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    # make session cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@post('/api/authenticate')
async def handler_post_api_authenticate(request, *, email, passwd):
    'post:passwd => sha1(email:123456)'
    'database => sha1(uid:passwd)'
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid passwd.')
    users = await User.findAll(where='email=?', args=[email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@post('/api/blogs')
async def handler_post_api_blogs(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name connot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name,
                user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog
