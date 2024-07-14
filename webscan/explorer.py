from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import logging

bilibili_config = {
    "website" : "www.bilibili.com",
    "items" : ["热门", ""]
}

class Explorer:
    def __init__(self, logger=None) -> None:
        # service = webdriver.ChromeService(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        # service = webdriver.ChromeService(executable_path="/Users/gongzhao/workspace/garage_toys/applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
        FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
        DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
        self.explorer = webdriver.Safari()
        if logger is None:
            self.log = logging.getLogger()
            logging.basicConfig(format=FORMAT, encoding="utf-8", level=logging.INFO, datefmt=DATE_FORMAT)
            self.log.setLevel(logging.INFO)
        else:
            self.log = logger
        self.log.info("The explorer is constructed")

    def access_page(self, website_path: str) -> None:
        if "https://" not in website_path:
            website_path = "https://{}".format(website_path)
        self.log.info("Start accessing the website {}".format(website_path))
        self.explorer.get(website_path)
        self.explorer.implicitly_wait(10.9)
        hot = self.explorer.find_element(By.TAG_NAME, "icon-bg icon-bg__popular")
        hot.click()
        # print(self.explorer.find_elements)
        # l = self.explorer.find_element(By.CLASS_NAME, "icon-bg icon-bg__popular")
        # l.click()


def UT():
    explorer = Explorer()
    explorer.access_page("https://www.bilibili.com/v/popular/all/?spm_id_from=333.1007.0.0")

if __name__ == "__main__":
    UT()