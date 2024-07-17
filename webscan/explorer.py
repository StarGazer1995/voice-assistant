from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import logging
import time
import requests
import json

bilibili_config = {
    "website" : "https://www.bilibili.com/v/popular/all/?spm_id_from=333.1007.0.0",
    "items" : ["video-name", "up-name__text", "play-text"],
}

zhihu_config = {
    "website" : "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true",
    "items" : ["HotItem-title", "HotItem-metrics HotItem-metrics--bottom"]
}

weibo_config = {
    "website" : "https://s.weibo.com/top/summary?Refer=top_hot&topnav=1&wvr=6",
    "items" : ["td-02"]
}

default_config = {
    "website" : "https://api.vvhan.com/api/hotlist/all",
    "items" : ["微博", "虎扑", "知乎热榜", "知乎日报", "36氪", "哔哩哔哩", "虎嗅"]
}

story_template = {
    'title' : None,
    'hot' : None,
}

class Explorer:
    def __init__(self, logger=None, debug=False) -> None:
        # service = webdriver.ChromeService(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        # service = webdriver.ChromeService(executable_path="/Users/gongzhao/workspace/garage_toys/applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
        FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
        DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
        self.debug = debug
        if not self.debug:
            self.explorer = webdriver.Safari()

        if logger is None:
            self.log = logging.getLogger()
            logging.basicConfig(format=FORMAT, encoding="utf-8", level=logging.INFO, datefmt=DATE_FORMAT)
            self.log.setLevel(logging.INFO)
        else:
            self.log = logger
        self.log.info("The explorer is constructed")

    
    def _apply_story_template(self, story):
        template_key = set(story_template.keys())
        story_key = set(story.keys())
        diff = story_key - template_key
        for d in diff:
            story.pop(d)
        return story

    def process_default_config(self, config):
    
        def search_info(data):
            hotlist = {}
            for item in data:
                hotlist[item['name']] = item['data']
            for name in list(hotlist.keys()):
                if name not in default_config["items"]:
                    hotlist.pop(name)
            for topic, story in hotlist.items():
                hotlist[topic] = list(map(self._apply_story_template, story))
            return hotlist
        
        if self.debug:
            import os
            file_path = os.path.join(os.path.dirname(__file__), "news.txt")
            print(file_path)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)['data']
        else:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"}
            news = requests.get(default_config["website"], headers=headers)
            data = json.loads(news.text)['data']
        hotstory = search_info(data)

        return hotstory
    
    def process_other_config(self, config):
        website_path = config['website']

        if "https://" not in website_path:
            website_path = "https://{}".format(website_path)

        self.log.info("Start accessing the website {}".format(website_path))
        self.explorer.set_window_size(width=1280, height=720)
        self.explorer.get(website_path)
        time.sleep(10)
        
        def search_info():
            temp_res = []
            for item in config["items"]:
                tmp = self.explorer.find_elements(By.CLASS_NAME, item)
                temp_res.append(list(map(lambda x: {item : x.text.strip()}, tmp)))

            for items_idx in range(1, len(temp_res)):
                item = temp_res[items_idx]
                for idx in range(len(item)):
                    temp_res[0][idx].update(item[idx])
            
            return temp_res[0]
        
        return search_info()
    
    def access_page(self, config):
        res = None
        if config == default_config:
            res = self.process_default_config(config)
        else:
            res = self.process_other_config(config)
        
        for source in res.keys():
            res[source] = list(map(lambda x: " ".join(x.values()), res[source][:10]))
            res[source] = source + ":" + ";".join(res[source])

        return list(map(lambda x : res[x], list(res.keys())))


def UT():
    explorer = Explorer(debug=True)
    print(explorer.access_page(default_config))
    # explorer.access_page(bilibili_config)
    # explorer.access_page(zhihu_config)
    # explorer.access_page(weibo_config)

if __name__ == "__main__":
    UT()