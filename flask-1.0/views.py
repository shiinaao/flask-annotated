# -*- coding: utf-8 -*-
"""
    flask.views
    ~~~~~~~~~~~

    This module provides class-based views inspired by the ones in Django.

    :copyright: © 2010 by the Pallets team.
    :license: BSD, see LICENSE for more details.
"""

'''
    flask.views
    ~~~~~~~~~~~

    模块提供了基于类的 View 实现, 这受 Django 所启发    
    
    create: 2018/06/24
'''

from .globals import request
from ._compat import with_metaclass


# frozenset 是一个不可修改的 set 类型
http_method_funcs = frozenset(['get', 'post', 'head', 'options',
                               'delete', 'put', 'trace', 'patch'])


class View(object):
    """Alternative way to use view functions.  A subclass has to implement
    :meth:`dispatch_request` which is called with the view arguments from
    the URL routing system.  If :attr:`methods` is provided the methods
    do not have to be passed to the :meth:`~flask.Flask.add_url_rule`
    method explicitly::

        class MyView(View):
            methods = ['GET']

            def dispatch_request(self, name):
                return 'Hello %s!' % name

        app.add_url_rule('/hello/<name>', view_func=MyView.as_view('myview'))

    When you want to decorate a pluggable view you will have to either do that
    when the view function is created (by wrapping the return value of
    :meth:`as_view`) or you can use the :attr:`decorators` attribute::

        class SecretView(View):
            methods = ['GET']
            decorators = [superuser_required]

            def dispatch_request(self):
                ...

    The decorators stored in the decorators list are applied one after another
    when the view function is created.  Note that you can *not* use the class
    based decorators since those would decorate the view class and not the
    generated view function!
    """

    #: A list of methods this view can handle.
    methods = None

    #: Setting this disables or force-enables the automatic options handling.
    # 设置此选项禁用或强制开启自动 options 处理
    provide_automatic_options = None

    #: The canonical way to decorate class-based views is to decorate the
    #: return value of as_view().  However since this moves parts of the
    #: logic from the class declaration to the place where it's hooked
    #: into the routing system.
    #:
    #: You can place one or more decorators in this list and whenever the
    #: view function is created the result is automatically decorated.
    #:
    #: .. versionadded:: 0.8
    decorators = ()

    def dispatch_request(self):
        """Subclasses have to override this method to implement the
        actual view function code.  This method is called with all
        the arguments from the URL rule.
        """
        raise NotImplementedError()

    # 将类转换为可在路由系统中实际使用的 view 函数
    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        """Converts the class into an actual view function that can be used
        with the routing system.  Internally this generates a function on the
        fly which will instantiate the :class:`View` on each request and call
        the :meth:`dispatch_request` method on it.

        The arguments passed to :meth:`as_view` are forwarded to the
        constructor of the class.
        """
        def view(*args, **kwargs):
            self = view.view_class(*class_args, **class_kwargs)
            return self.dispatch_request(*args, **kwargs)

        if cls.decorators:
            view.__name__ = name
            view.__module__ = cls.__module__
            # 装饰器依次被调用装饰当前 view
            for decorator in cls.decorators:
                view = decorator(view)

        # We attach the view class to the view function for two reasons:
        # first of all it allows us to easily figure out what class-based
        # view this thing came from, secondly it's also used for instantiating
        # the view class so you can actually replace it with something else
        # for testing purposes and debugging.
        view.view_class = cls
        view.__name__ = name
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.methods = cls.methods
        view.provide_automatic_options = cls.provide_automatic_options
        return view


class MethodViewType(type):
    """Metaclass for :class:`MethodView` that determines what methods the view
    defines.
    """

    def __init__(cls, name, bases, d):
        super(MethodViewType, cls).__init__(name, bases, d)

        '''将 View 类中实现的 method 的大写形式添加到 `__dict__['methods']` 中
        ```
        class CounterAPI(MethodView):
            def get(self):
                return session.get('counter', 0)
        counter = CounterAPI()
        ```
        结果就是 counter.methods = {'GET'}
        '''
        if 'methods' not in d:
            methods = set()

            for key in http_method_funcs:
                if hasattr(cls, key):
                    methods.add(key.upper())

            # If we have no method at all in there we don't want to add a
            # method list. This is for instance the case for the base class
            # or another subclass of a base method view that does not introduce
            # new methods.
            if methods:
                cls.methods = methods


'''
with_metaclass 只是对 Py2,Py3 中 MetaClass 的兼容实现, 效果相当于
```
class MethodView(View, metaclass=MethodViewType):
```
'''
class MethodView(with_metaclass(MethodViewType, View)):
    """A class-based view that dispatches request methods to the corresponding
    class methods. For example, if you implement a ``get`` method, it will be
    used to handle ``GET`` requests. ::

        class CounterAPI(MethodView):
            def get(self):
                return session.get('counter', 0)

            def post(self):
                session['counter'] = session.get('counter', 0) + 1
                return 'OK'

        app.add_url_rule('/counter', view_func=CounterAPI.as_view('counter'))
    """
    '''
    一个基于类的 View, 它将 request methods 发送给相应的 class methods
    '''

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        # 如果 request method 是 HEAD, 并且没有处理它的函数则使用 GET 的方式处理
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)

        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)
