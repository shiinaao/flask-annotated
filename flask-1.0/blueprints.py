# -*- coding: utf-8 -*-
"""
    flask.blueprints
    ~~~~~~~~~~~~~~~~

    Blueprints are the recommended way to implement larger or more
    pluggable applications in Flask 0.7 and later.

    :copyright: © 2010 by the Pallets team.
    :license: BSD, see LICENSE for more details.
"""

'''
    flask.blueprints
    ~~~~~~~~~~~~~~~~
    
    在 Flask 0.7 及更高版本中，建议使用 Blueprints 实现更大或更多的可插拔应用程序。
    
    代码摘要:
        class BlueprintSetupState(object):
        class Blueprint(_PackageBoundObject):
        
    create: 2018/06/25
        2k 行的 app.py, 我开始慌了
'''

from functools import update_wrapper
from werkzeug.urls import url_join

from .helpers import _PackageBoundObject, _endpoint_from_view_func


# 用于向 app 注册 blueprint 的临时持有对象, 不涉及逻辑只持有数据
class BlueprintSetupState(object):
    """Temporary holder object for registering a blueprint with the
    application.  An instance of this class is created by the
    :meth:`~flask.Blueprint.make_setup_state` method and later passed
    to all register callback functions.
    """

    def __init__(self, blueprint, app, options, first_registration):
        #: a reference to the current application
        self.app = app

        #: a reference to the blueprint that created this setup state.
        self.blueprint = blueprint

        #: a dictionary with all options that were passed to the
        #: :meth:`~flask.Flask.register_blueprint` method.
        self.options = options

        #: as blueprints can be registered multiple times with the
        #: application and not everything wants to be registered
        #: multiple times on it, this attribute can be used to figure
        #: out if the blueprint was registered in the past already.
        '''由于蓝图可以在应用程序中多次注册，并且并非所有内容都需要在其上注册多次，
        因此可以使用此属性来确定蓝图是否已在过去注册过。'''
        self.first_registration = first_registration

        subdomain = self.options.get('subdomain')
        if subdomain is None:
            subdomain = self.blueprint.subdomain

        #: The subdomain that the blueprint should be active for, ``None``
        #: otherwise.
        self.subdomain = subdomain

        url_prefix = self.options.get('url_prefix')
        if url_prefix is None:
            url_prefix = self.blueprint.url_prefix
        #: The prefix that should be used for all URLs defined on the
        #: blueprint.
        self.url_prefix = url_prefix

        #: A dictionary with URL defaults that is added to each and every
        #: URL that was defined with the blueprint.
        self.url_defaults = dict(self.blueprint.url_values_defaults)
        self.url_defaults.update(self.options.get('url_defaults', ()))

    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """A helper method to register a rule (and optionally a view function)
        to the application.  The endpoint is automatically prefixed with the
        blueprint's name.
        """
        # 添加 prefix
        if self.url_prefix is not None:
            if rule:
                rule = '/'.join((
                    self.url_prefix.rstrip('/'), rule.lstrip('/')))
            else:
                rule = self.url_prefix
        options.setdefault('subdomain', self.subdomain)
        # 没有设定 endpoint 时, 获取 view_func.__name__ 即函数名作为 endpoint
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)
        defaults = self.url_defaults
        if 'defaults' in options:
            # 合并字典
            defaults = dict(defaults, **options.pop('defaults'))
        self.app.add_url_rule(rule, '%s.%s' % (self.blueprint.name, endpoint),
                              view_func, defaults=defaults, **options)


