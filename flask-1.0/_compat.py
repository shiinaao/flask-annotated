# -*- coding: utf-8 -*-
"""
    flask._compat
    ~~~~~~~~~~~~~

    Some py2/py3 compatibility support based on a stripped down
    version of six so we don't have to depend on a specific version
    of it.

    :copyright: © 2010 by the Pallets team.
    :license: BSD, see LICENSE for more details.
"""

'''
    flask._compat
    ~~~~~~~~~~~~~
    
    py2/py3兼容性支持基于无版本的 `six`，所以我们不依赖于它特定的版本
    
    create: 2018/06/14
    update: 2018/06/24
        def with_metaclass(meta, *bases):
        这个元类的兼容操作太神了
'''

import sys

PY2 = sys.version_info[0] == 2
_identity = lambda x: x


# 在 Py2,Py3 之间统一类型判断名, 和一些差异操作
if not PY2:
    # Python 3.x
    text_type = str
    string_types = (str,)
    integer_types = (int,)

    iterkeys = lambda d: iter(d.keys())
    itervalues = lambda d: iter(d.values())
    iteritems = lambda d: iter(d.items())

    from inspect import getfullargspec as getargspec
    from io import StringIO

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    # implements_to_string() 是一个装饰器, 下同
    implements_to_string = _identity

else:
    # Python 2.x
    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)

    iterkeys = lambda d: d.iterkeys()
    itervalues = lambda d: d.itervalues()
    iteritems = lambda d: d.iteritems()

    from inspect import getargspec
    from cStringIO import StringIO

    # 没看懂问什么 Python 2.x 中需要这样声明一个函数
    exec('def reraise(tp, value, tb=None):\n raise tp, value, tb')

    def implements_to_string(cls):
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a
    # dummy metaclass for one level of class instantiation that replaces
    # itself with the actual metaclass.
    '''
    用 元类(metaclass) 创建一个 基类(base class)
    这需要一些解释: 基本的想法是做一个 类实例化级别的 dummy metaclass(虚拟元类??)
    用于替换实际使用的 metaclass
    ------------------------------------
    说这么多重点就是, 这是 Py2, Py3 使用 metaclass 的兼容方法
    简单解释为: 元类 meta 继承 bases=(Base1, Base2), 然后实例化出一个 temporary_class, 然后
    temporary_class 再被 user_class 继承, 效果相当于
    ```
    class user_class(Base1, Base2, metaclass=meta):
    ```
    Refer: https://gist.github.com/shiinaao/cc694204bfed9b9c8cc6df0fc9f21911
    '''
    class metaclass(type):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    # 下面这两行是等效的
    # return meta('temporary', bases, {})
    return type.__new__(metaclass, 'temporary_class', (), {})


# Certain versions of pypy have a bug where clearing the exception stack
# breaks the __exit__ function in a very peculiar way.  The second level of
# exception blocks is necessary because pypy seems to forget to check if an
# exception happened until the next bytecode instruction?
#
# Relevant PyPy bugfix commit:
# https://bitbucket.org/pypy/pypy/commits/77ecf91c635a287e88e60d8ddb0f4e9df4003301
# According to ronan on #pypy IRC, it is released in PyPy2 2.3 and later
# versions.
#
# Ubuntu 14.04 has PyPy 2.2.1, which does exhibit this bug.
'''
对 PyPy 解释器 BUG 的兼容处理, 出现在 Ubuntu 14.04 上的 PyPy 2.2.1
已经提交了修复 commit, 此处可跳过
'''
BROKEN_PYPY_CTXMGR_EXIT = False
if hasattr(sys, 'pypy_version_info'):
    class _Mgr(object):
        def __enter__(self):
            return self
        def __exit__(self, *args):
            if hasattr(sys, 'exc_clear'):
                # Python 3 (PyPy3) doesn't have exc_clear
                sys.exc_clear()
    try:
        try:
            with _Mgr():
                raise AssertionError()
        except:
            raise
    except TypeError:
        BROKEN_PYPY_CTXMGR_EXIT = True
    except AssertionError:
        pass
