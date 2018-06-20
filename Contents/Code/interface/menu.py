import os, logging
from func import route, handler
from kinoplex.utils import getVersion

PREFIX = '/video/kinopoisk'
version = getVersion(Core)
ObjectContainer.title1 = 'Kinopoisk'

@handler(PREFIX, 'Kinopoisk #%s' % version)
@route(PREFIX)
def root(**kwargs):
    title = 'Kinopoisk #%s' % version
    oc = ObjectContainer(title1=title, title2=title, header=title)
    return oc