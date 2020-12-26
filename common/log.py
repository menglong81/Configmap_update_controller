#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# file:log.py
# author: menglong.zhou@qunar.com
# 2020/12/23 10:10 PM

from common.config import CONF

import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys


class AppLog(object):
    logger_dict = dict()

    def __init__(self, log_name, mode, level, rotating=True, when='MIDNIGHT'):
        self.log_path = CONF['log_path']
        self.log_level = level
        self.logger = logging.getLogger(log_name)

        if self.log_level == 'DEBUG':
            formatter = logging.Formatter('%(asctime)s %(module)s %(funcName)s %(levelname)-8s: %(message)s')
        else:
            formatter = logging.Formatter('%(asctime)s %(module)s %(levelname)-8s: %(message)s')

        if rotating is True:    # 日志轮转默认按天
            self.file_handler = TimedRotatingFileHandler(os.path.join(self.log_path, log_name), when)
        else:   # 不轮转
            self.file_handler = logging.FileHandler(os.path.join(self.log_path, log_name))

        self.file_handler.setFormatter(formatter)
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.formatter = formatter
        self.logger.setLevel(getattr(logging, self.log_level))
        if mode == 'file':
            self._register_file()
        elif mode == 'console':
            self._register_console()
        elif mode == 'all':
            self._register_console()
            self._register_file()
        self.logger.debug('register {log_name}'.format(log_name=log_name))

    def _register_file(self):
        self.logger.addHandler(self.file_handler)

    def _register_console(self):
        self.logger.addHandler(self.console_handler)

    @classmethod
    def register(cls, log_name, log_type, log_level):
        if log_name not in cls.logger_dict:
            cls.logger_dict.__setitem__(log_name, cls(log_name, log_type, log_level))
        return cls.logger_dict[log_name]


MAIN_LOG = AppLog.register('hotupdate.log', 'all', CONF['log_level'])