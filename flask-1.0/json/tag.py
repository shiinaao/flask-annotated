# -*- coding: utf-8 -*-
"""
Tagged JSON
~~~~~~~~~~~

A compact representation for lossless serialization of non-standard JSON types.
:class:`~flask.sessions.SecureCookieSessionInterface` uses this to serialize
the session data, but it may be useful in other places. It can be extended to
support other types.

.. autoclass:: TaggedJSONSerializer
    :members:

.. autoclass:: JSONTag
    :members:

Let's seen an example that adds support for :class:`~collections.OrderedDict`.
Dicts don't have an order in Python or JSON, so to handle this we will dump
the items as a list of ``[key, value]`` pairs. Subclass :class:`JSONTag` and
give it the new key ``' od'`` to identify the type. The session serializer
processes dicts first, so insert the new tag at the front of the order since
``OrderedDict`` must be processed before ``dict``. ::

    from flask.json.tag import JSONTag

    class TagOrderedDict(JSONTag):
        __slots__ = ('serializer',)
        key = ' od'

        def check(self, value):
            return isinstance(value, OrderedDict)

        def to_json(self, value):
            return [[k, self.serializer.tag(v)] for k, v in iteritems(value)]

        def to_python(self, value):
            return OrderedDict(value)

    app.session_interface.serializer.register(TagOrderedDict, index=0)

:copyright: © 2010 by the Pallets team.
:license: BSD, see LICENSE for more details.
"""

'''
Tagged JSON
~~~~~~~~~~~

对于非标准JSON类型的无损序列化的紧凑表示。
:class:`~flask.sessions。SecureCookieSessionInterface` 使用这个来序列化

核心类: JSONTag(), TaggedJSONSerializer()

create: 2018/06/14
    [Delete]~~看完发现好像除了单元测试别的地方都没用过, 好像是 1.0版本 刚添加的, 难受~~ 
update: 2018/06/16
    TaggedJSONSerializer() 在 flask.session 模块中已使用
'''

from base64 import b64decode, b64encode
from datetime import datetime
from uuid import UUID

from jinja2 import Markup
from werkzeug.http import http_date, parse_date

from flask._compat import iteritems, text_type
from flask.json import dumps, loads


#############################################################################
# JSONTag 及其子类
# 定义了对各种 type 的不同序列化方式
#############################################################################
class JSONTag(object):
    """Base class for defining type tags for :class:`TaggedJSONSerializer`."""

    __slots__ = ('serializer',)

    #: The tag to mark the serialized object with. If ``None``, this tag is
    #: only used as an intermediate step during tagging.
    key = None
    # 在定义 `__slots__` 的情况下声明了类变量 `key`, `key` 在实例中将会变成只读属性
    # 只能使用子类继承的方式改变 `key` 的值

    def __init__(self, serializer):
        """Create a tagger for the given serializer."""
        self.serializer = serializer

    def check(self, value):
        """Check if the given value should be tagged by this tag."""
        raise NotImplementedError

    def to_json(self, value):
        """Convert the Python object to an object that is a valid JSON type.
        The tag will be added later."""
        raise NotImplementedError

    def to_python(self, value):
        """Convert the JSON representation back to the correct type. The tag
        will already be removed."""
        raise NotImplementedError

    def tag(self, value):
        """Convert the value to a valid JSON type and add the tag structure
        around it."""
        return {self.key: self.to_json(value)}


class TagDict(JSONTag):
    """Tag for 1-item dicts whose only key matches a registered tag.

    Internally, the dict key is suffixed with `__`, and the suffix is removed
    when deserializing.
    """
    # 在内部，dict 键以 `__` 作为后缀，反序列化时后缀被删除

    __slots__ = ()
    key = ' di'

    def check(self, value):
        return (
            isinstance(value, dict)
            and len(value) == 1
            and next(iter(value)) in self.serializer.tags
        )

    def to_json(self, value):
        key = next(iter(value))
        '''序列化时添加 `__` 后缀, 并将 value 封装为对应的 Tag 类的实例
        self.serializer.tag() 即为 TagDict(), PassDict() 等类
        详细说明参考下面的这个类 class TaggedJSONSerializer(object)'''
        return {key + '__': self.serializer.tag(value[key])}

    def to_python(self, value):
        key = next(iter(value))
        return {key[:-2]: value[key]}


class PassDict(JSONTag):
    __slots__ = ()

    def check(self, value):
        return isinstance(value, dict)

    def to_json(self, value):
        # JSON objects may only have string keys, so don't bother tagging the
        # key here.
        return dict((k, self.serializer.tag(v)) for k, v in iteritems(value))

    tag = to_json


