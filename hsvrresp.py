#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gzip import GzipFile
import shutil
import io
import threading
import json
import os 
from hsvrbase import println
import mimetypes
from hsvrbase import AppConf

class RespManager:
    @staticmethod
    def _is_client_abort(ex) -> bool:
        """
        判断是否为客户端主动断开导致的异常（无需打印堆栈）。
        """
        return isinstance(ex, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError))

    @staticmethod
    def _log_client_abort(http_handler, ex, context=""):
        """
        记录简要的客户端断开信息，不打印堆栈。
        """
        try:
            println(">>>>> client aborted during {} -- {}".format(context, str(ex)))
        except Exception:
            pass

    @staticmethod
    def resp_static_file(http_handler,static_file_path=".") :
        """
        静态文件响应：
        - 自动推断并设置 Content-Type
        - 小文件一次复制，大文件按生成器分块边读边写，降低内存占用
        """
        if not os.path.exists(static_file_path):
            RespManager.resp_error_status(http_handler)
            return
        file_len = os.path.getsize(static_file_path)
        println(">>>>> copy static_file_path:{}  -> to resp stream".format(static_file_path))
        http_handler.send_response(200)
        
        #http_handler.send_header("Content-type", "text/html; charset=utf-8")
        
        http_handler.send_header("Connection", "keep-alive")
        # 根据文件扩展名自动设置 Content-Type
        ctype, _ = mimetypes.guess_type(static_file_path)
        if ctype:
            http_handler.send_header("Content-type", ctype)
        
        if file_len < 2*1024*1024:
            with open(static_file_path,'rb') as fsrc:
                http_handler.send_header("Content-Length", str(file_len))
                http_handler.end_headers()
                try:
                    shutil.copyfileobj(fsrc,http_handler.wfile)
                except Exception as ex:
                    if RespManager._is_client_abort(ex):
                        RespManager._log_client_abort(http_handler, ex, "resp_static_file(small)")
                        return
                    else:
                        raise
        else:
            # 超过2m的文件使用协程读取，减小内存使用 或使用gzip压缩文件。静态加速
            # gzip_file_path = static_file_path+".httpgzip"
            # if not os.path.exists(gzip_file_path) :
                http_handler.send_header("Content-Length", str(file_len))
                http_handler.end_headers()
                #println(">>>>> wfile >>>>> fileno =",repr(http_handler.wfile.fileno()))
                with open(static_file_path,'rb') as fsrc:
                    for _bytes in RespManager.resp_static_file_bytes_read(http_handler,fsrc) : 
                        if not _bytes:
                            break
                        try:
                            http_handler.wfile.write(_bytes)
                            http_handler.wfile.flush()
                        except Exception as ex:
                            if RespManager._is_client_abort(ex):
                                RespManager._log_client_abort(http_handler, ex, "resp_static_file(large)")
                                break
                            else:
                                raise
            #     with open(static_file_path+".httpgzip","wb+") as f_gzip :
            #         f_gzip.write(RespManager.gzip_compress(all_bytes))   

            #     println(">>>>> create httpgzip  over.....")
            # else:
            #     http_handler.send_header("Content-Encoding","gzip") 
            #     file_len = os.path.getsize(static_file_path+".httpgzip")
            #     http_handler.send_header("Content-Length", str(file_len))
            #     http_handler.end_headers()

            #     with open(static_file_path+".httpgzip","rb+") as f_gzip:
            #         for gzip_bytes in RespManager.resp_static_file_bytes_read(http_handler,f_gzip) : 
            #             http_handler.wfile.write(gzip_bytes)
            #     println(">>>>> resp httpgzip over.....")
                

    @staticmethod
    def gzip_compress(buf):
        import gzip
        import io
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode="wb") as f:
            f.write(buf)
        return out.getvalue()

   
    @staticmethod
    def resp_static_file_bytes_read(http_handler,fsrc) :
        """
        以固定大小（2MB）分块读取文件，用于大文件边读边写响应。
        """
        while True :
            _bytes = fsrc.read(2*1024*1024)
            yield _bytes
            if len(_bytes) == 0 :
                println("resp_static_file_bytes  over ")
                break            
            
    @staticmethod
    def resp_error_status(http_handler,status_code=404,html="<B>Page was Not found</B>") :
        """
        错误响应（HTML）：
        - status_code：HTTP状态码
        - html：错误页面内容
        """
        enc = "UTF-8"
        encoded = html.encode(enc)
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        println("http handler GET resp_404 current thread =%s" % threading.current_thread().getName())
        http_handler.send_response(status_code)
        http_handler.send_header("Content-type", "text/html; charset=%s" % enc)
        http_handler.send_header("Content-Length", str(len(encoded)))
        http_handler.end_headers()
        try:
            shutil.copyfileobj(f, http_handler.wfile)
        except Exception as ex:
            if RespManager._is_client_abort(ex):
                RespManager._log_client_abort(http_handler, ex, "resp_error_status")
                return
            else:
                raise

    @staticmethod
    def resp_json_result(http_handler,status_code=200,return_code=0,return_message="success",data={}) :
        """
        JSON 响应：
        - 统一返回结构：ret_code、ret_msg、data
        - Content-Type 设置为 application/json
        """
        enc = "UTF-8"
        json_data= json.dumps(data,ensure_ascii=False)
        json_result= '{"ret_code":%d,"ret_msg":"%s","data":%s}' % (return_code,return_message,json_data)
        encoded = json_result.encode(enc)
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        println("http resp_json_result={} current thread ={}".format(encoded, threading.current_thread().getName()))
        http_handler.send_response(status_code)
        http_handler.send_header("Content-type", "application/json; charset={}".format(enc))
        http_handler.send_header("Content-Length", str(len(encoded)))
        http_handler.end_headers()
        try:
            shutil.copyfileobj(f, http_handler.wfile)
        except Exception as ex:
            if RespManager._is_client_abort(ex):
                RespManager._log_client_abort(http_handler, ex, "resp_json_result")
                return
            else:
                raise

    @staticmethod
    def create_html_format_view(view_uri="/views/index.html",**kwargs) :
        """
        简易模板渲染（format）：
        - 优先使用 conf.ini 的 http_server_views_dir 作为视图根目录
        - 回退到 ./views 保持兼容
        """
        # 优先配置的视图根路径
        views_root_conf = AppConf.get_instance().get_conf("http_server","http_server_views_dir","./httpserver/views")
        view_base = os.path.abspath(views_root_conf)
        if not os.path.isdir(view_base):
            # 回退到原有硬编码路径，确保兼容
            view_base = os.path.abspath("./views")
        println(">>>>> view_path={}".format(view_base))
        try:
            with open(os.path.join(view_base, view_uri.lstrip("/")), encoding="utf-8") as view:
                view_template ="\n".join(view.readlines())
                println(">>>>> view_template={}".format(view_template))
                kwargs["view_uri"]=view_uri
                println(kwargs)
                view_template = view_template.format(**kwargs)
                return view_template
        except Exception as ex:
            return "<b aliagn='center'>模板解析失败，{}</b>".format(ex)

    @staticmethod
    def resp_rendered_html(http_handler,html,view_uri="/views/index.html"):
        """
        渲染后的 HTML 响应：
        - 以 UTF-8 编码写出
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
        try:
            shutil.copyfileobj(f, http_handler.wfile)
        except Exception as ex:
            if RespManager._is_client_abort(ex):
                RespManager._log_client_abort(http_handler, ex, "resp_rendered_html")
                return
            else:
                raise
    
    @staticmethod
    def resp_redirect_status(http_handler,status_code=301,location="/index.html") :
        """
        重定向 到参数location的地址
        """
        enc = "UTF-8"
        println("http handler GET resp_301 current thread =%s" % threading.current_thread().getName())
        http_handler.send_response(status_code)
        http_handler.send_header("Content-type", "text/html; charset=%s" % enc)
        http_handler.send_header("Location", location)
        http_handler.end_headers()
