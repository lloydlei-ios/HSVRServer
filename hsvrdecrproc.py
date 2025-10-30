import sys

import urllib
from typing import Any, Tuple, Optional

from hsvrbase import println  
from hsvrbase import MetaclassTypeSingleton 
from hsvrbase import AppConf
from hsvrreq import ReqManager
from hsvrresp import RespManager

class DecrProcManager(metaclass=MetaclassTypeSingleton) :
    """
    装饰器注册管理：
    - actions：注册 GET/POST 处理函数
    - views：注册视图处理函数
    - filters：注册过滤器（前置校验）
    """
    def __init__(self):
        self.actions={}
        self.filters=[]
        self.actions_get={}
        self.actions_post={}
        self.views_pre= AppConf.get_instance().get_conf("http_server","http_server_views_pre","/views")
        self.action_pre= AppConf.get_instance().get_conf("http_server","http_server_action_pre","/action")
        self.views={}
        println(">>>>> init DecrProcManager OK ... ")
    @classmethod
    def get_instance(cls) :
        return cls._instance

    def reg_action(self,methonds=["GET","POST"],uri=None,ctx=None) :
        """
        将普通函数注册为 action：
        - methonds：支持 GET/POST
        - uri：注册的路由（默认用函数名）
        """
        _func_name=sys._getframe().f_code.co_name

        def reg_func(func):
            _uri = uri if uri and len(uri) > 0 else func.__name__
            action_uri = _uri 
            if methonds.__contains__("GET"):
                self.actions_get[action_uri] = func
                println(">>>>> {}.{}.{} func.__name__[{}] to actions_get[{}] ".format(__name__ ,self.__class__.__name__,_func_name,func.__name__,action_uri ))

            if methonds.__contains__("POST"):
                self.actions_post[action_uri] = func
                println(">>>>> {}.{}.{} func.__name__[{}] to actions_post[{}] ".format(__name__ ,self.__class__.__name__,_func_name,func.__name__,action_uri))
            if methonds.__contains__("GET") and methonds.__contains__("POST"):
                self.actions[action_uri] = func
            return func
        return reg_func

    def reg_action_get(self,uri=None,ctx=None) :
        
        return self.reg_action(["GET"],uri,ctx)
    def reg_action_post(self,uri=None,ctx=None) :
        return self.reg_action(["POST"],uri,ctx)

    def reg_filter_func(self,func) :
        """
        装饰回调注册函数为filter
        """
        _func_name=sys._getframe().f_code.co_name
        println(">>>>> {}.{}.{} func.__name__[{}] to filters ".format(__name__ ,self.__class__.__name__,_func_name,func.__name__))
        self.filters.append(func)
        return func

    def get_action(self,action_uri):
        """
        通过action_uri获取对应的注册的action函数
        """
        return self.actions.get(action_uri)

    def get_action_post(self,action_uri):
        """
        通过action_uri获取对应的注册的POST action函数
        """
        return self.actions_post.get(action_uri)

    def get_action_get(self,action_uri):
        """
        通过action_uri获取对应的注册的GET action函数
        """
        return self.actions_get.get(action_uri)

    def get_filter_funcs(self):
        """
        获取所有注册的 filter 函数
        """
        return self.filters

    def init_uri_and_params(self,http_handler: Any) -> None:
        """
        初始化请求路径、查询参数与基础头信息，确保字段健壮：
        - uri、query_str、params
        - content_type（无则为空字符串）
        - content_length（无则为 0）
        - 预置 filter_pre_check_result、form_params、form_files
        """
        uri, _, query = http_handler.path.partition('?')
        http_handler.uri = urllib.parse.unquote(uri)
        http_handler.query_str = query
        params = urllib.parse.parse_qs(query)
        raw_ct = (http_handler.headers.get("Content-Type") or "")
        http_handler.content_type = raw_ct.split(";")[0] if raw_ct else ""
        try:
            http_handler.content_length = int(http_handler.headers.get('Content-length') or 0)
        except ValueError:
            http_handler.content_length = 0
        println(">>>>> init_uri_and_params [{}] Content-Type={}".format(http_handler.command,http_handler.content_type))
        http_handler.params = params
        http_handler.filter_pre_check_result="success"
        http_handler.form_params={}
        http_handler.form_files={}


    def filter_http_get(self,func) :
        """
        GET 请求过滤器：
        - 初始化请求上下文
        - 依次执行已注册的 filters
        - 任一 filter 返回 False，则直接返回 403（也可在 filter 内自定义响应）
        """
        _decr_filer_func_name=sys._getframe().f_code.co_name

        from functools import wraps
        @wraps(func)     
        def http_get(http_handler):
            self.init_uri_and_params(http_handler)
            println(">>>>> {}.{} filter http get func.__name__[{}] ".format(__name__ ,_decr_filer_func_name,func.__name__ ))

            filter_ret = True
            for filter_fun in self.filters:
                if filter_fun(http_handler):
                    continue
                else:
                    filter_ret =False
                    break
            if filter_ret :
                return func(http_handler)
            else:
                # 统一返回 403（若 filter 内已响应，可按需修改此处为直接返回）
                RespManager.resp_error_status(http_handler,403,"<B>Forbidden</B>")
                return None
        return http_get

    def _handle_post_payload(self, http_handler: Any) -> Tuple[bool, str]:
        """
        解析 POST 请求负载，根据 Content-Type 分发到具体处理：
        - application/x-www-form-urlencoded、text/plain、text/xml、text/html：统一按表单解析
        - multipart/form-data：表单+文件
        - application/json：JSON
        - application/octet-stream：二进制上传（需 file_name 参数）
        - 其他：回落至表单解析
        返回：(是否成功, 信息)
        """
        ct = http_handler.content_type or ""
        if ct.startswith("application/x-www-form-urlencoded") \
            or ct.startswith("text/plain") \
            or ct.startswith("text/xml") \
            or ct.startswith("text/html"):
            try:
                return ReqManager.post_read_x_www_form_urlencoded(http_handler)
            except Exception as ex:
                return (False, str(ex))

        if ct.startswith("multipart/form-data"):
            _http_server_upload_dir = AppConf.get_instance().get_conf("http_server","http_server_upload_dir","./upload")
            return ReqManager.post_with_form_data_multi_part(http_handler,_http_server_upload_dir)

        if ct.startswith("application/json"):
            return ReqManager.post_read_json(http_handler)

        if ct.startswith("application/octet-stream"):
            _http_server_upload_dir = AppConf.get_instance().get_conf("http_server","http_server_upload_dir","./upload")
            file_name_l =http_handler.params.get("file_name")
            return ReqManager.upload_with_binary_yield(http_handler,_http_server_upload_dir, file_name_l[0] if file_name_l else file_name_l)

        # fallback
        return ReqManager.post_read_x_www_form_urlencoded(http_handler)

    def filter_http_post(self,func) :
        """
        POST 请求过滤器：
        - 初始化请求上下文
        - 依次执行已注册的 filters
        - 自动根据 Content-Type 解析负载（统一入口）
        - 任一环节失败则返回对应错误响应
        """
        _decr_filer_func_name=sys._getframe().f_code.co_name  
        from functools import wraps
        @wraps(func)     
        def http_post(http_handler):
            self.init_uri_and_params(http_handler)
            println(">>>>> {}.{} filter http post func.__name__[{}] ".format(__name__ ,_decr_filer_func_name,func.__name__ ))

            filter_ret = True
            for filter_fun in self.filters:
                if filter_fun(http_handler):
                    continue
                else:
                    filter_ret =False
                    break
            if filter_ret :
                succ_flag,msg = self._handle_post_payload(http_handler)
                if not succ_flag :
                    RespManager.resp_error_status(http_handler,500,msg)
                    return None
                return func(http_handler)
            else:
                RespManager.resp_error_status(http_handler,403,"<B>Forbidden</B>")
                return None
        return http_post

    def reg_view(self,uri=None) :
        """
        将普通函数注册为 view：
        - 默认挂载到 /views/{func.__name__}
        - 支持自定义 URI
        """
        _func_name=sys._getframe().f_code.co_name
        def reg_func(func):
            view_uri = self.views_pre + "/" + func.__name__ if uri is None else uri 
            println(">>>>> {}.{}.{} func.__name__[{}] to views[{}] ".format(__name__ ,self.__class__.__name__,_func_name,func.__name__,view_uri))
            self.views[view_uri] =func
            return func
        return reg_func


    def get_view(self,view_uri) :
        """
        通过view_uri获取对应的注册的view 处理函数
        """
        return self.views.get(view_uri)
    
decrmanager=DecrProcManager()


__CONST_GLOBALS_ACTIONS_KEY="__gmm_reg_actions"
globals()[__CONST_GLOBALS_ACTIONS_KEY] = {}
def decr_reg_action(func) :
    """
    （保留示例）注册到全局 actions 映射，当前不推荐使用
    """
    _func_name=sys._getframe().f_code.co_name
    globals()[__CONST_GLOBALS_ACTIONS_KEY]["/action/"+func.__name__] = func
    
    println(">>>>> {}.{} reg func.__name__[{}] to __globals__ ".format(__name__ ,_func_name,func.__name__ ))
    return func

def get_action_from_globals( action_uri):

    return globals()[__CONST_GLOBALS_ACTIONS_KEY][action_uri]

def split_params_to_dict(post_str="",url_params={}) :
    if post_str is None or len(post_str)== 0 :
        return url_params
    else :
        params_list=[]
        [params_list.append(kv.split("=")) for kv in post_str.split("&")]
        params_dict ={}
        import urllib
        [params_dict.__setitem__(item[0],urllib.parse.unquote(item[1])) for item in params_list ]
        params = url_params.copy()
        params = params.update(params_dict)
        return params



if __name__ == "__main__":
    pass
    