#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os,sys

from hsvrbase import AppConf

from hsvrresp import RespManager 
from hsvrview import ViewManager
from hsvrdecrproc import DecrProcManager,decrmanager
from hsvrreq import ReqManager
from hsvrserver import Hsvr

@Hsvr.view()
def index(http_handler) :

    _http_server_views_dir=os.path.abspath(AppConf.get_instance().get_conf("http_server","http_server_views_dir","./views"))
    view_html_path = (_http_server_views_dir + "/index.html").replace("\\","/")
    if os.path.exists(view_html_path) == False :
        RespManager.resp_error_status(http_handler,404)
        return
    params_dict = ReqManager.get_dict_from_params_key_list(http_handler.params)
    html = ViewManager.create_html_replace_view(view_html_path,params_dict)
    ViewManager.resp_rendered_html(http_handler,html)

@Hsvr.view() #默认注册到 /views/hello
def hello(http_handler) :
    _http_server_views_dir=os.path.abspath(AppConf.get_instance().get_conf("http_server","http_server_views_dir","./views"))
    view_html_path = (_http_server_views_dir+ "/hello.html").replace("\\","/")
    if os.path.exists(view_html_path) == False :
        RespManager.resp_error_status(http_handler,404)
        return
    params_dict = ReqManager.get_dict_from_params_key_list(http_handler.params)
    html = ViewManager.create_html_replace_view(view_html_path,params_dict)
    ViewManager.resp_rendered_html(http_handler,html)

@Hsvr.view("/views2/hello")
def testview2(http_handler) :
    _http_server_views_dir=os.path.abspath(AppConf.get_instance().get_conf("http_server","http_server_views_dir","./views"))
    view_html_path = (_http_server_views_dir+ "/hello.html").replace("\\","/")
    if os.path.exists(view_html_path) == False :
        RespManager.resp_error_status(http_handler,404)
        return
    params_dict = ReqManager.get_dict_from_params_key_list(http_handler.params)
    html = ViewManager.create_html_replace_view(view_html_path,params_dict)
    ViewManager.resp_rendered_html(http_handler,html)

@decrmanager.reg_view()
def hello2(http_handler) :
    _http_server_views_dir=os.path.abspath(AppConf.get_instance().get_conf("http_server","http_server_views_dir","./views"))
    view_html_path = (_http_server_views_dir+ "/hello2.html").replace("\\","/")
    if os.path.exists(view_html_path) == False :
        RespManager.resp_error_status(http_handler,404)
        return
    params_dict = ReqManager.get_dict_from_params_key_list(http_handler.params)
    html = ViewManager.create_html_replace_view(view_html_path,params_dict)
    ViewManager.resp_rendered_html(http_handler,html)

