from enum import Enum
from queue import Queue, Empty
from threading import Thread
from typing import Any, Callable, Dict
import time
from core.constant import EventType, Event

import traceback


class EventEngine:
    """
    事件引擎
    包含：
    1. 事件队列
    2. 事件引擎开关
    3. 事件处理线程
    4. 计时器线程
    """
    def __init__(self, timer_interval: float = 1):
        """
        初始化事件引擎
        Args:
            timer_interval: 计时器触发间隔（秒）
        """
        self._queue = Queue()
        self._active = False
        self._handlers: Dict[str, list] = {}
        self._general_handlers = []
        
        # 事件处理线程
        self._thread = Thread(target=self._run)
        
        # 计时器线程
        self._timer = Thread(target=self._run_timer)
        self._timer_active = False
        self._timer_interval = timer_interval  # 计时器间隔
        self._timer_handlers = []  # 计时器事件处理函数列表

    def _run(self):
        """引擎运行"""
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=1)
                self._process(event)
            except Empty:
                continue
    
    def _process(self, event: Event):
        """处理事件"""
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    # 为每个handler提供事件的独立副本
                    handler(event.clone())
                except Exception as e:
                    print(f"处理事件出错: {e}")
                    traceback.print_exc()

    def _run_timer(self):
        """
        运行计时器循环
        """
        while self._timer_active:
            # 执行计时器事件处理函数
            for handler in self._timer_handlers:
                try:
                    handler()
                except Exception as e:
                    print(f"Timer handler error: {e}")
            
            time.sleep(self._timer_interval)
            
    def start(self):
        """
        启动事件引擎
        """
        self._active = True
        self._timer_active = True
        self._thread.start()
        self._timer.start()

    def stop(self):
        """
        停止事件引擎
        """
        self._timer_active = False
        self._timer.join()
        
        self._active = False
        self._thread.join()

    def register(self, type_: EventType, handler: Callable[[Event], None]):
        """注册事件处理函数"""
        handler_list = self._handlers.setdefault(type_, [])
        handler_list.append(handler)
        
    def unregister(self, type_: EventType, handler: Callable[[Event], None]):
        """注销事件处理函数"""
        handler_list = self._handlers.get(type_, [])
        if handler in handler_list:
            handler_list.remove(handler)

    def put(self, event: Event):
        """推送事件"""
        self._queue.put(event)

    def register_timer_handler(self, handler: Callable[[], None]):
        """
        注册计时器事件处理函数
        
        Args:
            handler: 计时器事件处理函数
        """
        self._timer_handlers.append(handler)

    def unregister_timer_handler(self, handler: Callable[[], None]):
        """
        注销计时器事件处理函数
        
        Args:
            handler: 计时器事件处理函数
        """
        if handler in self._timer_handlers:
            self._timer_handlers.remove(handler) 