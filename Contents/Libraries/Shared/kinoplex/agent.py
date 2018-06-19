# -*- coding: utf-8 -*-
from .sources import SourceBase
from scoring import Scoring

class KinoPlex(object):
    def __init__(self):
        super(KinoPlex, self).__init__() # make init call for agentkit
        self.score = Scoring(self)
        self.meta_id = None
        self.sources = [src(self) for src in SourceBase.getAll()]

    def fire(self, event, *args, **kwargs):
        self.api.Log('fired %s with params: %s', event, args)
        [getattr(s, event)(*args, **kwargs) for s in self.sources]