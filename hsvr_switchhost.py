#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys,os

from hsvrbase import *
from hsvrresp import RespManager 
from hsvrview import ViewManager
from hsvrdecrproc import DecrProcManager,decrmanager
from hsvrreq import ReqManager
from hsvrserver import Hsvr

__HOSTS_ID_MAX=0

def incr_id():
    global __HOSTS_ID_MAX
    __HOSTS_ID_MAX +=1
    return __HOSTS_ID_MAX
def set_max_id(id):
    global __HOSTS_ID_MAX
    if id > __HOSTS_ID_MAX :
        __HOSTS_ID_MAX = id



class Hosts:
    
    def __init__(self,id,name,host_txt="",opened="off",file_path=""):
        self.id = id
        self.name = name
        self.host_txt=host_txt
        self.opened=opened
        self.file_path = file_path

    def __str__(self):
        return "host={}".format(self.__dict__)
    def to_dict(self):
        return {"id":self.id,"name":self.name,"host_txt":self.host_txt,"opened":self.opened,"file_path":self.file_path}

class SwitchHosts(metaclass=MetaclassTypeSingleton):
    
    def __init__(self):
        self.hosts_list = []
        hosts_path = AppConf.getconf("switchhost","hosts_file_path_win","C:/Windows/System32/drivers/etc/hosts")
        hosts_path = os.path.abspath(hosts_path)
        with open(hosts_path,"rb") as hosts_f:
            lines_str = "".join([str(line_bytes,encoding="utf-8") for line_bytes in hosts_f.readlines()])
            self.hosts_list.append(Hosts(0,"Windows System Hosts","".join(lines_str),"on",hosts_path))
        hosts_save_dir = AppConf.getconf("switchhost","hosts_save_dir","./switchhosts")
        for dirpath, dirnames, filenames in os.walk(hosts_save_dir):
            for filename in filenames:
                if filename.startswith("hosts") :
                    tmp_list = filename.split("_-swh-_")
                    tmp_host_txt = ""
                    tmp_file_path = hosts_save_dir + "/" + filename
                    tmp_file_path = os.path.abspath(tmp_file_path)
                    with open(tmp_file_path,"rb") as hosts_f:
                        lines = "".join([str(line_bytes,encoding="utf-8") for line_bytes in hosts_f.readlines()])
                        tmp_host_txt = lines
                        println(">>>>> hosts_txt file content=",filename,tmp_host_txt)
                    self.hosts_list.append(Hosts(int(tmp_list[1]),tmp_list[2],tmp_host_txt,'off',tmp_file_path))
        [println(">>>>>  >>>>> hosts_list=" ,host) for host in self.hosts_list ]

        [ set_max_id(host.id) for host in self.hosts_list ] 
    @classmethod
    def get_instance(cls):
        return cls._instance
    @classmethod
    def get_hosts(cls):
        return cls._instance.hosts_list
    
SwitchHosts()

__HTML_MENU_LI="""
<li class="" onclick="showPopup('addRule')">
                    <a>{name}
                        <label class="label-switch">
                            <input type="checkbox">
                            <div host_id="{id}" class="checkbox {opened}" ></div>
                        </label>
                        <span class="edit" host_id="{id}">编辑</span>
                    </a>
                </li>
"""
@Hsvr.view("/switchhost")
def index(http_handler):
    resp_rendered_index(http_handler)

@Hsvr.view("/switchhost/")
def index(http_handler):
    resp_rendered_index(http_handler)

@Hsvr.view("/switchhost/index")
def index(http_handler):
    resp_rendered_index(http_handler)

def resp_rendered_index(http_handler):
    _http_server_views_dir=os.path.abspath(AppConf.get_instance().get_conf("http_server","http_server_views_dir","./views"))
    # 根据浏览器语言选择页面，默认英文
    def _detect_lang():
        try:
            al = (http_handler.headers.get("Accept-Language") or "").lower()
            return "zh" if ("zh" in al) else "en"
        except Exception:
            return "en"
    lang = _detect_lang()
    # 优先 index_{lang}.html，不存在则回退到 index.html
    candidate = (_http_server_views_dir+ f"/switchhost/index_{lang}.html").replace("\\","/")
    view_html_path = candidate if os.path.exists(candidate) else (_http_server_views_dir+ "/switchhost/index.html").replace("\\","/")
    #view_html_path = _http_server_views_dir+ "/switchhost/index.html"
    println(">>>>> switchhost index view path=",view_html_path)
    if os.path.exists(view_html_path) == False :
        RespManager.resp_error_status(http_handler,404)
        return
    # 当前开启的 hosts 文本与路径
    opened_host_txt = ""
    opened_host_file_path = ""
    for host in SwitchHosts.get_hosts():
        if host.opened == "on" :
            opened_host_txt = host.host_txt
            opened_host_file_path = host.file_path
            break
    # 菜单渲染
    menu_li_list = [__HTML_MENU_LI.format(**hosts.to_dict()) for hosts in SwitchHosts.get_hosts()]
    html_menu_li_list = "".join(menu_li_list)
    replace_dict={"html_menu_li_list":html_menu_li_list}
    replace_dict["opened_host_txt"]=opened_host_txt
    replace_dict["opened_host_file_path"]=opened_host_file_path
    html = ViewManager.create_html_replace_view(view_html_path,replace_dict)
    ViewManager.resp_rendered_html(http_handler,html)

