# -*- coding: utf-8 -*-
import os, datetime, urlparse
import StringIO
import glob
from zipfile import ZipFile, ZIP_DEFLATED
from func import route, handler, ZipObject
from kinoplex.utils import getVersionInfo

PREFIX = '/video/kinopoisk'
ObjectContainer.title1 = 'Kinopoisk'
Plugin.AddViewGroup("FullDetails", viewMode="InfoList", mediaType="items")

ICON = 'icon-default.jpg'

V,D = getVersionInfo(Core)

DirectoryObject.thumb = R(ICON)

@handler(PREFIX, 'Kinopoisk #%s' % V)
@route(PREFIX)
def root(**kwargs):
    title = 'Kinopoisk #%s' % V
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")
    oc.add(DirectoryObject(key=Callback(info), title=u'Информация о плагине',))
    oc.add(DirectoryObject(key=Callback(advanced), title=u'Расширенные настройки',))
    oc.add(DirectoryObject(key=Callback(restart), title=u'Перезагрузка плагина'))
    oc.add(DirectoryObject(key=Callback(update_status), title=u'Статус автообновления'))
    oc.add(DirectoryObject(key=Callback(get_logs), title=u'Загрузить логи'))
    return oc

@route(PREFIX + '/info')
def info(**kwargs):
    title = u'Информация о плагине'
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")
    oc.add(DirectoryObject(key=Callback(info), title=u'Версия: %s' % V))
    oc.add(DirectoryObject(key=Callback(info), title=u'Дата обновления: %s' % datetime.datetime.fromtimestamp(D).strftime('%d.%m.%Y %X')))
    return oc

@route(PREFIX + '/advanced')
def advanced(**kwargs):
    title = u'Расширенные настройки'
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")
    return oc

@route(PREFIX + '/restart')
def restart(**kwargs):
    title = u'Перезагрузка плагина'
    oc = ObjectContainer(title1=title, title2=title, header=title, view_group="FullDetails")
    return oc

@route(PREFIX + '/update_status')
def update_status(**kwargs):
    title = u'Статус автообновления'
    error = Core.storage.load_data_item('error_update')
    oc = ObjectContainer(title2=title)

    if error:
        oc.add(DirectoryObject(key=Callback(info), title=u'Ошибка: %s' % error))
    else:
        oc.add(DirectoryObject(key=Callback(info), title=u'OK'))

    return oc

@route(PREFIX + '/get_logs')
def get_logs(**kwargs):
    req_headers = Core.sandbox.context.request.headers
    get_external_ip = True
    link_base = ""

    if "Origin" in req_headers:
        link_base = req_headers["Origin"]
        Log.Debug("Using origin-based link_base")
        get_external_ip = False

    elif "Referer" in req_headers:
        parsed = urlparse.urlparse(req_headers["Referer"])
        link_base = "%s://%s%s" % (parsed.scheme, parsed.hostname, (":%s" % parsed.port) if parsed.port else "")
        Log.Debug("Using referer-based link_base")
        get_external_ip = False

    if get_external_ip or "plex.tv" in link_base:
        ip = Core.networking.http_request("http://www.plexapp.com/ip.php", cacheTime=7200).content.strip()
        link_base = "https://%s:32400" % ip
        Log.Debug("Using ip-based fallback link_base")

    logs_link = "%s%s?X-Plex-Token=%s" % (link_base, PREFIX + '/logs', req_headers['X-Plex-Token'])
    oc = ObjectContainer(
        title2=logs_link,
        no_cache=True,
        no_history=True,
        header="Copy this link and open this in your browser, please",
        message=logs_link)
    return oc


@route(PREFIX + '/logs')
def DownloadLogs():
    plugin_log_path = None
    server_log_path = None
    for handler in Core.log.handlers:
        cls_name = getattr(getattr(handler, "__class__"), "__name__")
        if cls_name in ('FileHandler', 'RotatingFileHandler', 'TimedRotatingFileHandler'):
            plugin_log_file = handler.baseFilename

            if os.path.isfile(os.path.realpath(plugin_log_file)):
                plugin_log_path = plugin_log_file

    if plugin_log_path:
        server_log_file = os.path.realpath(os.path.join(plugin_log_path, "../../Plex Media Server.log"))
        if os.path.isfile(server_log_file):
            server_log_path = server_log_file


    buff = StringIO.StringIO()
    zip_archive = ZipFile(buff, mode='w', compression=ZIP_DEFLATED)

    logs = sorted(glob.glob(plugin_log_path + '*')) + [server_log_path]
    for path in logs:
        data = StringIO.StringIO()
        data.write(Core.storage.load(path))
        zip_archive.writestr(os.path.basename(path), data.getvalue())

    zip_archive.close()

    return ZipObject(buff.getvalue())