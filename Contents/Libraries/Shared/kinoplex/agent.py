# -*- coding: utf-8 -*-
from kinoplex.sources import SourceBase
from kinoplex.scoring import Scoring


class KinoPlex(object):
    def __init__(self):
        super(KinoPlex, self).__init__()
        self.trace('%s init', self.__class__.__name__)
        self.score = Scoring(self)
        self.sources = [src(self) for src in SourceBase.getAll()]

    def fire(self, event, *args, **kwargs):
        self.trace('fired %s with params: %s', event, args)
        [getattr(s, event)(*args, **kwargs) for s in self.sources]

    def quick_search(self, results, media, lang, manual, primary):
        self.trace('perform quick search on filename %s', media.filename)