@Hsvr.get("/switchhost/api/add")
def add(http_handler):
    if http_handler.params["name"] :
        name = http_handler.params["name"][0]
        hst = Hosts(incr_id(),name)
        SwitchHosts.get_hosts().append(hst)

    RespManager.resp_json_result(http_handler,200,0)

@Hsvr.get("/switchhost/api/edit")
def edit(http_handler):
    id = http_handler.params["id"][0]
    if int(id) == 0 :
        RespManager.resp_json_result(http_handler,200,1000,"系统hosts 禁止修改名称")
        return

    for host in SwitchHosts.get_hosts():
        if host.id == int(id) and http_handler.params["name"]:
            if http_handler.params["name"][0] != host.name :
                host.name = http_handler.params["name"][0]
                if len(host.file_path) > 0 and os.path.exists(host.file_path) :
                    hosts_save_dir = AppConf.getconf("switchhost","hosts_save_dir","./switchhosts")
                    hosts_file_path = hosts_save_dir + "/hosts_-swh-_"+ str(host.id) +"_-swh-_"+host.name
                    hosts_file_path = os.path.abspath(hosts_file_path)
                    os.rename(host.file_path,hosts_file_path)
                    host.file_path=hosts_file_path
             
    RespManager.resp_json_result(http_handler,200,0)

@Hsvr.get("/switchhost/api/get_hosts_txt")
def get_hosts_txt(http_handler):
    id = http_handler.params["id"][0]
    data={}
    for host in SwitchHosts.get_hosts():
        if host.id == int(id) :
            hosts_save_dir = AppConf.getconf("switchhost","hosts_save_dir","./switchhosts")
            hosts_file_path = hosts_save_dir + "/hosts_-swh-_"+ str(host.id) +"_-swh-_"+host.name
            data = {"host_txt": host.host_txt,"file_path":host.file_path}
            break
    
    RespManager.resp_json_result(http_handler,200,0,"",data)


@Hsvr.post("/switchhost/api/save")
def save(http_handler):
    if http_handler.form_params.get("id") :
        id = http_handler.form_params.get("id")[0]
        # 新增：解析 opened 参数（布尔），支持 true/false/on/off/1/0
        def _to_bool(val):
            s = (val or "").strip().lower()
            return s in ("1","true","on","yes")
        opened_flag = _to_bool((http_handler.form_params.get("opened") or ["false"])[0])

        for host in SwitchHosts.get_hosts():
            if host.id == int(id) and http_handler.form_params.get("host_txt","") :
                hosts_save_dir = AppConf.getconf("switchhost","hosts_save_dir","./switchhosts")
                hosts_file_path = host.file_path
                host.host_txt = http_handler.form_params["host_txt"][0]

                # 同步 opened 状态：当前规则按客户端传值，其他规则统一关闭
                for h in SwitchHosts.get_hosts():
                    h.opened = "on" if (h.id == host.id and opened_flag) else "off"

                if host.id > 0 :
                    hosts_file_path = hosts_save_dir + "/hosts_-swh-_"+ str(host.id) +"_-swh-_"+host.name
                    if os.path.exists(hosts_save_dir) == False :
                        os.makedirs(hosts_save_dir)                    
                    host.file_path=os.path.abspath(hosts_file_path)

                    # 只有在 opened=true 时才写入系统 hosts
                    if opened_flag :
                        try:
                            import ctypes
                            if os.name == "nt" and not ctypes.windll.shell32.IsUserAnAdmin():
                                RespManager.resp_json_result(http_handler, 200, 1001, "需要管理员权限才能写入系统 hosts", {"file_path": SwitchHosts.get_hosts()[0].file_path})
                                return
                            with open(SwitchHosts.get_hosts()[0].file_path,"wb") as host_f:
                                host_f.write(bytes(host.host_txt,encoding="utf-8"))
                                SwitchHosts.get_hosts()[0].host_txt = http_handler.form_params["host_txt"][0]
                            # 刷新DNS
                            cmd_flushdns = "ipconfig /flushdns"
                            try:
                                import subprocess
                                state, result = subprocess.getstatusoutput(cmd_flushdns)
                                println(">>>>> save changehosts first exec [%s] state=%d ,result=%s" % (cmd_flushdns,state, result))
                                state, result = subprocess.getstatusoutput(cmd_flushdns)
                                println(">>>>> save changehosts second exec [%s] state=%d ,result=%s" % (cmd_flushdns,state, result))
                            except Exception:
                                import traceback
                                println('><><> save changehosts flushdns exception >>>>>' + traceback.format_exc())
                        except PermissionError as e:
                            RespManager.resp_json_result(http_handler, 200, 1001, "写入系统 hosts 被拒绝，请以管理员身份运行", {"error": str(e), "file_path": SwitchHosts.get_hosts()[0].file_path})
                            return
                        except Exception as e:
                            RespManager.resp_json_result(http_handler, 200, 1002, "写入系统 hosts 出错", {"error": str(e)})
                            return
                try:
                    with open(hosts_file_path,"wb+") as host_f:
                        host_f.write(bytes(host.host_txt,encoding="utf-8"))
                    RespManager.resp_json_result(http_handler, 200, 0, "保存 hosts 成功", { "file_path": hosts_file_path})
                    return
                except Exception as e:
                    RespManager.resp_json_result(http_handler, 200, 1003, "保存自定义 hosts 文件失败", {"error": str(e), "file_path": hosts_file_path})
                    return
                break

    RespManager.resp_redirect_status(http_handler,301,"/switchhost/index")

