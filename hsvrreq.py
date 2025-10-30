#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import platform
import re
import traceback
import shutil
import io
import urllib
from hsvrbase import println

class ReqManager :
    """
    请求参数及请求体处理相关函数
    """
    @staticmethod
    def init_uri_and_params(http_handler):
        uri, _, query = http_handler.path.partition('?')
        http_handler.uri = urllib.parse.unquote(uri)
        params = urllib.parse.parse_qs(query)
        http_handler.params = params
    
    @staticmethod
    def get_req_uri(http_handler):
        """
        获取请求URI；若尚未初始化则调用初始化方法。
        """
        if getattr(http_handler, "uri", None):
            return http_handler.uri
        else:
            ReqManager.init_uri_and_params(http_handler)
            return http_handler.uri

    @staticmethod
    def get_req_query_params(http_handler):
        """
        获取查询参数；若尚未初始化则调用初始化方法。
        """
        if getattr(http_handler, "params", None):
            return http_handler.params
        else:
            ReqManager.init_uri_and_params(http_handler)
            return http_handler.params
        
    @staticmethod
    def get_dict_from_params_key_list(params={}):
        params_dict = {}
        [ params_dict.__setitem__(k, v[0] if v else "")  for k,v in params.items() ] 
        return params_dict  
        
    @staticmethod
    def post_with_form_data_multi_part(http_handler,upload_dir="./webserver/upload") :
        """
        处理 multipart/form-data 提交的请求

        multipart/form-data post body 样例：
    ----WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Disposition: form-data; name="name1"
    Content-Encoding: utf-8

    value1
    ----WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Disposition: form-data; name="name2"

    value2
    ----WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Disposition: form-data; name="file1"; filename="94b5b232gw1ewlx3p595wg20ak0574qq.gif"
    Content-Type: image/gif
    Content-Encoding: utf-8 
    
    ----WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Disposition: form-data; name="file2"; filename="1443175219259.jpg"
    Content-Type: image/jpeg
    
    ----WebKitFormBoundary7MA4YWxkTrZu0gW

        """
        path = os.path.abspath(upload_dir).replace("\\","/")
        if os.path.exists(path) == False :
            os.makedirs(path)
        # 更健壮的 boundary 解析
        ctype = http_handler.headers.get("Content-Type") or ""
        if "boundary=" not in ctype:
            return (False, "Content-Type missing multipart boundary")
        boundary = ctype.split("boundary=", 1)[1].encode("utf-8")

        remainbytes = int(http_handler.headers.get('Content-length') or 0)
        println(boundary,remainbytes)
        post_form_params={} #form params
        #post的body 第一行读取
        boundary_line = http_handler.rfile.readline()
        println("read line={}|{}".format(boundary_line,"first boundary") )
        remainbytes -= len(boundary_line)
        while boundary in boundary_line: 
            if remainbytes > 0:
                line = http_handler.rfile.readline() 
                println(">>>>> post [multipart/form-data] type(line)={},line={}".format(type(line),repr(line)))
                remainbytes -= len(line)
                trim_line = str(line,encoding="utf-8")
                #判断表单标记 是否为文件，并提取名称及文件名
                if "filename" not in trim_line :
                    fn_matchs =re.match( r'Content-Disposition: form-data; name="(.*)"\r\n', trim_line,re.I)
                else:
                    fn_matchs =re.match( r'Content-Disposition: form-data; name="(.*)"; filename="(.*)"\r\n', trim_line,re.I)
                println(">>>>> post [multipart/form-data] find name and filename fn_matchs={}".format(repr( fn_matchs.groups() )))
                fn_groups = fn_matchs.groups()
                if fn_matchs and len(fn_groups) ==1  : #表单标记非文件类型
                    key = fn_groups[0]
                    while True :
                        line = http_handler.rfile.readline() 
                        println(">>>>> post [multipart/form-data] > read line={}".format(line))
                        remainbytes -= len(line)
                        #读取到标记表单值的\r\n一行，则表示需要读取值了
                        if b"\r\n"== line :
                            println(">>>>> post [multipart/form-data] > start read form params key=[{}] value".format(key))
                            break
                    line = http_handler.rfile.readline() 
                    remainbytes -= len(line)
                    println(">>>>> post [multipart/form-data] > read line value ={},remainbytes={}".format(line,remainbytes))
                    
                    
                    if post_form_params.__contains__(key) :
                        post_form_params[key].append(str(line,encoding="utf-8").strip())
                    #    println("post name params={}".format(post_form_params[key]))
                    else :
                        post_form_params.__setitem__(key,[str(line,encoding="utf-8").strip()])
                    #println("post_form_params[{}]={}".format(key,post_form_params[key]) )
                    #标记表单值读取完毕，开始下一个分隔符行的读取
                    line = http_handler.rfile.readline()
                    remainbytes -= len(line)
                    #println("> read next form data line={},remainbytes={}".format(line,remainbytes))

                elif fn_matchs and len(fn_groups) > 1: #表单标记为文件类型
                    post_form_params.__setitem__(fn_groups[0],fn_groups[1]) #保存下文件类型标记名及文件名
                    while True :
                        line = http_handler.rfile.readline() 
                        #println(">> read line={}".format(line))
                        remainbytes -= len(line)
                        #读取到标记表单值的\r\n一行，则表示需要读取文件内容了
                        if b"\r\n"== line:
                            println(">>>>> post [multipart/form-data] >> start read form file filename=[{}] value".format(fn_groups[1]))
                            break
                    
                    println(">>>>> post [multipart/form-data] >> ---- save before {} remainbytes={}".format(fn_groups[1],remainbytes))
                    http_handler.upload_dir = upload_dir
                    http_handler.file_name = fn_groups[1]
                    http_handler.boundary=boundary
                    read_len,write_len,temp_file_path = ReqManager.upload_save_file(http_handler,fn_groups[1])
                    upload_file_dict={"file_name":fn_groups[1],"temp_file":temp_file_path}
                    http_handler.form_files.__setitem__(fn_groups[0],upload_file_dict)
                    remainbytes -= read_len
                    println(">>>>> post [multipart/form-data] >> ---- save over {} remainbytes={}, read_len={},total save len={}".format(fn_groups[1],remainbytes,read_len,write_len))
                    
                
                else:

                    line = http_handler.rfile.readline() 
                    println("><>< read line={}".format(line))
                    remainbytes -= len(line)
                    break
            else:
                http_handler.form_params=post_form_params
                println(">>>>> post [multipart/form-data] process over ,http_handler.form_params={}".format(repr(post_form_params))) 
                println(">>>>> post [multipart/form-data] process over ,http_handler.form_files={}".format(repr(http_handler.form_files))) 
                return (True, "Content upload over")
        
        return (False, "Content NOT begin with boundary")

    @staticmethod
    def upload_form_data_file_readline_yield(http_handler) :
        """
        按行读取上传的文件内容，遇到下一 boundary 终止。
        """
        need_break_flag = False
        
        while True :
            
            line = http_handler.rfile.readline()
            if line and http_handler.boundary in line :
                need_break_flag = True
            
            #println(">>>>> ** readline yield cur read line len={}".format(len(line)))
            yield (need_break_flag,line)
            if need_break_flag :
                println(">>>>> readline yield break http_handler.file_name={}".format(http_handler.file_name))
                return
    
    @staticmethod
    def upload_form_data_file_truncat(uped_file):
        """
        解决二进制文件最后两个字符\r\n需要剔除，，否则文件无法正常打开
        """
        uped_file.seek(-2 ,os.SEEK_END)
        last_2bytes=uped_file.read(2)
        println(">>>>> last >> type(uped_file.read(1)) ={}".format(last_2bytes))
        if  last_2bytes == b"\r\n" :
            uped_file.seek(-2 ,os.SEEK_END)
            uped_file.truncate()
            println(r">>>>> last \r\n removed")
        
        
    @staticmethod
    def upload_save_file(http_handler,file_name) :
        """
        保存 multipart 文件字段内容到临时文件，并在末尾进行 \r\n 截断处理。
        返回 (读取字节数, 写入字节数, 本地临时文件路径)
        """
        path = os.path.abspath(http_handler.upload_dir).replace("\\","/")
        if os.path.exists(path) == False :
            os.makedirs(path)
        write_len,read_len=0,0
        import time
        up_file_path = path +"/" +str(time.time()) + "_"+ file_name
        with open(up_file_path,"ab") as up_file :
            for (read_over_flag,line)  in ReqManager.upload_form_data_file_readline_yield(http_handler):
                read_len += len(line)
                #println(">>>>> ** readline yield return cur_read_len={},read_len={}".format(len(line),read_len))

                if not read_over_flag :
                    up_file.write(line)
                    write_len += len(line)
                    #println(">>>>> read yield flag[{}] read_len={} write_len={} write bytes to next...".format(read_over_flag,read_len,write_len))
                    
                else :
                    println(">>>>> read yield flag[{}] read_len={} write_len={} write over to next...".format(read_over_flag,read_len,write_len))
                    break

        with open(up_file_path,"rb+") as uped_file :
            ReqManager.upload_form_data_file_truncat(uped_file)
        
        return  (read_len,write_len,up_file_path)

    @staticmethod
    def upload_with_binary_yield_read(http_handler) :  
        """
        application/octet-stream 的分块读取生成器：
        - 每次读取固定大小（32KB），直到 Content-Length 消耗为 0
        """
        remainbytes = int(http_handler.headers['Content-length'])
        println("file remainbytes ={}".format(remainbytes))
        try:
            buffer_len=32*1024
            while remainbytes > 0:
                chunk_size = buffer_len if remainbytes > buffer_len else remainbytes
                buffer_bytes = http_handler.rfile.read(chunk_size) 
                if not buffer_bytes:
                    break
                yield buffer_bytes
                remainbytes -= len(buffer_bytes)
                println("read chunk size={}, remainbytes={}".format(len(buffer_bytes),remainbytes))
        except IOError:
            println("><><> binary yield read buffer to write error,please check it...")
            return 
        println(">>>>> binary yield read file over...")

    @staticmethod
    def upload_with_binary_yield(http_handler,upload_dir="./webserver/upload",file_name=None) :
        """
        二进制文件上传处理（生成器分块写入）：
        - 写入到 upload_dir 下临时文件
        - 返回 (是否成功, 信息)
        """
                
        remainbytes = int(http_handler.headers['Content-length'])
        println(">>>>> >> file remainbytes ={}".format(remainbytes))
        path = os.path.abspath(upload_dir).replace("\\","/")
        if os.path.exists(path) == False :
            os.makedirs(path)
        if file_name is None or len(file_name) == 0 :
            return (False, "file_name was empty")
        try:
            import time,random
            fn = str(time.time()) +"."+ str(random.randint(1000,10000)) + "_" +file_name
            write_len = 0
            temp_file_path = path +"/" + fn
            with open(temp_file_path,"ab") as up_file :
                for buffer_bytes in ReqManager.upload_with_binary_yield_read(http_handler) :
                    if buffer_bytes :
                        up_file.write(buffer_bytes)
                        write_len += len(buffer_bytes)
                        # TODO: 限制文件上传大小
                    else:
                        println(">>>>> binary yield read buffer is none,total write length={} ,over...".format(write_len))
                        break
            http_handler.octet_stream_file={"file_name":file_name,"size":write_len,"temp_file_path":temp_file_path}
            println(">>>>> post [{}] binary yield upload over,".format(http_handler.content_type))
            return (True, ">>>>> binary yield file upload save over ,http_handler.octet_stream_file={}".format(http_handler.octet_stream_file))    
        except IOError:
            return (False, ">>>>> binary yield error ,please check it...")

    @staticmethod
    def post_read_x_www_form_urlencoded(http_handler) :
        """
        处理 Content-Type=application/x-www-form-urlencoded post请求的参数
        放入http_handler.form_params 在实际的自定义的action中使用

        text/plain,text/html,text/xml 也使用此方法兼容处理
        """
        remainbytes = int(http_handler.headers['Content-length'])
        println(">>>>> post [{}] content-length={}".format(http_handler.content_type,remainbytes))
        try:
            buffer_len=2*1024*1024
            if remainbytes > buffer_len:
                return (False,"post body too long...")  
            post_bytes = http_handler.rfile.read(remainbytes) 
            remainbytes -=remainbytes
            form_params = urllib.parse.parse_qs(str(post_bytes,"utf-8"))
            http_handler.form_params = form_params
            println(">>>>> read post [{}] over ,form _params={}".format(http_handler.content_type,repr(form_params)))

        except IOError:
            println("><><> post [{}] -- Can't read post http_handler.rfile stream ,please check it...".format(http_handler.content_type))
            return (False,"read post payload fail...")
        else:
            return (True,"read post payload success")
    
    @staticmethod
    def post_read_json(http_handler) :
        """
        处理 Content-Type=application/json post请求的参数
        放入http_handler.form_params 在实际的自定义的action中使用
        """
        remainbytes = int(http_handler.headers['Content-length'])
        println(">>>>> post [application/json] content-length={}".format(remainbytes))
        try:
            buffer_len=2*1024*1024
            if remainbytes > buffer_len:
                return (False,"post json body too long...")  
            post_bytes = http_handler.rfile.read(remainbytes) 
            remainbytes -=remainbytes
            json_str = str(post_bytes,"utf-8")
            import json
            try:
                post_json_dict = json.loads(json_str)
            except Exception as ex:
                println(">>>>> read post [application/json] error ,post json={}".format(json_str))
                return (False,"read post json error")
            http_handler.post_json = json_str
            http_handler.post_json_dict = post_json_dict
            println(">>>>> read post [application/json] over ,post json={}".format(repr(post_json_dict)))

        except IOError:
            println("><><> read post [application/json] -- Can't read post http_handler.rfile stream ,please check it...")
            return (False,"read post payload fail...")
        else:
            return (True,"read post payload success")


    @staticmethod         
    def merge_post_str_and_query_params_to_dict(post_str="",query_params={}) :
        """
        合并 post 字符串与 query 参数为 dict（每个 key 为 list）：
        - post 字符串按 k=v&k2=v2 解析，进行 URL 解码
        """
        if post_str is None or len(post_str)== 0 :
            return query_params
        else :
            params_list=[kv.split("=",1) for kv in post_str.split("&") if kv]
            params_dict ={}
            import urllib
            for k,v in params_list:
                val = urllib.parse.unquote(v)
                if k in params_dict:
                    params_dict[k].append(val)
                else:
                    params_dict[k]=[val]
            params = query_params.copy()
            params.update(params_dict)
            return params
    
    @staticmethod         
    def merge_post_form_data_and_query_params_to_dict(post_data={},query_params={}) :
        """
        合并 form-data 与 query 参数为 dict（浅拷贝后更新）。
        """
        if post_data is None or len(post_data)== 0 :
            return query_params
        else :
            params = query_params.copy()
            params.update(post_data)
            return params

    
    @staticmethod 
    def upload_with_binary(http_handler,upload_dir="./webserver/upload") :
        """
        二进制文件上传处理，通过重用内存buffer，暂不推荐使用
        """
        path = os.path.abspath(upload_dir).replace("\\","/")
        if os.path.exists(path) == False :
            os.makedirs(path)
        if http_handler.headers["Content-Type"] is not None:
            boundary = str(http_handler.headers["Content-Type"].split("=")[1]).encode("utf-8")
        
        remainbytes = int(http_handler.headers['Content-length'])
        println("file len ={}".format(remainbytes))
        try:
            import time,random
            fn = str(time.time()) + "." +  str(random.randint(1000,10000)) +".test.temp" 
            with open(path +"/" + fn,"ab") as up_file :
                readed_len,buffer_len=0,32*1024
                f = io.BytesIO()
                while True :
                    if remainbytes > 0 :
                        if buffer_len > remainbytes :
                            need_read = remainbytes
                            #最后一次缩减buffer的大小为剩余的字节数，否则会多保存上次的字节内容
                            #或者在后面刷到本地文件的时候指定读取的字节数shutil.copyfileobj 复制指定的字节数
                            #f.truncate(need_read)  
                            
                        else :
                            need_read = buffer_len                        
                        read_bytes= http_handler.rfile.read(need_read) 
                        println("read len ={}".format(len(read_bytes)))
                        if read_bytes is not None and len(read_bytes) > 0 :
                            f.write(read_bytes)
                            f.seek(0) #重置读指针到buffer头
                            shutil.copyfileobj(f,up_file,len(read_bytes))
                            f.seek(0,0) #重置读写指针到buffer头，为下次重用buffer准备
                            remainbytes -=len(read_bytes)
                            println("write len ={},remainbytes={}".format(len(read_bytes),remainbytes))
                        else:
                            break
                    else:
                        break
                println("write over,remainbytes={}".format(remainbytes))
                
        except IOError:
            return (False, "Can't create file to write,please check it...")

        return (True, "文件 '%s' 上传成功" % fn)

