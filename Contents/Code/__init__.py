# -*- coding: utf-8 -*-
import interface
from kinoplex.restore import restore_builtins
from kinoplex.updater import Updater
from interface import *

# restore globals hack #
module = sys.modules['__main__']
restore_builtins(module, {})
globals = getattr(module, "__builtins__")["globals"]

from kinoplex.utils import init_class, setup_network, setup_sentry
setup_network(Core, Prefs)
if Prefs['sentry']:
    setup_sentry(Core, Platform, Prefs)

def Start():
    Log('Start function call')
    HTTP.CacheTime = 0 #CACHE_1WEEK
    HTTP.Headers['User-Agent'] = 'Plex Kinopoisk.bundle'
    if Prefs['update_channel'] != 'none':
        Thread.CreateTimer(int(Prefs['update_interval'] or 1)*60, Updater.auto_update_thread, core=Core, pref=Prefs)

def ValidatePrefs():
    Log('ValidatePrefs function call')

KinopoiskMovieAgent = init_class('KinopoiskMovieAgent', Agent.Movies, globals(), 0)
KinopoiskShowAgent = init_class('KinopoiskShowAgent', Agent.TV_Shows, globals(), 0)