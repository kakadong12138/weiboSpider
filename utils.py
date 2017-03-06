#-*- coding: UTF-8 -*-   
#!/usr/bin/python
import requests
import Queue
import threading  
import time 
import json 
import random
import traceback
import logging
import redis
import pickle

class LogManager():
    def __init__(self,logger_names=[]):
        logger_list = {}
        for logger_name in logger_names:
            logger = self.makeLogger(logger_name)
            logger_list[logger_name] = logger
        self.logger_list = logger_list
    def makeLogger(self,logger_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('%s.log'%(logger_name))
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return logger
    def addLogger(self,logger_name):
        logger = self.makeLogger(logger_name)
        self.logger_list[logger_name] = logger
    def getLogger(self,logger_name):
        if logger_name not in self.logger_list:
            self.addLogger(logger_name)
        return self.logger_list.get(logger_name)

class Task():
    def __init__(self,url,task_type,max_try_time=5,meta={}):
        self.url = url
        self.task_type = task_type
        self.try_times = 0
        self.max_try_time = max_try_time
        self.meta = meta
        self.meta["messages"] = {}
        self.is_failed = False
    def add_tryTimes(self):
        if self.try_times >= self.max_try_time: 
            pass
        else:
            self.try_times+=1

class Customer(threading.Thread): 
    def __init__(self,thread_num, queue,get_timeout=1):  
        threading.Thread.__init__(self)  
        self.if_stop = False
        self.queue = queue
        self.get_timeout = get_timeout
        self.thread_num = thread_num
   
    def run(self): 
        print "thread %s start"%(self.thread_num)
        while not self.if_stop:
            try:
                task = self.queue.get(block=False,timeout=self.get_timeout)
                task = pickle.loads(task)
            except:
                #traceback.print_exc()
                continue
            try:
                max_try_time = task.max_try_time
                try_times = task.try_times
                if try_times >= max_try_time:
                    task.meta["messages"]["run"] = "too many try times"
                    self.deal_failed_task(task)
                    continue
                self.do_task(task)
            except:
                traceback.print_exc()
    def stop(self):  
        print "thread %s stop"%(self.thread_num)
        self.if_stop = True  

    def do_task(self,task):
        is_failed = task.is_failed 
        if is_failed:
            try:
                self.deal_failed_task(task)
            except:
                traceback.print_exc()
            return
        task_type = task.task_type
        fun = self.task_fun_relation.get(task_type)
        try:
            fun(task)
        except:            
            task.add_tryTimes()
            self.queue.put(task)
    
            print "fun error",fun
            traceback.print_exc()

    def deal_failed_task(self,task):
        pass

class Producer(threading.Thread): 
    def __init__(self, queue,put_timeout=1):  
        threading.Thread.__init__(self)  
        self.queue = queue
        self.put_timeout = put_timeout   
    def run(self): 
        pass
    def stop(self):  
        pass 


class RedisQueue(object):
    """Simple Queue with Redis Backend"""
    def __init__(self, name, namespace='queue', **redis_kwargs):
        """The default connection parameters are: host='localhost', port=6379, db=0"""
        self.__db= redis.Redis(**redis_kwargs)
        self.key = '%s:%s' %(namespace, name)

    def qsize(self):
        """Return the approximate size of the queue."""
        return self.__db.llen(self.key)

    def empty(self):
        """Return True if the queue is empty, False otherwise."""
        return self.qsize() == 0

    def put(self, item):
        """Put item into the queue."""
        self.__db.rpush(self.key, item)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args block is true and timeout is None (the default), block
        if necessary until an item is available."""
        if block:
            item = self.__db.blpop(self.key, timeout=timeout)
        else:
            item = self.__db.lpop(self.key)
        '''
        if item:
            item = item[1]
        '''
        return item

    def get_nowait(self):
        """Equivalent to get(False)."""
        return self.get(False)
