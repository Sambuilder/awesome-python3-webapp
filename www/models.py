#!/bin/bash env python3
# -*- coding: utf-8 -*-

from orm import Model, StringField, IntergerField, BooleanField, FloatField, TextField
import time
import uuid

'''
Models for user, blog, comment.
'''


def next_id():
    return '%015d%s000' % (int(time.time()) * 1000, uuid.uuid4().hex)

# 注意到定义在User类中的__table__、id和name是类的属性，不是实例的属性;
# 所以，在类级别上定义的属性用来描述User对象和表的映射关系，而实例属性必须通过__init__()方法去初始化，所以两者互不干扰


class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_images = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)

# 在编写ORM时，给一个Field增加一个default参数可以让ORM自己填入缺省值，非常方便;
# 并且，缺省值可以作为函数对象传入，在调用save()时自动计算;
# 例如，主键id的缺省值是函数next_id，创建时间created_at的缺省值是函数time.time，可以自动设置当前日期和时间;
# 日期和时间用float类型存储在数据库中，而不是datetime类型;
# 这么做的好处是不必关心数据库的时区以及时区转换问题，排序非常简单，显示的时候，只需要做一个float到str的转换，也非常容易。
