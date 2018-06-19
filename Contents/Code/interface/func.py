# -*- coding: utf-8 -*-
def enable_channel_wrapper(func):
    def noop(*args, **kwargs):
        def inner(*a, **k):
            return a[0]

        return inner

    def wrap(*args, **kwargs):
        enforce_route = kwargs.pop("enforce_route", None)
        return (func if (Prefs['channel'] or enforce_route) else noop)(*args, **kwargs)
    return wrap

route = enable_channel_wrapper(route)
handler = enable_channel_wrapper(handler)