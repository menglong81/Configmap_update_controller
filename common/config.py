#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# file:config.py
# author: menglong.zhou@qunar.com
# 2020/12/23 10:12 PM
import sys
import os
import yaml

from common.utils import SingletonDict


class ConfigBase(SingletonDict):
    def __init__(self):
        self.range = dict()
        super(ConfigBase, self).__init__()
        self.parse()

    def parse(self):
        '''
        All config class run method
        '''
        raise NotImplementedError('%s not found "parse()" method' % self.__class__)

    def check_config(self):
        for k in self:
            if self.range.get(k, None) is not None:
                if self[k] not in self.range[k]:
                    raise ValueError('Config "{k}: {v}" invalid, reference "{r}"'.format(k=k, v=self[k], r='|'.join(self.range[k])))

    def __setitem__(self, key, value, value_range=None):
        if value_range is not None:
            self.range[key] = value_range
        super(ConfigBase, self).__setitem__(key, value)


class ParseSysArgv(ConfigBase):
    '''
    Parse the parameters(sys.argv) when starting the program.
    '''
    def parse(self):
        argv = sys.argv
        for _e in argv:
            if _e.startswith('--') is True:
                _k, _v = _e.split('--')[-1].split('=')
                self.__setitem__(_k, _v)

        self.__setitem__('base_dir', os.path.dirname(argv[0]))


class ParseConfFile(ConfigBase):
    '''
    Parse config file
    Config file path is parse the parameters(sys.argv) when starting the program( --config-file='/etc/NAME.conf')
    '''

    def parse(self):
        sys_argv = ParseSysArgv()
        cfg_pth = sys_argv.get('config_file', 'conf/prod.conf')
        if cfg_pth is None:
            raise ValueError('--config_file is require!')
        self._default()
        self.update(yaml.load(open(cfg_pth, "r")))
        self.update(sys_argv)
        self.check_config()

    def _default(self):
        self.__setitem__('log_path', '/tmp/hotupdate')

        if sys.platform == "win32":
            self.__setitem__('log_path', "D:\\logs\\hotupdate")

        self.__setitem__('log_level', 'DEBUG', ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])


def config():
    _obj = ParseConfFile()
    return _obj

CONF = config()