@Hsvr.get("/switchhost/api/changehosts")
def save(http_handler):
    if http_handler.params.get("id") :
        id = http_handler.params.get("id")[0]
        # 新增：解析 opened 参数（布尔）
        def _to_bool(val):
            s = (val or "").strip().lower()
            return s in ("1","true","on","yes")
        opened_flag = _to_bool((http_handler.params.get("opened") or ["true"])[0])

        for host in SwitchHosts.get_hosts():
            if host.id == int(id) :
                host.opened = "on" if opened_flag else "off"
                # 其他规则全部关闭
                for h in SwitchHosts.get_hosts():
                    if h.id != host.id:
                        h.opened = "off"

                # opened=true 时应用到系统 hosts
                if opened_flag:
                    try:
                        import ctypes
                        if os.name == "nt" and not ctypes.windll.shell32.IsUserAnAdmin():
                            RespManager.resp_json_result(http_handler, 200, 1001, "需要管理员权限才能写入系统 hosts", {"file_path": SwitchHosts.get_hosts()[0].file_path})
                            return
                        with open(SwitchHosts.get_hosts()[0].file_path,"wb+") as host_f:
                            host_f.write(bytes(host.host_txt,encoding="utf-8"))
                            SwitchHosts.get_hosts()[0].host_txt = host.host_txt
                        # 刷新DNS
                        cmd_flushdns = "ipconfig /flushdns"
                        try:
                            import subprocess
                            state, result = subprocess.getstatusoutput(cmd_flushdns)
                            println(">>>>> changehosts first  exec [%s] state=%d ,result=%s" % (cmd_flushdns,state, result))
                            state, result = subprocess.getstatusoutput(cmd_flushdns)
                            println(">>>>> changehosts second exec [%s] state=%d ,result=%s" % (cmd_flushdns,state, result))
                        except Exception:
                            import traceback
                            println('><><> changehosts exec [ipconfig /flushdns] exception >>>>>' + traceback.format_exc())
                    except PermissionError as e:
                        RespManager.resp_json_result(http_handler, 200, 1001, "写入系统 hosts 被拒绝，请以管理员身份运行", {"error": str(e), "file_path": SwitchHosts.get_hosts()[0].file_path})
                        return
                    except Exception as e:
                        RespManager.resp_json_result(http_handler, 200, 1002, "写入系统 hosts 出错", {"error": str(e)})
                        return
            else:
                host.opened="off"

    RespManager.resp_json_result(http_handler,200,0)

if __name__ == "__main__" :

    import asyncio

    from asyncio.events import AbstractEventLoop
    async def run_async(app: "Hsvr"):
        loop: AbstractEventLoop = asyncio.get_running_loop()
        println("start ... port ", app.http_server.server_port)

        @app.get("/switchhost/home")
        def get_home(http_handler):
            RespManager.resp_error_status(http_handler, 200, "welcome get home")

        @app.post("/switchhost/home")
        def post_home(http_handler):
            RespManager.resp_error_status(http_handler, 200, "welcome post home")

        # 将阻塞的 serve_forever 放到线程执行器中运行，避免阻塞事件循环
        server_future = loop.run_in_executor(None, app.run)
        await server_future  # 正常情况下不会返回，除非调用 shutdown()

    app = Hsvr()

    try:
        asyncio.run(run_async(app))
    except KeyboardInterrupt:
        println("KeyboardInterrupt received, shutting down...")
        try:
            app.http_server.shutdown()
            app.http_server.server_close()
        except Exception as ex:
            println("shutdown error:", repr(ex))