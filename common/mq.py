#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# file:mq.py
# author: menglong.zhou@qunar.com
# 2020/12/23 10:16 PM

import queue

class Q(object):

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Q, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # if not hasattr(self, 'lock'):
        self.q = queue.Queue()
        # self.lock = True

    def put(self, obj):
        # print 'self.q.qsize()', self.q.qsize()
        return self.q.put_nowait(obj)

    def get(self):
        obj = self.q.get()
        self.q.task_done()
        return obj


if __name__ == '__main__':
    Q.put({'msg': 1})
