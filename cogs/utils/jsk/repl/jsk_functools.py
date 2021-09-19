# -*- coding: utf-8 -*-

"""
jishaku.functools
~~~~~~~~~~~~~~~~~

Function-related tools for Jishaku.
https://jishaku.readthedocs.io/en/latest/_modules/jishaku/functools.html

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""


class AsyncSender:
    """
    Storage and control flow class that allows prettier value sending to async iterators.

    Example
    --------

    .. code:: python3

        async def foo():
            print("foo yielding 1")
            x = yield 1
            print(f"foo received {x}")
            yield 3

        async for send, result in AsyncSender(foo()):
            print(f"asyncsender received {result}")
            send(2)

    Produces:

    .. code::

        foo yielding 1
        asyncsender received 1
        foo received 2
        asyncsender received 3
    """

    __slots__ = ('iterator', 'send_value')

    def __init__(self, iterator):
        self.iterator = iterator
        self.send_value = None

    def __aiter__(self):
        return self._internal(self.iterator.__aiter__())

    async def _internal(self, base):
        try:
            while True:
                # Send the last value to the iterator
                value = await base.asend(self.send_value)
                # Reset it in case one is not sent next iteration
                self.send_value = None
                # Yield sender and iterator value
                yield self.set_send_value, value
        except StopAsyncIteration:
            pass

    def set_send_value(self, value):
        """
        Sets the next value to be sent to the iterator.

        This is provided by iteration of this class and should
        not be called directly.
        """

        self.send_value = value
