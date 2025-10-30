
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import os
import traceback

from hsvrbase import println
from hsvrbase import AppConf
from hsvrresp import RespManager 
from hsvrview import ViewManager
from hsvrdecrproc import DecrProcManager,decrmanager
from hsvrreq import ReqManager

class DispatchManager:
    """
    路由分发管理器：
    - 根据 URI 和 HTTP 方法分发到静态文件、action 处理函数或 view 渲染函数
    - 统一 GET/POST 分发逻辑，减少重复代码
    """

    @staticmethod
    def _resolve_static_path(uri: str, uri_static: str, static_dir: str) -> str:
        """
        计算静态文件的本地路径，并做目录穿越防护：
        - 当请求路径为 /static 或 /static/ 时返回 index.html
        - 只允许访问 static_dir 目录下的文件
        """
        file_path = uri.replace(uri_static, "")
        file_path = "/index.html" if len(file_path) <= 1 else file_path
        static_root = os.path.abspath(static_dir).replace("\\", "/")
        static_local_file_path = os.path.abspath((static_dir + file_path)).replace("\\", "/")

        # 目录穿越防护：只允许在 static_root 下
        if not static_local_file_path.startswith(static_root):
            println(f">>>>> static path violated: {static_local_file_path} not under {static_root}")
            return ""
        return static_local_file_path

    @staticmethod
    def _dispatch(http_handler, method: str):
        """
        统一分发实现：
        - method: 'GET' or 'POST'
        """
        app_conf = AppConf.get_instance()
        uri_static = app_conf.get_conf("http_server", "http_server_uri_static", "/static")
        static_dir = app_conf.get_conf("http_server", "http_server_static_dir", "./static")
        uri_action = app_conf.get_conf("http_server", "http_server_uri_action", "/action")
        uri_views = app_conf.get_conf("http_server", "http_server_uri_views", "/views")

        dm = DecrProcManager.get_instance()
        uri = http_handler.uri

        # 1) 静态资源
        if uri == uri_static or uri.startswith(uri_static + "/"):
            static_local_file_path = DispatchManager._resolve_static_path(uri, uri_static, static_dir)
            if not static_local_file_path:
                RespManager.resp_error_status(http_handler, 403, "<B>Forbidden</B>")
                return
            println(f">>>>> request uri={uri}, response static_local_file_path={static_local_file_path}")
            RespManager.resp_static_file(http_handler, static_local_file_path)
            return

        # 2) 自定义注册的 action（完整匹配）
        if method == "GET" and uri in dm.actions_get:
            action = decrmanager.get_action_get(uri)
            action(http_handler)
            return
        if method == "POST" and uri in dm.actions_post:
            action = decrmanager.get_action_post(uri)
            if action is None:
                RespManager.resp_error_status(http_handler, 404)
            else:
                action(http_handler)
            return

        # 3) /action/* 前缀的 action
        if uri.startswith(uri_action):
            action = decrmanager.get_action_get(uri) if method == "GET" else decrmanager.get_action_post(uri)
            println(">>>>> action >>>>> " + repr(action))
            if action is None:
                RespManager.resp_error_status(http_handler, 404)
            else:
                action(http_handler)
            return

        # 4) /views/* 前缀的 view
        if uri.startswith(uri_views):
            view = dm.get_view(uri)
            if view is None:
                RespManager.resp_error_status(http_handler, 404)
            else:
                view(http_handler)
            return

        # 5) 指定的 URI 注册的 view（完整匹配）
        view = dm.get_view(uri)
        if view is not None:
            view(http_handler)
            return

        # 6) 其他：404
        println(f"http request handler {method} uri[{uri}] not found")
        RespManager.resp_error_status(http_handler, 404)

    @staticmethod
    def dispatchGetUri(http_handler):
        """
        GET 请求分发入口
        """
        DispatchManager._dispatch(http_handler, "GET")

    @staticmethod
    def dispatchPostUri(http_handler):
        """
        POST 请求分发入口
        """
        DispatchManager._dispatch(http_handler, "POST")
