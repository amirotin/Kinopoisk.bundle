# -*- coding: utf-8 -*-
import re, unicodedata

from fuzzywuzzy import fuzz, process

class Scoring(object):
    def __init__(self, app):
        self.app = app
        self.api = app.api
        self.c = app.c
        self.l = app.api.Log

    def _is_permitted_char(self, char):
        cat = unicodedata.category(char)[0]
        if cat == 'L':
            return 'LATIN' in unicodedata.name(char, '').split()
        elif cat == 'N':
            return '0' <= char <= '9'
        elif cat in ('S', 'P', 'Z'):
            return True
        else:
            return False

    def score_year(self, entry, fileyear):
        yearpenalty = self.c.score.penalty.year / 3  # if we have no year
        mediayear = int(fileyear or 0)
        year = entry[2] if isinstance( entry[2], int ) else int(re.sub('[^0-9]', '', entry[2] or '0') or '0')
        if mediayear != 0 and year != 0:
            yeardiff = abs(mediayear - year)
            if yeardiff < 1:
                yearpenalty = 0
            else:
                if yeardiff == 1:
                    yearpenalty = int(self.c.score.penalty.year / 4)
                elif yeardiff == 2:
                    yearpenalty = int(self.c.score.penalty.year / 3)
                else:
                    yearpenalty = yeardiff * int(self.c.score.penalty.year / 4)
        entry[4] = entry[4] - yearpenalty

    def _is_valid(self, text):
        return all(self._is_permitted_char(c) for c in text)

    def score(self, media, matches):
        medianame = unicode(media.name)
        self.l('score %s with matches %s', medianame, str(matches))
        name_type = 1 if self._is_valid(unicode(medianame)) else 0
        score_data = {n:k[name_type] for n,k in matches.items()}

        res = process.extract(unicode(medianame), score_data, scorer=fuzz.UWRatio)
        for r in res:
            matches[r[2]][4] += r[1]
            matches[r[2]][4] -= matches[r[2]][3] * self.c.score.penalty.rating
            # score year mismatch
            self.score_year(matches[r[2]], media.year)