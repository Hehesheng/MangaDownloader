import os
import re
import time
import argparse

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from tqdm import tqdm

from proxies import proxies


def download_img(base_url, img_url, i, file_name_len, saving_dir, title):
    # print(f"download {title} page {i+1}")
    img_request_res = requests.get(base_url+img_url, proxies=proxies)
    img_data = img_request_res.content
    split_res = re.split('[/.]', img_url)
    img_name = str(i+1).zfill(file_name_len) + "." + split_res[-1]
    with open(os.path.join(saving_dir, img_name), 'wb') as handler:
        handler.write(img_data)


def get_next_link(soup, base_url, processed_urls) -> str:
    p_tag = soup.find(lambda tag: tag.name == "p" and "下一" in tag.text)
    if p_tag is not None:
        return base_url + p_tag.find('a')['href']

    p_tags = soup.find_all('a')
    for i, p_tag in enumerate(p_tags):
        link_path = p_tag['href']
        if link_path[0] != '/':
            continue
        res_link = base_url + link_path
        if res_link not in processed_urls:
            return res_link

    return None


def generate_saving_dir(name) -> str:
    root_dir = "./download/"
    if name is None:
        return root_dir
    return root_dir + name + '/'


def main(args):
    if args.url == "":
        return
    next_link = args.url
    target_dir = args.dir
    base_saving_dir = generate_saving_dir(target_dir)
    max_threads = args.thread
    processed_urls = []
    while next_link is not None:
        processed_urls.append(next_link)
        parsed_url = urlparse(next_link)
        base_url = parsed_url.scheme + "://" + parsed_url.netloc
        response = requests.get(next_link, proxies=proxies)
        soup = BeautifulSoup(response.text, 'html.parser')

        img_tags = soup.find_all('img')
        img_num = len(img_tags)
        file_name_len = len(str(len(img_tags)))

        web_title = soup.find('title')
        title = ''
        try:
            title = web_title.text
        except:
            title = str(int(time.time()))
            print(f"Could not find title, rename at:\n{title}")

        if target_dir is None:
            target_dir = re.split('[-\s]', title)[0]
            base_saving_dir = generate_saving_dir(target_dir)
            print(
                f"Not config saving directory, saving to:\n{base_saving_dir}")

        print(
            f"begin download web img, title:\n{title},\nweb url:{next_link},\nimg num:{img_num}")

        saving_dir = os.path.join(base_saving_dir, title)
        if not os.path.exists(saving_dir):
            os.makedirs(saving_dir)
            print(f"mkdir:{title}")

        pbar = tqdm(total=img_num,
                    desc=f"Downloading {title}", unit="image")
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            for i, img_tag in enumerate(img_tags):
                img_url = img_tag['src']
                executor.submit(download_img, base_url, img_url, i,
                                file_name_len, saving_dir, title).add_done_callback(lambda p: pbar.update())

        pbar.close()
        next_link = get_next_link(soup, base_url, processed_urls)
        if next_link is not None:
            print(f"find next link:\n{next_link}\ncontinue downloading")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='manga downloader', description='Download images from a given URL.')
    parser.add_argument('url', default="", type=str,
                        help='The URL to download images from.')
    parser.add_argument('-d', '--dir', default=None, type=str,
                        help='The directory to download images from.')
    parser.add_argument('-t', '--thread', default=8,
                        type=int, help='The downloader threads.')
    args = parser.parse_args()
    main(args)
