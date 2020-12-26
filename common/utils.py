#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# file:utils.py
# author: menglong.zhou@qunar.com
# 2020/12/23 10:12 PM

class SingletonDict(dict):
    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = dict.__new__(cls)
            return cls._instance
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'Singleton_lock'):
            self.Singleton_lock = True
            super(SingletonDict, self).__init__()