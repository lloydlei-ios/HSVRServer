#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from asyncio.events import AbstractEventLoop

from socketserver import ThreadingMixIn
from http.server import HTTPServer ,BaseHTTPRequestHandler
import urllib,io,shutil,subprocess
import threading
import os
import sys
import time
import asyncio

from hsvrbase import println
from hsvrbase import AppConf
from hsvrbase import decr_time_elapsed_ms

from hsvrreq import ReqManager
from hsvrdecrproc import decrmanager ,DecrProcManager
from hsvrdispatch import DispatchManager
from hsvrview import ViewManager
from hsvrresp import RespManager

__all__=["Hsvr"]

class HsvrThreadingHttpServer(ThreadingMixIn, HTTPServer):
    pass

HsvrServer=HsvrThreadingHttpServer

class HsvrHttpRequestHandler( BaseHTTPRequestHandler ):
    
    @decr_time_elapsed_ms
    @decrmanager.filter_http_get
    def do_GET(self):
        println("http request handler GET current thread ={} active_threads={} path = {} ,query= {}" .format(threading.current_thread().getName(),threading.active_count(),self.uri,str(self.query_str)))
        
        DispatchManager.dispatchGetUri(self)

    @decr_time_elapsed_ms
    @decrmanager.filter_http_post
    def do_POST(self):    
        println("http request handler POST current thread =%s active_threads=%d path = %s ,query= %s" % (threading.current_thread().getName(),threading.active_count(),self.uri,self.query_str))
        DispatchManager.dispatchPostUri(self)

HsvrReqHandler=HsvrHttpRequestHandler 

class Hsvr:
    app_conf = AppConf.get_instance()
    _decrprocmanager=DecrProcManager.get_instance()
    get = _decrprocmanager.reg_action_get
    post= _decrprocmanager.reg_action_post
    filters = _decrprocmanager.reg_filter_func
    view = _decrprocmanager.reg_view
    http_server=None
    def run(self):
        if self.http_server is None:
            raise Exception("http server is None")
        else:
            self.http_server.serve_forever()

    def __init__(self):
        _conf_http_server_ip=self.app_conf.get_conf("http_server","http_server_ip","0.0.0.0")
        _conf_http_server_port=self.app_conf.get_conf("http_server","http_server_port","8000")
        self.http_server=HsvrServer((_conf_http_server_ip,int(_conf_http_server_port)),HsvrReqHandler) 
 

def sync_run (): 
        app = Hsvr()
        println("start ... port ",app.http_server.server_port)
        
        @app.get("/action/home")
        def home(http_handler):
            RespManager.resp_error_status(http_handler,200 ,"welcome get home")
        @app.post("/action/home")
        def home(http_handler):
            RespManager.resp_error_status(http_handler,200 ,"welcome post home")

        app.run()

if __name__ == "__main__" :

    import asyncio

    async def run_async(app: "Hsvr"):
        loop: AbstractEventLoop = asyncio.get_running_loop()
        println("start ... port ", app.http_server.server_port)

        @app.get("/action/home")
        def home(http_handler):
            RespManager.resp_error_status(http_handler, 200, "welcome get home")

        @app.post("/action/home")
        def home(http_handler):
            RespManager.resp_error_status(http_handler, 200, "welcome post home")

        # 将阻塞的 serve_forever 放到线程执行器中运行，避免阻塞事件循环
        server_future = loop.run_in_executor(None, app.run)
        try:
            await server_future  # 正常情况下不会返回，除非调用 shutdown()/取消任务
        except asyncio.CancelledError:
            println("serve_forever cancelled, shutting down gracefully...")
        finally:
            try:
                app.http_server.shutdown()
                app.http_server.server_close()
            except Exception:
                pass
            println("server closed.")

    app = Hsvr()
    import hsvr_sample_actions
    try:
        asyncio.run(run_async(app))
    except KeyboardInterrupt:
        println("KeyboardInterrupt received, shutting down...")
        try:
            app.http_server.shutdown()
            app.http_server.server_close()
        except Exception as ex:
            println("shutdown error:", repr(ex))



   