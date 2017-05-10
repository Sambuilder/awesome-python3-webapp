#!/bin/bash env python3
# -*- coding: utf-8 -*-

from orm import Model, StringField, IntergerField


class User(Model):
    __table__ = 'users'
    id = IntergerField('id', primary_key=True)
    name = StringField('name')

# 注意到定义在User类中的__table__、id和name是类的属性，不是实例的属性;
# 所以，在类级别上定义的属性用来描述User对象和表的映射关系，而实例属性必须通过__init__()方法去初始化，所以两者互不干扰