#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from hsvrbase import AppConf
from hsvrbase import println
from hsvrresp import RespManager 
from hsvrview import ViewManager
from hsvrdecrproc import DecrProcManager,decrmanager
from hsvrreq import ReqManager
from hsvrserver import Hsvr

@Hsvr.get("/action/info")
def info(http_handler):
    RespManager.resp_json_result(http_handler,200,0,"ok",{"info":"rest info"})

@Hsvr.get("/act/hello")
def act_hello(http_handler):
    RespManager.resp_json_result(http_handler,200,0,"ok",{"get_act_hello":"rest act_hello"})


@Hsvr.post("/act/hello") #装饰之后实际的函数名不再是act_hello
def act_hello(http_handler):
    RespManager.resp_json_result(http_handler,200,0,"ok",{"post_act_hello":"rest act_hello"})

@Hsvr.post("/action/test2")
def upload(http_handler):
    content_type=http_handler.content_type
    println(">>>>> post filter_pre_check_result",repr(http_handler.filter_pre_check_result))
    println(">>>>> post content-length=",repr(http_handler.content_length))
    println(">>>>> post content-type=",repr(http_handler.content_type))
    println(">>>>> post form_params",repr(http_handler.form_params))
    println(">>>>> post form_files",repr(http_handler.form_files))
    
    RespManager.resp_error_status(http_handler,200 ,"post over")

@Hsvr.post("/action/upload")
def upload(http_handler):
    content_type=http_handler.content_type
    println(">>>>> upload_by_form_data post content-type=",repr(content_type))
    if content_type  :
        println(">>>>> post filter_pre_check_result",repr(http_handler.filter_pre_check_result))
        println(">>>>> post content-length=",repr(http_handler.content_length))
        println(">>>>> post content-type=",repr(http_handler.content_type))
        println(">>>>> post form_params",repr(http_handler.form_params))
        println(">>>>> post form_files",repr(http_handler.form_files))
        RespManager.resp_error_status(http_handler,200 ,"upload over")
    else :
        RespManager.resp_error_status(http_handler,500 ,"upload error,content-type error")
    
