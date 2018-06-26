# -*- coding: utf-8 -*-
"""
    flask.signals
    ~~~~~~~~~~~~~

    Implements signals based on blinker if available, otherwise
    falls silently back to a noop.

    :copyright: © 2010 by the Pallets team.
    :license: BSD, see LICENSE for more details.
"""

'''
    flask.signals
    ~~~~~~~~~~~~~
    
    如果可用, 实现基于 blinker 的信号类, 否则静默的回到 noop
    没有什么过多的东西, 理解如何使用 signals 即可
    
    create: 2018/06/16
'''

signals_available = False
try:
    from blinker import Namespace
    signals_available = True
except ImportError:
    class Namespace(object):
        def signal(self, name, doc=None):
            return _FakeSignal(name, doc)

    class _FakeSignal(object):
        """If blinker is unavailable, create a fake class with the same
        interface that allows sending of signals but will fail with an
        error on anything else.  Instead of doing anything on send, it
        will just ignore the arguments and do nothing instead.
        """
        '''如果 blinker 不可用, 则创建一个具有相同接口允许发送信号的伪类, 
        但是会在任何时候出错. 它不是发送任何东西, 只是忽略参数并且什么都不做'''

        def __init__(self, name, doc=None):
            self.name = name
            self.__doc__ = doc
        # 这里声明的 _fail(), 在类末尾处被删除, 但是 connect() 等函数会保留下来
        def _fail(self, *args, **kwargs):
            raise RuntimeError('signalling support is unavailable '
                               'because the blinker library is '
                               'not installed.')
        send = lambda *a, **kw: None
        connect = disconnect = has_receivers_for = receivers_for = \
            temporarily_connected_to = connected_to = _fail
        del _fail

# The namespace for code signals.  If you are not Flask code, do
# not put signals in here.  Create your own namespace instead.
_signals = Namespace()


# Core signals.  For usage examples grep the source code or consult
# the API documentation in docs/api.rst as well as docs/signals.rst
template_rendered = _signals.signal('template-rendered')
before_render_template = _signals.signal('before-render-template')
request_started = _signals.signal('request-started')
request_finished = _signals.signal('request-finished')
request_tearing_down = _signals.signal('request-tearing-down')
got_request_exception = _signals.signal('got-request-exception')
appcontext_tearing_down = _signals.signal('appcontext-tearing-down')
appcontext_pushed = _signals.signal('appcontext-pushed')
appcontext_popped = _signals.signal('appcontext-popped')
message_flashed = _signals.signal('message-flashed')
