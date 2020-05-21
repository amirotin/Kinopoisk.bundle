# -*- coding: utf-8 -*-
import re, unicodedata

from fuzzywuzzy import fuzz, process

# Регулярка для выделения года из строки
EXTRACT_YEAR_REGEXP = re.compile('((19|20)\d{2})')


def extract_year(value):
    """
    Функция выделения года из строки, числа или массива, в случае некорректных данных возвращает 0
    @param value: значение, из которого необходимо выделить год
    @type value: int or str or unicode or list or tuple
    @return: Возвращает год в типе int
    @rtype: int
    """
    # Если значение пустое(пустой массив, строка или 0), возвращаем 0
    if not value:
        return 0
    # Если нам передали число, возвращаем его же
    if isinstance(value, int):
        return value

    # Если нам передали строку, пытаемся выделить из нёё год
    if isinstance(value, (str, unicode)):
        m = EXTRACT_YEAR_REGEXP.match(value)
        if m:
            return int(m.groups()[0])
        else:
            return 0

    # Если внезапно "прилетел" массив(такое бывает в редких случаях, то выбираем первый элемент и прогоняем его
    # через эту функцию
    if isinstance(value, (list, tuple)):
        return extract_year(value[0])


class Scoring(object):
    def __init__(self, app):
        self.app = app
        self.api = app.api
        self.c = app.c
        self.l = app.api.Log
        self.trace = app.trace

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
        mediayear = extract_year(fileyear)
        year = extract_year(entry[2])
        if mediayear and year:
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
        medianame = unicode(media.name if self.app.agent_type == 'movie' else media.show)
        self.trace('score %s (%s) with matches %s', medianame, media.year, str(matches))
        name_type = 1 if self._is_valid(unicode(medianame)) else 0
        score_data = {n:k[name_type] for n,k in matches.items()}
        self.trace('score_data = %s', score_data)
        res = process.extract(unicode(medianame), score_data, scorer=fuzz.UWRatio, limit=15)
        for r in res:
            matches[r[2]][4] += r[1]
            matches[r[2]][4] -= matches[r[2]][3] * self.c.score.penalty.rating
            self.score_year(matches[r[2]], media.year)