class TagTuple(JSONTag):
    __slots__ = ()
    key = ' t'

    def check(self, value):
        return isinstance(value, tuple)

    def to_json(self, value):
        return [self.serializer.tag(item) for item in value]

    def to_python(self, value):
        return tuple(value)


class PassList(JSONTag):
    __slots__ = ()

    def check(self, value):
        return isinstance(value, list)

    def to_json(self, value):
        return [self.serializer.tag(item) for item in value]

    tag = to_json


class TagBytes(JSONTag):
    __slots__ = ()
    key = ' b'

    def check(self, value):
        return isinstance(value, bytes)

    def to_json(self, value):
        return b64encode(value).decode('ascii')

    def to_python(self, value):
        return b64decode(value)


class TagMarkup(JSONTag):
    """Serialize anything matching the :class:`~flask.Markup` API by
    having a ``__html__`` method to the result of that method. Always
    deserializes to an instance of :class:`~flask.Markup`."""

    __slots__ = ()
    key = ' m'

    def check(self, value):
        return callable(getattr(value, '__html__', None))

    def to_json(self, value):
        return text_type(value.__html__())

    def to_python(self, value):
        return Markup(value)


class TagUUID(JSONTag):
    __slots__ = ()
    key = ' u'

    def check(self, value):
        return isinstance(value, UUID)

    def to_json(self, value):
        return value.hex

    def to_python(self, value):
        return UUID(value)


class TagDateTime(JSONTag):
    __slots__ = ()
    key = ' d'

    def check(self, value):
        return isinstance(value, datetime)

    def to_json(self, value):
        return http_date(value)

    def to_python(self, value):
        return parse_date(value)


class TaggedJSONSerializer(object):
    """Serializer that uses a tag system to compactly represent objects that
    are not JSON types. Passed as the intermediate serializer to
    :class:`itsdangerous.Serializer`.

    The following extra types are supported:

    * :class:`dict`
    * :class:`tuple`
    * :class:`bytes`
    * :class:`~flask.Markup`
    * :class:`~uuid.UUID`
    * :class:`~datetime.datetime`
    """

    __slots__ = ('tags', 'order')

    #: Tag classes to bind when creating the serializer. Other tags can be
    #: added later using :meth:`~register`.
    default_tags = [
        TagDict, PassDict, TagTuple, PassList, TagBytes, TagMarkup, TagUUID,
        TagDateTime,
    ]

    def __init__(self):
        self.tags = {}
        # tags 结构: { ' di': TagDict(self), ' t': TagTuple(self), ... }
        # 注意 tags 中只会保存定义了 `key` 的 Tag 类
        self.order = []
        # order 结构: [ TagDict(self), PassDict(self), ... ]

        for cls in self.default_tags:
            self.register(cls)

    # 注册不同 type 的处理类, force=True 会覆盖注册
    def register(self, tag_class, force=False, index=None):
        """Register a new tag with this serializer.

        :param tag_class: tag class to register. Will be instantiated with this
            serializer instance.
        :param force: overwrite an existing tag. If false (default), a
            :exc:`KeyError` is raised.
        :param index: index to insert the new tag in the tag order. Useful when
            the new tag is a special case of an existing tag. If ``None``
            (default), the tag is appended to the end of the order.

        :raise KeyError: if the tag key is already registered and ``force`` is
            not true.
        """
        # `self` 赋值给 `JSONTag.serializer`
        tag = tag_class(self)
        key = tag.key

        if key is not None:
            if not force and key in self.tags:
                raise KeyError("Tag '{0}' is already registered.".format(key))

            self.tags[key] = tag

        if index is None:
            self.order.append(tag)
        else:
            self.order.insert(index, tag)

    def tag(self, value):
        """Convert a value to a tagged representation if necessary."""
        # 对符合已定义 Tag 类的 value 返回对应的 Tag 类的实例
        for tag in self.order:
            if tag.check(value):
                # chenk() 函数判断使用哪个类初始化
                return tag.tag(value)

        return value

    def untag(self, value):
        """Convert a tagged representation back to the original type."""
        # 将 Tag 类的实例还原为原类型
        if len(value) != 1:
            return value

        key = next(iter(value))

        if key not in self.tags:
            return value

        return self.tags[key].to_python(value[key])

    def dumps(self, value):
        """Tag the value and dump it to a compact JSON string."""
        # TODO: 没有调用 to_json() 看不懂啊
        return dumps(self.tag(value), separators=(',', ':'))

    def loads(self, value):
        """Load data from a JSON string and deserialized any tagged objects."""
        # object_hook(): 将对解码的任何对象调用并返回其结果, 功能可以理解为回调函数
        return loads(value, object_hook=self.untag)
