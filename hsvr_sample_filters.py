#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from hsvrbase import println
from hsvrbase import AppConf
from hsvrresp import RespManager
from hsvrserver import Hsvr

@Hsvr.filters
def first_filter_check(http_handler):
    #restresp.resp_json_result(http_handler,403,0,"forbidden",{"first_filter_check":"true"})
    #   return False
    println (">>>>> first_filter_check http_handler uri={},params={} ".format(http_handler.uri,repr(http_handler.params)))
    return True

@Hsvr.filters
def second_filter_check(http_handler):
    println (">>>>> second_filter_check http_handler uri={},params={} ".format(http_handler.uri,repr(http_handler.params)))
    return True
