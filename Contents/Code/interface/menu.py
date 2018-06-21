# -*- coding: utf-8 -*-
import os, logging
from func import route, handler
from kinoplex.utils import getVersion

PREFIX = '/video/kinopoisk'
version = getVersion(Core)
ObjectContainer.title1 = 'Kinopoisk'
Plugin.AddViewGroup("full_details", viewMode="InfoList", mediaType="items", type="list", summary=2)

@handler(PREFIX, 'Kinopoisk #%s' % version)
@route(PREFIX)
def root(**kwargs):
    title = 'Kinopoisk #%s' % version
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="full_details")
    return oc