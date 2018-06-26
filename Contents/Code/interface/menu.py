# -*- coding: utf-8 -*-
import os, logging, datetime
from func import route, handler
from kinoplex.utils import getVersionInfo

PREFIX = '/video/kinopoisk'
ObjectContainer.title1 = 'Kinopoisk'
Plugin.AddViewGroup("full_details", viewMode="InfoList", mediaType="items", type="list", summary=2)
v,d = getVersionInfo(Core)

@handler(PREFIX, 'Kinopoisk #%s' % v)
@route(PREFIX)
def root(**kwargs):
    v, d = getVersionInfo(Core)
    d = datetime.datetime.fromtimestamp(d).strftime('%d.%m.%Y %X')
    title = 'Kinopoisk #%s' % v
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="full_details")

    oc.add(DirectoryObject(
        title= 'Kinopoisk #%s (%s)' % (v, d)
    ))

    return oc