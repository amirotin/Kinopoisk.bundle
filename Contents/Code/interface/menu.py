import os, logging
from func import route, handler

PREFIX = '/video/kinopoisk'
ObjectContainer.title1 = 'Kinopoisk'

@handler(PREFIX, 'Kinopoisk')
@route(PREFIX)
def root(**kwargs):
    oc = ObjectContainer(title1='Kinopoisk', title2='Kinopoisk', header='Kinopoisk')
    return oc