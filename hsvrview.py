#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import shutil
import os
import threading
from hsvrbase import println
from typing import Dict, Any

class ViewManager :

    @staticmethod #TODO 缓存
    def create_html_replace_view(view_html_path: str = "./views/index.html", v_params: Dict[str, Any] = {}) -> str :
        """
        替换式模板渲染：
        - 模板占位形如 {#(key)#}
        - 自动注入 {#(view_html_path)#} 为模板真实路径
        - 失败时返回错误提示 HTML
        """
        try:
            path_abs = os.path.abspath(view_html_path).replace("\\", "/")
            if not os.path.exists(path_abs):
                return '<b aliagn="center">模板解析失败，文件不存在：{}</b>'.format(path_abs)
            with open(path_abs, "r", encoding="utf-8") as view:
                view_template = view.read()

            params = {'{#(view_html_path)#}': path_abs}
            for k, v in (v_params or {}).items():
                params["{#(" + str(k) + ")#}"] = str(v)

            for k, v in params.items():
                view_template = view_template.replace(k, v)

            return view_template
        except Exception as ex:
            return '<b aliagn="center">模板解析失败，{}</b>'.format(ex)

    @staticmethod #TODO 缓存
    def create_html_format_view(view_html_path: str = "./views/index.html", v_params: Dict[str, Any] = {}) -> str :
        """
        保留兼容利用字符串的格式化替换式模板渲染。
        """
        println(">>>>> params={}".format(repr(v_params)))
        with open(view_html_path,"rb+")  as view :
            view_template = "".join([str(line_bytes,encoding="utf-8") for line_bytes in view.readlines()])
            params = {}
            params[r'#(view_html_path)#']=view_html_path
            [params.__setitem__("#("+str(k) + ")#",v) for k,v in v_params.items()]
            println(">>>>> params={}".format(repr(params)))
            try:
                view_template = view_template.format(**params)
            except Exception as ex:
                return '<b aliagn="center">模板解析失败，{}</b>'.format(ex)
            else:    
                return view_template

    @staticmethod
    def resp_rendered_html(http_handler, html: str) -> None:
        """
        将已渲染的 HTML 输出到响应：
        - 统一使用 UTF-8 编码
        - 设置 Content-Type 与 Content-Length
        """
        enc = "UTF-8"
        encoded = html.encode(enc)
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        println("http handler GET resp html current thread =%s" % threading.current_thread().getName())
        http_handler.send_response(200)
        http_handler.send_header("Content-type", "text/html; charset=%s" % enc)
        http_handler.send_header("Content-Length", str(len(encoded)))
        http_handler.end_headers()
        shutil.copyfileobj(f, http_handler.wfile)

if __name__=="__main__":
    view_html_path = os.path.abspath("./views/hello.html")
    out=ViewManager.create_html_format_view(view_html_path,v_params={"name":"lloyd"})
    println(out)
