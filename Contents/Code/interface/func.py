# -*- coding: utf-8 -*-
import datetime

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

ObjectClass = getattr(getattr(Redirect, "_object_class"), "__bases__")[0]

class ZipObject(ObjectClass):
    def __init__(self, data):
        ObjectClass.__init__(self, "")
        self.zipdata = data
        self.SetHeader("Content-Type", "application/zip")

    def Content(self):
        self.SetHeader("Content-Disposition",
                       'attachment; filename="' + datetime.datetime.now().strftime("Logs_%y%m%d_%H-%M-%S.zip")
                       + '"')
        return self.zipdata
