# -*- coding: utf-8 -*-
"""
flask.logging
~~~~~~~~~~~~~

:copyright: © 2010 by the Pallets team.
:license: BSD, see LICENSE for more details.
"""

'''
flask.logging
~~~~~~~~~~~~~

内容很少, 不用说明

create: 2018/06/16
'''

from __future__ import absolute_import

import logging
import sys

from werkzeug.local import LocalProxy

from .globals import request


# 为应用找到最合适的错误流. 如果请求是活动的则记录到 `wsgi.errors`, 否则记录到 `sys.stderr`
@LocalProxy
def wsgi_errors_stream():
    """Find the most appropriate error stream for the application. If a request
    is active, log to ``wsgi.errors``, otherwise use ``sys.stderr``.

    If you configure your own :class:`logging.StreamHandler`, you may want to
    use this for the stream. If you are using file or dict configuration and
    can't import this directly, you can refer to it as
    ``ext://flask.logging.wsgi_errors_stream``.
    """
    return request.environ['wsgi.errors'] if request else sys.stderr


def has_level_handler(logger):
    """Check if there is a handler in the logging chain that will handle the
    given logger's :meth:`effective level <~logging.Logger.getEffectiveLevel>`.
    """
    # 检查 logging chain 中是否有处理给定 logger 的 handlers
    level = logger.getEffectiveLevel()
    current = logger

    while current:
        '''
        CRITICAL = 50
        FATAL = CRITICAL
        ERROR = 40
        WARNING = 30
        WARN = WARNING
        INFO = 20
        DEBUG = 10
        NOTSET = 0
        
        日志等级使用数字标记, 可通过大小对比判断是否记录
        '''
        if any(handler.level <= level for handler in current.handlers):
            return True

        if not current.propagate:
            break

        current = current.parent

    return False


#: Log messages to :func:`~flask.logging.wsgi_errors_stream` with the format
#: ``[%(asctime)s] %(levelname)s in %(module)s: %(message)s``.
# 默认 handler 和默认的日志格式
default_handler = logging.StreamHandler(wsgi_errors_stream)
default_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))


def create_logger(app):
    """Get the ``'flask.app'`` logger and configure it if needed.

    When :attr:`~flask.Flask.debug` is enabled, set the logger level to
    :data:`logging.DEBUG` if it is not set.

    If there is no handler for the logger's effective level, add a
    :class:`~logging.StreamHandler` for
    :func:`~flask.logging.wsgi_errors_stream` with a basic format.
    """
    logger = logging.getLogger('flask.app')

    if app.debug and logger.level == logging.NOTSET:
        # app.debug=True 时, 日志等级也设为 DEBUG
        logger.setLevel(logging.DEBUG)

    if not has_level_handler(logger):
        # 不存在可以可以使用的 handler 时, 添加默认 handler
        logger.addHandler(default_handler)

    return logger