class Blueprint(_PackageBoundObject):
    """Represents a blueprint.  A blueprint is an object that records
    functions that will be called with the
    :class:`~flask.blueprints.BlueprintSetupState` later to register functions
    or other things on the main application.  See :ref:`blueprints` for more
    information.

    .. versionadded:: 0.7
    """

    warn_on_modifications = False
    _got_registered_once = False

    #: Blueprint local JSON decoder class to use.
    #: Set to ``None`` to use the app's :class:`~flask.app.Flask.json_encoder`.
    # 设置为 None 时使用 :class:`~flask.app.Flask.json_encoder`
    json_encoder = None
    #: Blueprint local JSON decoder class to use.
    #: Set to ``None`` to use the app's :class:`~flask.app.Flask.json_decoder`.
    json_decoder = None

    # TODO remove the next three attrs when Sphinx :inherited-members: works
    # https://github.com/sphinx-doc/sphinx/issues/741

    #: The name of the package or module that this app belongs to. Do not
    #: change this once it is set by the constructor.
    import_name = None

    #: Location of the template files to be added to the template lookup.
    #: ``None`` if templates should not be added.
    template_folder = None

    #: Absolute path to the package on the filesystem. Used to look up
    #: resources contained in the package.
    root_path = None

    def __init__(self, name, import_name, static_folder=None,
                 static_url_path=None, template_folder=None,
                 url_prefix=None, subdomain=None, url_defaults=None,
                 root_path=None):
        _PackageBoundObject.__init__(self, import_name, template_folder,
                                     root_path=root_path)
        self.name = name
        self.url_prefix = url_prefix
        self.subdomain = subdomain
        self.static_folder = static_folder
        self.static_url_path = static_url_path
        self.deferred_functions = []
        if url_defaults is None:
            url_defaults = {}
        self.url_values_defaults = url_defaults

    # 注册一个函数, 当 blueprint 注册后此函数被调用
    def record(self, func):
        """Registers a function that is called when the blueprint is
        registered on the application.  This function is called with the
        state as argument as returned by the :meth:`make_setup_state`
        method.
        """
        if self._got_registered_once and self.warn_on_modifications:
            from warnings import warn
            warn(Warning('The blueprint was already registered once '
                         'but is getting modified now.  These changes '
                         'will not show up.'))
        self.deferred_functions.append(func)

    # 与 record 类似, 但是对函数进行了包装, 使函数只会执行一次
    def record_once(self, func):
        """Works like :meth:`record` but wraps the function in another
        function that will ensure the function is only called once.  If the
        blueprint is registered a second time on the application, the
        function passed is not called.
        """
        def wrapper(state):
            if state.first_registration:
                func(state)
        return self.record(update_wrapper(wrapper, func))

    # 创建一个 BlueprintSetupState 的实例, first_registration 默认设定为 False
    def make_setup_state(self, app, options, first_registration=False):
        """Creates an instance of :meth:`~flask.blueprints.BlueprintSetupState`
        object that is later passed to the register callback functions.
        Subclasses can override this to return a subclass of the setup state.
        """
        return BlueprintSetupState(self, app, options, first_registration)

    # 注册所有 views 和注册到 blueprint 的回调函数到 app
    def register(self, app, options, first_registration=False):
        """Called by :meth:`Flask.register_blueprint` to register all views
        and callbacks registered on the blueprint with the application. Creates
        a :class:`.BlueprintSetupState` and calls each :meth:`record` callback
        with it.

        :param app: The application this blueprint is being registered with.
        :param options: Keyword arguments forwarded from
            :meth:`~Flask.register_blueprint`.
        :param first_registration: Whether this is the first time this
            blueprint has been registered on the application.
        """
        self._got_registered_once = True
        state = self.make_setup_state(app, options, first_registration)

        # 如果有 static 文件夹, 添加相关的 URL rule
        if self.has_static_folder:
            state.add_url_rule(
                self.static_url_path + '/<path:filename>',
                view_func=self.send_static_file, endpoint='static'
            )
            # '/<path:filename>' 的这种形式应该会由 static endpoint 处理

        # blueprint 注册时, 依次执行所有后处理函数
        for deferred in self.deferred_functions:
            deferred(state)

    # @route 装饰器
    def route(self, rule, **options):
        """Like :meth:`Flask.route` but for a blueprint.  The endpoint for the
        :func:`url_for` function is prefixed with the name of the blueprint.
        """
        def decorator(f):
            endpoint = options.pop("endpoint", f.__name__)
            self.add_url_rule(rule, endpoint, f, **options)
            return f
        return decorator

    # 注册一个添加路由函数
    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """Like :meth:`Flask.add_url_rule` but for a blueprint.  The endpoint for
        the :func:`url_for` function is prefixed with the name of the blueprint.
        """
        # endpoint 和 view_func 的名称中都不能包含 dots(.)
        if endpoint:
            assert '.' not in endpoint, "Blueprint endpoints should not contain dots"
        if view_func and hasattr(view_func, '__name__'):
            assert '.' not in view_func.__name__, "Blueprint view function name should not contain dots"
        '''路由注册以匿名函数的方式添加到 self.deferred_functions[] 中, 
        当 blueprint 注册时再调用并添加'''
        self.record(lambda s:
            s.add_url_rule(rule, endpoint, view_func, **options))

    # @endpoint 装饰器, 这不是给 endpoint 添加 blueprint name 前缀
    def endpoint(self, endpoint):
        """Like :meth:`Flask.endpoint` but for a blueprint.  This does not
        prefix the endpoint with the blueprint name, this has to be done
        explicitly by the user of this method.  If the endpoint is prefixed
        with a `.` it will be registered to the current blueprint, otherwise
        it's an application independent endpoint.
        """
        def decorator(f):
            def register_endpoint(state):
                state.app.view_functions[endpoint] = f
            self.record_once(register_endpoint)
            return f
        return decorator

    #########################################################################
    # 往下都是写注册函数了, 没什么意思
    #########################################################################

    # 注册一个自定义的 template filter, blueprint 级
    # 例如: {{ user | tojson | safe }}
    def app_template_filter(self, name=None):
        """Register a custom template filter, available application wide.  Like
        :meth:`Flask.template_filter` but for a blueprint.

        :param name: the optional name of the filter, otherwise the
                     function name will be used.
        """
        def decorator(f):
            self.add_app_template_filter(f, name=name)
            return f
        return decorator

    # 注册一个自定义的 template filter, app 级
    def add_app_template_filter(self, f, name=None):
        """Register a custom template filter, available application wide.  Like
        :meth:`Flask.add_template_filter` but for a blueprint.  Works exactly
        like the :meth:`app_template_filter` decorator.

        :param name: the optional name of the filter, otherwise the
                     function name will be used.
        """
        def register_template(state):
            state.app.jinja_env.filters[name or f.__name__] = f
        self.record_once(register_template)

    # 注册一个自定义的 template test, blueprint 级
    # 例如: {% if name is upper %}
    def app_template_test(self, name=None):
        """Register a custom template test, available application wide.  Like
        :meth:`Flask.template_test` but for a blueprint.

        .. versionadded:: 0.10

        :param name: the optional name of the test, otherwise the
                     function name will be used.
        """
        def decorator(f):
            self.add_app_template_test(f, name=name)
            return f
        return decorator

    # 注册一个自定义的 template test, app 级
    def add_app_template_test(self, f, name=None):
        """Register a custom template test, available application wide.  Like
        :meth:`Flask.add_template_test` but for a blueprint.  Works exactly
        like the :meth:`app_template_test` decorator.

        .. versionadded:: 0.10

        :param name: the optional name of the test, otherwise the
                     function name will be used.
        """
        def register_template(state):
            state.app.jinja_env.tests[name or f.__name__] = f
        self.record_once(register_template)

    # 注册 template global (全局函数, 可在模板内使用), blueprint 级
    # 例如: {% for num in range(10, 20, 2) %}
    def app_template_global(self, name=None):
        """Register a custom template global, available application wide.  Like
        :meth:`Flask.template_global` but for a blueprint.

        .. versionadded:: 0.10

        :param name: the optional name of the global, otherwise the
                     function name will be used.
        """
        def decorator(f):
            self.add_app_template_global(f, name=name)
            return f
        return decorator

    def add_app_template_global(self, f, name=None):
        """Register a custom template global, available application wide.  Like
        :meth:`Flask.add_template_global` but for a blueprint.  Works exactly
        like the :meth:`app_template_global` decorator.

        .. versionadded:: 0.10

        :param name: the optional name of the global, otherwise the
                     function name will be used.
        """
        def register_template(state):
            state.app.jinja_env.globals[name or f.__name__] = f
        self.record_once(register_template)

    # 为 blueprint 注册预处理函数
    def before_request(self, f):
        """Like :meth:`Flask.before_request` but for a blueprint.  This function
        is only executed before each request that is handled by a function of
        that blueprint.
        """
        self.record_once(lambda s: s.app.before_request_funcs
            .setdefault(self.name, []).append(f))
        return f

    # 为 app 注册预处理函数, app 级
    def before_app_request(self, f):
        """Like :meth:`Flask.before_request`.  Such a function is executed
        before each request, even if outside of a blueprint.
        """
        self.record_once(lambda s: s.app.before_request_funcs
            .setdefault(None, []).append(f))
        return f

    # 注册一个只在第一个 request 时调用的函数, app 级
    def before_app_first_request(self, f):
        """Like :meth:`Flask.before_first_request`.  Such a function is
        executed before the first request to the application.
        """
        self.record_once(lambda s: s.app.before_first_request_funcs.append(f))
        return f

    # 注册一个后处理函数, blueprint 级
    def after_request(self, f):
        """Like :meth:`Flask.after_request` but for a blueprint.  This function
        is only executed after each request that is handled by a function of
        that blueprint.
        """
        self.record_once(lambda s: s.app.after_request_funcs
            .setdefault(self.name, []).append(f))
        return f

    def after_app_request(self, f):
        """Like :meth:`Flask.after_request` but for a blueprint.  Such a function
        is executed after each request, even if outside of the blueprint.
        """
        self.record_once(lambda s: s.app.after_request_funcs
            .setdefault(None, []).append(f))
        return f

    '''注册一个函数, 当每个 blueprint 下 request 请求结束时被调用
    当 pop 一个请求上下文时, 即使没有执行实际请求也会执行'''
    def teardown_request(self, f):
        """Like :meth:`Flask.teardown_request` but for a blueprint.  This
        function is only executed when tearing down requests handled by a
        function of that blueprint.  Teardown request functions are executed
        when the request context is popped, even when no actual request was
        performed.
        """
        self.record_once(lambda s: s.app.teardown_request_funcs
            .setdefault(self.name, []).append(f))
        return f

    # 同上, app 级的
    def teardown_app_request(self, f):
        """Like :meth:`Flask.teardown_request` but for a blueprint.  Such a
        function is executed when tearing down each request, even if outside of
        the blueprint.
        """
        self.record_once(lambda s: s.app.teardown_request_funcs
            .setdefault(None, []).append(f))
        return f

    # 注册上下文处理器, 函数只在 blueprint 处理 requests 时执行
    def context_processor(self, f):
        """Like :meth:`Flask.context_processor` but for a blueprint.  This
        function is only executed for requests handled by a blueprint.
        """
        self.record_once(lambda s: s.app.template_context_processors
            .setdefault(self.name, []).append(f))
        return f

    # 同上, app 级的
    def app_context_processor(self, f):
        """Like :meth:`Flask.context_processor` but for a blueprint.  Such a
        function is executed each request, even if outside of the blueprint.
        """
        self.record_once(lambda s: s.app.template_context_processors
            .setdefault(None, []).append(f))
        return f

    # 注册 errorhandler, app 级的
    def app_errorhandler(self, code):
        """Like :meth:`Flask.errorhandler` but for a blueprint.  This
        handler is used for all requests, even if outside of the blueprint.
        """
        def decorator(f):
            self.record_once(lambda s: s.app.errorhandler(code)(f))
            return f
        return decorator

    # 注册一个 URL values 预处理器, blueprint 级
    def url_value_preprocessor(self, f):
        """Registers a function as URL value preprocessor for this
        blueprint.  It's called before the view functions are called and
        can modify the url values provided.
        """
        self.record_once(lambda s: s.app.url_value_preprocessors
            .setdefault(self.name, []).append(f))
        return f

    '''这个 blueprint 的默认 URL 回调函数, 它使用 endpoint 和 values 调用, 
    并应该更新已传递的值, 自动地将值注入到 url_for() 的调用中去'''
    def url_defaults(self, f):
        """Callback function for URL defaults for this blueprint.  It's called
        with the endpoint and values and should update the values passed
        in place.
        """
        self.record_once(lambda s: s.app.url_default_functions
            .setdefault(self.name, []).append(f))
        return f

    def app_url_value_preprocessor(self, f):
        """Same as :meth:`url_value_preprocessor` but application wide.
        """
        self.record_once(lambda s: s.app.url_value_preprocessors
            .setdefault(None, []).append(f))
        return f

    def app_url_defaults(self, f):
        """Same as :meth:`url_defaults` but application wide.
        """
        self.record_once(lambda s: s.app.url_default_functions
            .setdefault(None, []).append(f))
        return f

    # @errorhandler 装饰器, blueprint 级
    def errorhandler(self, code_or_exception):
        """Registers an error handler that becomes active for this blueprint
        only.  Please be aware that routing does not happen local to a
        blueprint so an error handler for 404 usually is not handled by
        a blueprint unless it is caused inside a view function.  Another
        special case is the 500 internal server error which is always looked
        up from the application.

        Otherwise works as the :meth:`~flask.Flask.errorhandler` decorator
        of the :class:`~flask.Flask` object.
        """
        def decorator(f):
            self.record_once(lambda s: s.app._register_error_handler(
                self.name, code_or_exception, f))
            return f
        return decorator

    def register_error_handler(self, code_or_exception, f):
        """Non-decorator version of the :meth:`errorhandler` error attach
        function, akin to the :meth:`~flask.Flask.register_error_handler`
        application-wide function of the :class:`~flask.Flask` object but
        for error handlers limited to this blueprint.

        .. versionadded:: 0.11
        """
        self.record_once(lambda s: s.app._register_error_handler(
            self.name, code_or_exception, f))
