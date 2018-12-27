# -*- coding: utf-8 -*-
from base import SourceBase
from urlparse import urlparse, parse_qs

class KPTrailersSource(SourceBase):
    def __init__(self, app):
        super(KPTrailersSource, self).__init__(app)

    def extra_type(self, extra):
        return {
            extra.find(u'трейлер') >= 0: 'trailer',
            extra.find(u'фрагмент') >= 0: 'scene_or_sample',
            extra.find(u'съёмках') >= 0: 'behind_the_scenes',
            extra.find(u'интервью') >= 0: 'interview'
        }.get(True, None)

    def make_request(self, params):
        param_str = ''
        for id, data in params.iteritems():
            param_str += '%s,%s,rnd-%s;' % data['d']
        return self.api.String.Quote(param_str[:-1])

    def update(self, metadata, media, lang, force=False, periodic=False):
        self.l('update from KPTrailersSource')
        extras = []
        TYPE_ORDER = ['scene_or_sample', 'interview', 'behind_the_scenes', 'trailer']
        TYPE_MAP = {'trailer': self.api.TrailerObject,
                    'interview': self.api.InterviewObject,
                    'behind_the_scenes': self.api.BehindTheScenesObject,
                    'scene_or_sample': self.api.SceneOrSampleObject}

        video_page = self.api.HTTP.Request(
            self.c.kinopoisk.extras.base % metadata['id'],
            headers=self.c.kinopoisk.main.headers(),
            follow_redirects=False)

        redirect = video_page.get_redirect_location()
        if redirect:
            if 'showcaptcha' in redirect:
                redirect = redirect.replace('https://www.kinopoisk.ru/showcaptcha?cc=1&repath=', '').replace('%3A', ':')
            else:
                redirect = 'https://www.kinopoisk.ru%s' % redirect
            video_page = self.api.HTTP.Request(redirect, headers=self.c.kinopoisk.main.headers())

        # list of trailers for movie
        page = self.api.HTML.ElementFromString(video_page.content)

        if len(page) != 0:
            params = {}
            # form array of id+name
            for link in page.xpath(self.c.kinopoisk.extras.re):
                id = link.get('href').split('/')[-2]
                params[int(id)] = {
                    'd': (metadata['id'], id, self.api.Util.Random()),
                    'n': link.text
                }
            if not params:
                return

            # get trailers data
            trailers = self._fetch_json(
                self.c.kinopoisk.extras.url % self.make_request(params),
                headers=self.c.kinopoisk.extras.headers()
            )
            # form extras array
            for key, trailer in trailers.iteritems():
                title = params[trailer['id']]['n']
                clip_type = self.extra_type(title.lower())
                if clip_type and 'yandexVideoId' in trailer:
                    extras.append({
                        'type': clip_type,
                        'views': trailer['views'],
                        'extra': TYPE_MAP[clip_type](
                            title=title,
                            url=self.c.kinopoisk.extras.clip_url % trailer['yandexVideoId'],
                            thumb='https:' + trailer['img'].get('bigPreviewUrl', {}).get('x1', '')
                        )
                    })
        metadata['kp_extras'] = sorted(extras, key=lambda x: (TYPE_ORDER.index(x['type']), x['views']), reverse=True)
