#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import os
import sys
import time
import datetime
import traceback
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def println(value: Any, *args: Any, **kwargs: Any) -> None:
    """
    统一的控制台打印函数：
    - 前缀包含当前时间与线程名，便于排查并发问题
    - 保持与内置 print 相同的调用方式（*args、**kwargs）
    """
    _cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    _thread_name = threading.current_thread().name
    tmp_value = "{} - {} -- {}".format(_cur_time, _thread_name, value)
    print(tmp_value, *args, **kwargs)


def decr_class_info(cls):
    """
    类装饰器：打印类的 __dict__ 信息，用于调试类结构。
    """
    println('>>>>> class dict={}'.format(cls.__dict__))
    return cls


class MetaclassTypeSingleton(type):
    """
    元类 -- 创建类对象单例 ，使用样例 metaclass=MetaclassTypeSingleton
    """
    _instance_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with MetaclassTypeSingleton._instance_lock:
                if not hasattr(cls, "_instance"):
                    cls._instance = super(MetaclassTypeSingleton, cls).__call__(*args, **kwargs)
        return cls._instance


def reg_globals(key: str, value: Any, upd_flag: bool = True) -> None:
    """
    注册（或更新）值到全局变量：
    - upd_flag 为 True 时覆盖已有值
    """
    if globals().get(key) and upd_flag:
        globals()[key] = value
    elif not globals().get(key):
        globals()[key] = value
    else:
        pass


reg_globals("__APP_CONF_FILENAME", "conf.ini")
# 使用当前文件所在目录定位 conf.ini，避免依赖进程工作目录
reg_globals("__APP_CONF_FILEPATH", os.path.join(os.path.dirname(__file__), "conf.ini").replace("\\", "/"))


@dataclass
class RestResult:
    """
    统一的 REST 响应数据结构（用于字符串化返回 JSON）：
    - ret_code：业务返回码
    - ret_msg：业务消息
    - data：附加数据
    """
    ret_code: int = 0
    ret_msg: str = "成功"
    data: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __str__(self) -> str:
        if not self.data:
            json_result = '{"ret_code":%d,"ret_msg":"%s"}' % (self.ret_code, self.ret_msg)
        else:
            json_data = json.dumps(self.data, ensure_ascii=False)
            json_result = '{"ret_code":%d,"ret_msg":"%s","data":%s}' % (self.ret_code, self.ret_msg, json_data)
        println(">>>>> RestResult=", json_result)
        return json_result


class AppConf(metaclass=MetaclassTypeSingleton):
    """
    单例配置类：
    - 基于 ConfigParser 读取 conf.ini
    - 通过 get_conf(section, option, def) 获取配置项
    """
    app_conf_file_path = globals()["__APP_CONF_FILEPATH"]
    app_conf_file_name = globals()["__APP_CONF_FILENAME"]
    app_conf = None

    def __init__(self):
        try:
            if self.app_conf is None:
                from configparser import ConfigParser
                self.app_conf = ConfigParser()
                if not os.path.exists(self.app_conf_file_path):
                    println("><><> app conf file[{}] was not exists, please check it, app continues with defaults..."
                            .format(self.app_conf_file_path))
                else:
                    self.app_conf.read(self.app_conf_file_path)
        except Exception:
            msg = traceback.format_exc()
            println('><><> AppConf read error >>>>>\n' + msg)
        else:
            println(">>>>> AppConf init success ...")

    def get_conf(self, section_name: str, option_name: str, def_value: Optional[str] = None) -> Optional[str]:
        """
        获取配置项：
        - section_name：配置段名
        - option_name：配置项名
        - def_value：默认值（当不存在时返回）
        """
        from configparser import NoOptionError, NoSectionError
        try:
            val = self.app_conf.get(section_name, option_name)
        except (NoOptionError, NoSectionError):
            msg = traceback.format_exc()
            println("><><> get config fail, section[{}] option[{}], error:\n{}"
                    .format(section_name, option_name, msg))
            return def_value
        return val

    @classmethod
    def getconf(cls, section_name: str, option_name: str, def_value: Optional[str] = None) -> Optional[str]:
        return cls._instance.get_conf(section_name, option_name, def_value)

    @classmethod
    def get_instance(cls) -> "AppConf":
        return cls._instance


# 初始化单例配置类
AppConf()


def get_elapsed_ms(pre_time: float) -> int:
    """
    计算函数执行耗时（毫秒）
    """
    elapsed_sec = time.time() - pre_time
    return int(elapsed_sec * 1000)


