# -*- coding: utf-8 -*-
import sys, interface
from kinoplex.restore import restore_builtins
from kinoplex.updater import Updater
from interface.menu import *

# restore globals hack #
module = sys.modules['__main__']
restore_builtins(module, {})
globals = getattr(module, "__builtins__")["globals"]

from kinoplex.utils import init_class, setup_sentry, setup_network
setup_sentry(Core, Platform)
setup_network(Core)

def Start():
    HTTP.CacheTime = 0
    HTTP.Headers['User-Agent'] = 'Plex Kinopoisk.bundle'
    #Thread.CreateTimer(int(Prefs['update_interval'] or 1)*60, Updater.auto_update_thread, core=Core, pref=Prefs)

def ValidatePrefs():
    HTTP.Request("http://127.0.0.1:32400/:/plugins/%s/restart" % Plugin.Identifier, immediate=True, cacheTime=0)

KinopoiskMovieAgent = init_class('KinopoiskMovieAgent', Agent.Movies, globals())
KinopoiskShowAgent = init_class('KinopoiskShowAgent', Agent.TV_Shows, globals())