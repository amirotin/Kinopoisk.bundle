# -*- coding: utf-8 -*-
import os, logging, datetime
from func import route, handler
from kinoplex.utils import getVersionInfo

PREFIX = '/video/kinopoisk'
ObjectContainer.title1 = 'Kinopoisk'
Plugin.AddViewGroup("FullDetails", viewMode="InfoList", mediaType="items")

ICON = 'icon-default.jpg'

v,d = getVersionInfo(Core)

DirectoryObject.thumb = R(ICON)

@handler(PREFIX, 'Kinopoisk #%s' % v)
@route(PREFIX)
def root(**kwargs):
    v, d = getVersionInfo(Core)
    d = datetime.datetime.fromtimestamp(d).strftime('%d.%m.%Y %X')
    title = 'Kinopoisk #%s' % v
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")

    oc.add(DirectoryObject(
        title=u'Плагин Kinopoisk',
        tagline=u'Обновлен %s' % d,
        summary=u'Версия %s' % v
    ))

    oc.add(DirectoryObject(
        key='advanced',
        title=u'Расширенные настройки',
    ))

    oc.add(DirectoryObject(
        key='restart',
        title=u'Перезагрузка плагина'
    ))

    return oc

@route(PREFIX + '/advanced')
def advanced(**kwargs):
    title = u'Расширенные настройки'
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")
    return oc

@route(PREFIX + '/restart')
def advanced(**kwargs):
    title = u'Перезагрузка плагина'
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")
    return oc