def decr_time_elapsed_ms(func):
    """
    装饰器：记录函数执行耗时（毫秒），并打印开始/结束日志
    """
    from functools import wraps

    @wraps(func)
    def elapsed_ms(*args, **kwargs):
        pre_time = time.time()
        call_id = int(round(pre_time * 1000000))
        args_str = ",".join([str(item) for item in list(args)])
        println(">>>>> [{}] call id[{}] elapsed_ms func.__name__[{}] exec start -- >>>>> args[{}] kwargs[{}]"
                .format(__name__, call_id, func.__name__, args_str, kwargs))
        ret = None
        try:
            ret = func(*args, **kwargs)
        finally:
            println(">>>>> [{}] call id[{}] elapsed_ms func.__name__[{}] exec end   -- <<<<< elapsed [{}] ms"
                    .format(__name__, call_id, func.__name__, str(get_elapsed_ms(pre_time))))
        return ret

    return elapsed_ms


class AppLogTrans(metaclass=MetaclassTypeSingleton):
    """
    简易日志转发器（将 stdout 重定向到每日滚动文件，非 DEV 环境启用）：
    - console_log_filedir：日志目录
    - console_log_filepath_today_name：当日日志文件
    - 在非 DEV 环境中启动守护线程，定时刷新并按天滚动
    """
    log_to_file = False

    def __init__(self):
        self.console_log_filedir = AppConf.getconf("http_server", "http_server_console_log_dir", "./logs")
        self.console_log_filepath = self.console_log_filedir + "/console.log"
        self.postfix_log_name = str(datetime.date.today())
        self.console_log_filepath_today_name = self.console_log_filepath + "." + self.postfix_log_name
        if not os.path.isdir(self.console_log_filedir):
            os.makedirs(self.console_log_filedir)

        self.console = sys.stdout
        self.env = AppConf.getconf("http_server", "http_server_env", "DEV")
        if self.env is None or self.env == "DEV":
            # 开发环境：保持输出到控制台
            pass
        else:
            # 非开发环境：输出重定向到日志文件（每日滚动）
            self.console_f = open(self.console_log_filepath_today_name, "a+", encoding="utf-8")
            print(">>>>> AppLogTrans to env[{}] console.log >> {} ".format(self.env, self.console_log_filepath))
            sys.stdout = self.console_f
            self.log_to_file = True
            threading.Thread(target=self.flushLogTask, args=(), name='thread-flushLog', daemon=True).start()

    def flushLogTask(self):
        """
        日志刷新与滚动任务：
        - 每 5 秒刷新缓冲
        - 日期变更后切换到当日日志文件，并清理 7 天前的日志
        """
        while True:
            self.postfix_log_name = str(datetime.date.today())
            console_log_filepath_today_name_now = self.console_log_filepath + "." + self.postfix_log_name
            println(">>>>> {} flushLogTask postfix_log_name={}".format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), console_log_filepath_today_name_now))
            if console_log_filepath_today_name_now != self.console_log_filepath_today_name:
                # 删除 7 天前日志
                delete_postfix_log_name = str(datetime.date.today() - datetime.timedelta(days=7))
                try:
                    delet_log_file = self.console_log_filepath + "." + delete_postfix_log_name
                    if os.path.isfile(delet_log_file):
                        os.remove(delet_log_file)
                except OSError as e:
                    print("flushLogTask delete log file Error: {} - {}.".format(e.filename, e.strerror))

                self.console_log_filepath_today_name = console_log_filepath_today_name_now
                if hasattr(self, "console_f") and self.console_f:
                    self.console_f.close()
                # 切回控制台输出（先确保恢复 stdout）
                sys.stdout = self.console

                # 切换到新日志文件
                self.console_f = open(self.console_log_filepath_today_name, "a+", encoding="utf-8")
                sys.stdout = self.console_f

            try:
                sys.stdout.flush()
            except Exception:
                pass
            time.sleep(5)

    @classmethod
    def get_instance(cls) -> "AppLogTrans":
        return cls._instance


# 初始化日志配置
AppLogTrans()


if __name__ == "__main__":
    AppLogTrans()
    conf = AppConf()
    println (">>>>> conf=",conf)
    # conf = AppConf()
    # print (">>>>> conf=",conf,"--- server context--", conf.get_conf("flask","ok1"))

    # conf = AppConf.get_instance()
    # print (">>>>> conf=",conf)
