# -*- coding: utf-8 -*-
from base import SourceBase
from urlparse import urlparse, urlunparse
from types import MethodType
import json, time, urllib, re, m3u8

class KPTrailersSource(SourceBase):
    def __init__(self, app):
        super(KPTrailersSource, self).__init__(app)
        self.api.Route.Connect('/video/kinopoisk/trailer', self.trailer_route)

    @staticmethod
    def extra_type(extra):
        return {
            extra.find(u'трейлер') >= 0: 'trailer',
            extra.find(u'фрагмент') >= 0: 'scene_or_sample',
            extra.find(u'ТВ-ролик') >= 0: 'scene_or_sample',
            extra.find(u'съёмках') >= 0: 'behind_the_scenes',
            extra.find(u'интервью') >= 0: 'interview'
        }.get(True, None)

    @staticmethod
    def chunks(data, size):
        for i in xrange(0, len(data), size):
            yield dict(data.items()[i:i+size])

    def trailer_route(self, url, width, height):
        link = url.rsplit('/', 1)[0]
        m3u8_obj = m3u8.loads(self.api.Core.networking.http_request(url).content)
        m3u8_data = list()
        m3u8_data.append('#EXTM3U')
        m3u8_data.append('#EXT-X-VERSION:'+m3u8_obj.version)
        for stream in m3u8_obj.playlists:
            if stream.stream_info.resolution == (int(width), int(height)):
                stream.uri = link + '/' + stream.uri
                m3u8_data.append(str(stream))
                break

        audio = m3u8_obj.media[0]
        audio.uri = link + '/' + audio.uri
        m3u8_data.append(str(audio))

        m3u8_obj = self.api.Framework.objects.Object(None, data="\n".join(m3u8_data))
        m3u8_obj.SetHeader("Content-Type", "application/force-download")

        def m3u8_Content(self):
            self.SetHeader("Content-Disposition", 'attachment; filename="master.m3u8"')
            return self.data

        m3u8_obj.Content = MethodType(m3u8_Content, m3u8_obj)
        return m3u8_obj

    def make_request(self, params):
        param_str = ''
        for id, data in params.iteritems():
            param_str += '%s,%s,rnd-%s;' % data['d']
        return self.api.String.Quote(param_str[:-1])

    def get_anti_captcha(self, taskid):
        while True:
            captcha_response = self.api.JSON.ObjectFromString(self.api.HTTP.Request(
                self.conf.anticaptcha.gettask, method='POST', data=json.dumps({
                    "clientKey": self.api.Prefs['captcha_key'],
                    "taskId": taskid
                })
            ).content)

            if captcha_response["errorId"] == 0:
                if captcha_response["status"] == "processing":
                    time.sleep(10)
                else:
                    return captcha_response
            else:
                return captcha_response

    def report_captcha(self, taskid):
        resp = self.api.JSON.ObjectFromString(self.api.HTTP.Request(
            self.conf.anticaptcha.report, method='POST', data=json.dumps({
                "clientKey": self.api.Prefs['captcha_key'],
                "taskId": taskid
            })
        ).content)

    def solve_captcha(self, captcha_req, attemps):
        form_data = {}
        captcha_page = self.api.HTML.ElementFromString(captcha_req.content)
        captcha_form = captcha_page.xpath(self.conf.extras.recaptcha)
        if captcha_form:
            for input in captcha_form[0].xpath('//input'):
                if input.value:
                    form_data[input.name] = input.value

            img = captcha_form[0].xpath('//img/@src')
            img_data = self.api.HTTP.Request(img[0]).content
            task_data = self.api.JSON.ObjectFromString(self.api.HTTP.Request(
                self.conf.anticaptcha.newtask,
                method='POST',
                data=json.dumps({
                    "clientKey": self.api.Prefs['captcha_key'],
                    "softId": 900,
                    "languagePool": "rn",
                    "task":
                        {
                            "type": "ImageToTextTask",
                            "phrase": True,
                            "case": True,
                            "comment": "Enter all symbols",
                            "body": self.api.String.Base64Encode(img_data)
                        }
                })
            ).content)
            self.d('captcha task id %s', task_data['taskId'])

            task_result = self.get_anti_captcha(task_data['taskId'])
            if 'solution' in task_result:
                attemps = attemps - 1
                self.d('captcha task solution %s', task_result)
                form_data['rep'] = task_result['solution']['text']
                url_parts = list(urlparse(self.conf.extras.captcha))
                url_parts[4] = urllib.urlencode(form_data)
                res = self.api.HTTP.Request(urlunparse(url_parts), headers=self.c.kinopoisk.main.headers)
                if 'status=failed' in res.url and attemps > 0:
                    self.report_captcha(task_data['taskId'])
                    return self.solve_captcha(res, attemps)
                else:
                    return res
            return None

    def update(self, metadata, *args):
        self.l('update from KPTrailersSource')
        if self.app.agent_type != 'movie':
            return

        try:
            limit = int(self.api.Prefs['trailer_limit'] or 0)
            if limit == 0:
                return
        except:
            self.d('error while parsing trailer limit %s', self.api.Prefs['trailer_limit'])

        extras = []
        TYPE_ORDER = ['scene_or_sample', 'interview', 'behind_the_scenes', 'trailer']
        TYPE_MAP = {'trailer': self.api.TrailerObject,
                    'interview': self.api.InterviewObject,
                    'behind_the_scenes': self.api.BehindTheScenesObject,
                    'scene_or_sample': self.api.SceneOrSampleObject}

        video_page = self.api.HTTP.Request(
            self.conf.extras.base % metadata['id'],
            headers=self.c.kinopoisk.main.headers())

        if 'showcaptcha' in video_page.url:
            self.d('CAPTCHA %s', video_page.url)
            if self.api.Prefs['captcha_key']:
                video_page = self.solve_captcha(video_page, 5)

        page = self.api.HTML.ElementFromString(video_page.content)

        if len(page) != 0:
            self.d('searching for videos')
            tv_match = re.compile(u"сезон (?P<season>\d{1,2})(?:.*эпизод (?P<episode>\d{1,2}))?")
            params = {}
            for link in page.xpath(self.conf.extras.re):
                vid = link.get('href').split('/')[-2]
                params[int(vid)] = {'d': (metadata['id'], vid, self.api.Util.Random()), 'n': link.text}
            if not params:
                return

            trailers = {}
            for p in self.chunks(params, 80):
                trailers.update(self._fetch_json(
                    self.conf.extras.url % self.make_request(p),
                    headers=self.conf.extras.headers()
                ))

            for key, trailer in trailers.iteritems():
                season = episode = None
                title = params[trailer['id']]['n']
                clip_type = self.extra_type(title.lower())

                self.d('trailer %s, %s', title, clip_type)

                #try:
                #    trailer_id = urlparse(trailer['url']).path.rpartition('/')[2]
                #except:
                #    self.d('error parsing trailer url %s', trailer['url'])
                #    trailer_id = None

                tv_res = tv_match.search(title)
                if tv_res:
                    season, episode = tv_res.groups()

                if clip_type:
                    extras.append({
                        'type': clip_type,
                        'views': trailer['views'],
                        'season': season,
                        'episode': episode,
                        'extra': TYPE_MAP[clip_type](
                            title=title,
                            url=trailer['streamUrl'],
                            thumb='https:' + trailer['img'].get('bigPreviewUrl', {}).get('x1', '')
                        )
                    })
        metadata['clips']['kp'] = sorted(extras, key=lambda x: (TYPE_ORDER.index(x['type']), x['views']), reverse=True)
