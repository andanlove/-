# _*_ coding: utf-8 _*_
import json
import os
import re
from hashlib import md5
from multiprocessing import Pool
from urllib.parse import urlencode

import pymongo
import requests
from bs4 import BeautifulSoup
from requests import RequestException

from toutiao.config import *

client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

#获取索引页的信息
def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': '3',
        'from': 'gallery',
    }
    proxies = {
        'https': 'https://121.40.183.166:80',
        'http': 'http://118.190.95.35:9001',
    }
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:  # ,proxies = proxies,verify=False
        response = requests.get(url=url, headers=headers)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页失败')
        return None

#解析的到详情页的url
def parse_page_index(html):
    data = json.loads(html)
    if 'data' in data.keys():
        # print(data.keys())
        for item in data.get('data'):
            yield item.get('article_url')

#获取详情页信息
def get_page_detail(url):
    proxies = {
        'https': 'https://221.1.200.242:38652',
        'http': 'http://221.7.255.167:8080',
    }
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    try:
        response = requests.get(url=url, headers=headers)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页失败')
        return None

#解析图片信息
def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].get_text()
    # print(title)
    images_patter = re.compile(r'gallery: JSON.parse(.*?)siblingList:', re.S)
    result = re.search(images_patter, html)

    if result:
        data = result.group(1).replace("\\", "")
        data = data.strip()[2:-3]
        # print(data)
        data = json.loads(data)
        if 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                download_image(image)
            return {
                'title': title,
                'url': url,
                'images': images,
            }

    # print(html)

#将url保存到mongodb中
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储成功', result)
        return True
    return False

#下载图片
def download_image(url):
    print('正在下载' + url)
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    }
    try:
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print('请求图片失败', url)
        return None

#保存图片
def save_image(content):
    file_path = '{0}\{1}.{2}'.format(os.getcwd()+'\images', md5(content).hexdigest(), 'jpg')
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as fp:
            fp.write(content)
            fp.close()


def main(page):
    html = get_page_index(page, KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html, url)
            if result:
                save_to_mongo(result)


if __name__ == '__main__':
    groups = [x * 20 for x in range(START, END + 1)]
    pool = Pool()
    pool.map(main,groups)

