#!/bin/bash env python3
# -*- coding: utf-8 -*-

# 创建连接池
# 我们需要创建一个全局的连接池，每个HTTP请求都可以从连接池中直接获取数据库连接；
# 使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用；
# 连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务

import asyncio
import aiomysql
import logging
logging.basicConfig(level=logging.INFO)


def log(sql, args):
    logging.info('SQL: %s (Args: %s)' % (sql, args))


async def create_pool(loop, **kw):
    logging.info('create database connection pool')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', '10.0.0.2'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop)


# Select
# 要执行SELECT语句，用select函数执行，需要传入SQL语句和SQL参数


async def select(sql, args, size=None):
    log(sql, args)
    with (await __pool) as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
        await cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs


# SQL语句的占位符是?，而MySQL的占位符是%s，select()函数在内部自动替换;
# 注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
# 注意到yield from将调用一个子协程（也就是在一个协程中调用另一个协程）并直接获得子协程的返回结果。
# 如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录

# Insert, Update, Delete
# 要执行INSERT、UPDATE、DELETE语句，可以定义一个通用的execute()函数；
# 因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数

# execute()函数和select()函数所不同的是，cursor对象不返回结果集，而是通过rowcount返回结果数
async def execute(sql, args):
    log(sql, args)
    with (await __pool) as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return affected

# ORM
# 有了基本的select()和execute()函数，我们就可以开始编写一个简单的ORM了。
# 设计ORM需要从上层调用者角度来设计。
# 我们先考虑如何定义一个User对象，然后把数据库表users和它关联起来。
# 以及Field和各种Field子类


class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 映射varchar的StringField
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class IntergerField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='bigint(100)'):
        super().__init__(name, ddl, primary_key, default)

# 注意到Model只是一个基类，如何将具体的子类如User的映射信息读取出来呢？答案就是通过metaclass：ModelMetaclass

# 这样，任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中


class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise RuntimeError(
                            'Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))

        def create_args_string(len):
            return ', '.join(['?'] * len)

        attrs['__mapping__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主属性外的属性名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (
            primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__selectNumber__'] = 'select count(`%s`) from `%s`' % (
            primaryKey, tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
            tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
            tableName, ', '.join(
                map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)),
            primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (
            tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


# Model从dict继承，所以具备所有dict的功能，同时又实现了特殊方法__getattr__()和__setattr__()，因此又可以像引用普通字段那样写
# user['id'] => 123
# user.id => 123
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s:%s' %
                              (key, str(value)))
        return value

    # 然后，我们往Model类添加class方法，就可以让所有子类调用class方法
    # user = yield from User.find(1)
    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        # => Model(self,**{'id':1, 'name':'Test'})  =>  返回一个Model对象，**args是这个**dict
        return cls(**rs[0])

    # 根据WHERE条件查找
    async def findAll(self, size=None):
        args = list(map(self.getValueOrDefault, self.__fields__))
        rs = await select('%s where %s' %
                          (self.__select__, ' and '.join(list(map(lambda f: '`%s`=?' % f, self.__fields__)))), args, size)
        return rs

    async def findNumber(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        rs = await select('%s where %s' % (self.__selectNumber__, ' and '.join(list(map(lambda f: '`%s`=?' % f, self.__fields__)))), args)
        return list(rs[0].values())[0]

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        # logging.info(args)
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows %s' % rows)

    async def update(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update record: affected rows %s' % rows)

    async def remove(self):
        args = self.getValue(self.__primary_key__)
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to delete record: affected rows %s' % rows)
