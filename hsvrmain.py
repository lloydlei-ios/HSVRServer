#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib,io,shutil,subprocess
import threading
import os
import sys

from hsvrbase import println
from hsvrresp import RespManager
from hsvrserver import Hsvr

def sync_run ():
    app = Hsvr()
    try:
        println("start ... port ",app.http_server.server_port)
        port = app.http_server.server_port
        @app.get("/action/home")
        def home(http_handler):
            RespManager.resp_error_status(http_handler,200 ,"welcome get home")
        @app.post("/action/home")
        def home(http_handler):
            RespManager.resp_error_status(http_handler,200 ,"welcome post home")
        visit_url = "http://localhost:{}/switchhost".format(port)
        println('please visit switchhost by url [{}]'.format(visit_url))
        #import webbrowser
        #webbrowser.open(visit_url, new=1, autoraise=True) 
        app.run()

    except KeyboardInterrupt:
        println("KeyboardInterrupt received, shutting down...")
        try:
            app.http_server.shutdown()
            app.http_server.server_close()
        except Exception as ex:
            println("shutdown error:", repr(ex))
    except Exception as ex:
        import traceback,time
        msg = traceback.format_exc()
        println("><><> run exception :\n" ,msg)
        time.sleep(5*60)
    
if __name__ == "__main__" :
    #注册actions
    from hsvr_sample_actions import *
    from hsvr_sample_views import *
    from hsvr_sample_filters import *
    from hsvr_switchhost import *
    
    # sync_run()

    import asyncio

    async def run_async(app: "Hsvr"):
        loop = asyncio.get_running_loop()
        server_future = loop.run_in_executor(None, app.http_server.serve_forever)
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


