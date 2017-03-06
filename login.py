#-*- coding: UTF-8 -*-   
#!/usr/bin/python
import os 
import urlparse
import time
import datetime
import urllib
import urllib2
import requests
import json
import logging
import cookielib
import Queue
import threading  
import traceback
import re
import base64
import rsa
import binascii
import chardet
import pickle
from bs4 import BeautifulSoup
import pymongo
import random
from utils import LogManager
from jinja2 import Template
import copy
try:
    from PIL import Image
    import matplotlib.pyplot as plt
except:
    pass
        
logManager = LogManager(["LoginManager","WeiboLoginManager"])

def find_yonghuming(html):
    for i,h in enumerate(html.split("\n")):
        if "$CONFIG['nick']" in h:
            break
    else:
        return None
    re_text = r".*\$CONFIG\['nick'\]\s*=\s*'(.*)'\s*;\s*"
    pattern = re.compile(re_text)
    match = pattern.match(h)
    return match.group(1)

class InputThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.input = False
        self.yanzhengma = None
        self.if_stop =False

        
    def run(self):
        while not self.if_stop:
            if self.input == False:
                time.sleep(2)
                continue
            self.yanzhengma = raw_input("yanzhengma:")
            self.input = False

    def get_yanzhengma(self):
        while True:
            if self.yanzhengma != None:
                break 
            else:
                time.sleep(1)
        yanzhengma = self.yanzhengma 
        self.yanzhengma = None 
        return yanzhengma

    def stop(self):
        self.if_stop = True

class WeiboLoginManager():
    def __init__(self,username,pwd,base_dir=""):
        self.headers = {
        'User-Agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A5313e Safari/7534.48.3',
        #"User-Agent":"Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1)",
        }
        self.logger = logManager.getLogger(self.__class__.__name__)
        self.base_dir = base_dir

        self.username = username
        self.pwd = pwd
        self.session =  requests.Session()
        self.session_file = "session.pkl"
    def get_servertime(self):
        url = 'http://login.sina.com.cn/sso/prelogin.php?entry=sso&callback=sinaSSOController.preloginCallBack&su=%s&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.4)' % self.username
        url = 'https://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su=%s&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.18)&_=%s123' % (base64.b64encode(urllib.quote(self.username)),int(time.time()))
        #https://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.preloginCallBack&su=Yml0YW9iYW8lNDAxNjMuY29t&rsakt=mod&checkpin=1&client=ssologin.js(v1.4.18)&_=1482386159854
        #print url
        data = urllib2.urlopen(url).read()
        p = re.compile('\((.*)\)')
        try:
            #print data
            json_data = p.search(data).group(1)
            data = json.loads(json_data)
            servertime = str(data['servertime'])
            nonce = data['nonce']
            pubkey  = data['pubkey']
            rsakv = data['rsakv']
            pcid = data["pcid"]
            return servertime, nonce,pubkey,rsakv,pcid
        except Exception, e:
            self.logger.error('Get severtime error! \n%s'%(traceback.format_exc()))
            return None

    def show_yanzhengma(self):
        pass


    def get_yanzhengma(self,yanzhengma_url):
        print yanzhengma_url
        response = requests.get(yanzhengma_url,headers=self.headers)
        open('pic', 'wb').write(response.content)
        inputThread.input = True
        time.sleep(3)
        img=Image.open('pic')
        plt.figure("dog")
        plt.imshow(img)
        plt.show() 
        yanzhengma = inputThread.get_yanzhengma()
        return yanzhengma


    def login(self,need_yanzhengma=False,if_save=True):
        self.session =  requests.Session()
        url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.4)'
        try:
            servertime, nonce ,pubkey ,rsakv,pcid= self.get_servertime()
        except:
            self.logger.error("call servertime url error \n %s"%(traceback.format_exc()))
            return False 
        yanzhengma_url =  "http://login.sina.com.cn/cgi/pin.php?r=%s&s=0&p=%s"%(int(time.time()),pcid)

        postdata = {
                         'entry': 'weibo',
                         'gateway': '1',
                         'from': '',
                         'savestate': '7',
                         'userticket': '1',
                         'ssosimplelogin': '1',
                         'vsnf': '1',
                         'vsnval': '',
                         'su': '',
                         'service': 'miniblog',
                         'servertime': '',
                         'nonce': '',
                         'pwencode': 'rsa2',
                         'sp': '',
                         'encoding': 'UTF-8',
                         'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack',
                         'returntype': 'META',
                         'rsakv' : '',
                         }

        postdata['servertime'] = str(servertime)
        postdata['nonce'] = str(nonce)
        postdata['su'] = base64.b64encode(urllib.quote(self.username)) #get_user(username)
        postdata['rsakv'] = rsakv
        rsaPublickey = int(pubkey, 16)
        key = rsa.PublicKey(rsaPublickey,65537)
        message = str(servertime) +'\t' + str(nonce) + '\n' + str(self.pwd)
        passwd = rsa.encrypt(message, key)
        sp = binascii.b2a_hex(passwd)
        postdata['sp'] = sp 

        for i in xrange(5):
            if need_yanzhengma:
                door = self.get_yanzhengma(yanzhengma_url)
                postdata["pcid"] = pcid
                postdata["door"] = door
            response = self.session.post("http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.4)",data=postdata,headers=self.headers)
            text = response.text
            #print text
            p = re.compile('location\.replace\(\'(.*?)\'\)')
            try:
                login_url = p.search(text).group(1)
                print login_url
                self.session.get(login_url,headers=self.headers)   
                print 'login seccuss'
                self.logger.debug(self.username +' login seccuss')
                if if_save:
                    self.save_session()
                    self.logger.debug(self.username +' save session seccuss')
                break
            except Exception, e:
                #traceback.print_exc()
                print 'login error time %s'%(i)
                p = re.compile('location\.replace\(\"(.*?)\"\)')
                error_login_url = p.search(text).group(1)
                #print error_login_url
                reason = error_login_url.split("reason=")[1].split("&")[0]
                reason =  urllib.unquote(str(reason)).decode("gb2312")
                print "reason is %s"%(reason)
                self.logger.debug(self.username +' login error')
        else:
            print "login failed"


    def get_session(self):
        return self.session

    @staticmethod
    def validate_cookies(html,tag={"type":"","attrs":{}},tag_len = 1):
        soup = BeautifulSoup(html,'lxml')
        tag_list = soup.find_all(tag.get("type") ,attrs = tag.get("attrs"))
        tag_list = soup.find_all("a" ,attrs ={"class":"gn_name"})
        print len(tag_list)
        if len(tag_list) == tag_len:
            return True 
        else:
            return False 

        pass
    def call(self,url):
        response = self.session.get(url,headers=self.headers)
        html = response.text.encode("utf8")
        f = open("response.html","w")
        f.write(html)
        f.close()
        return html

    def save_session(self):
        output = open(self.session_file, 'wb')
        pickle.dump(self.session, output)
        output.close()
    
    def get_session_from_file(self,if_load=True):
        pkl_file = open(self.session_file, 'rb')
        session = pickle.load(pkl_file)
        pkl_file.close()
        if if_load:
            self.session = session
        return session


if __name__ == "__main__":
    use_browser_cookies = False
    username = ""
    password = ""
    weiboLoginManager = WeiboLoginManager(username, password)
    
    inputThread = InputThread()
    inputThread.start()
    weiboLoginManager.login(need_yanzhengma=True)
    inputThread.stop()

    
   
    
    
    
    
    
    
    
    












