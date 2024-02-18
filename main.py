import os
import re
import time
import argparse
import asyncio
from urllib.parse import urlparse
from typing import Callable, Any, Optional

import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm
import aiofiles

from proxies import http_proxy


def print_run(func: Callable) -> Callable:
    async def wrapper(*args, **kw):
        print(f'call in: {func.__name__}, args: {args}, kw: {kw}')
        await func(*args, **kw)
        print(f'call out: {func.__name__}, args: {args}, kw: {kw}')
    return wrapper


async def async_download_img(semaphore: asyncio.Semaphore,
                             session: aiohttp.ClientSession,
                             base_url: str,
                             img_url: str,
                             i: int,
                             file_name_len: int,
                             saving_dir: str,
                             title: str) -> None:
    async with semaphore:
        await download_img(session, base_url, img_url, i,
                           file_name_len, saving_dir, title)


async def download_img(session: aiohttp.ClientSession,
                       base_url: str,
                       img_url: str,
                       i: int,
                       file_name_len: int,
                       saving_dir: str,
                       title: str) -> None:
    # print(f"download {title} page {i+1}")
    req_url = img_url
    if re.match('^(http|https):\/\/.*', img_url) is None:
        req_url = base_url + img_url
    img_data = None
    async with session.get(req_url, proxy=http_proxy) as img_request_res:
        img_data = img_request_res.content
        split_res = re.split('[/.]', img_url)
        img_name = str(i+1).zfill(file_name_len) + "." + split_res[-1]
        async with aiofiles.open(os.path.join(saving_dir, img_name), mode='wb') as handler:
            await handler.write(await img_data.read())


def get_next_link(soup: BeautifulSoup,
                  base_url: str,
                  processed_urls: list[str]) -> str:
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


async def process_loop(session: aiohttp.ClientSession,
                       args) -> None:
    next_link: str = args.url
    target_dir: str = args.dir
    base_saving_dir: str = generate_saving_dir(target_dir)
    max_threads: int = args.thread
    processed_urls: list[str] = []
    while next_link is not None:
        processed_urls.append(next_link)
        parsed_url = urlparse(next_link)
        base_url: str = parsed_url.scheme + "://" + parsed_url.netloc
        soup: Optional[BeautifulSoup] = None
        async with session.get(next_link, proxy=http_proxy) as response:
            soup: BeautifulSoup = BeautifulSoup(await response.text(), 'html.parser')

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

        desc_title = title if (len(title) <= 50) else title[:50-3] + '...'
        pbar = tqdm(total=img_num,
                    desc=f"Downloading {desc_title}", unit="image")
        sem = asyncio.Semaphore(value=max_threads)
        task_list: list[asyncio.Task] = []
        for i, img_tag in enumerate(img_tags):
            img_url = img_tag['src']
            task = asyncio.create_task(async_download_img(sem, session, base_url, img_url, i,
                                                          file_name_len, saving_dir, title))

            def download_task_done_callback(fu: asyncio.Task):
                pbar.update()
            task.add_done_callback(download_task_done_callback)
            task_list.append(task)
            yield
        await asyncio.gather(*task_list)
        pbar.close()

        next_link = get_next_link(soup, base_url, processed_urls)
        if next_link is not None:
            print(f"find next link:\n{next_link}\ncontinue downloading")


async def main(args):
    if args.url == "":
        return
    next_link: str = args.url
    target_dir: str = args.dir
    base_saving_dir: str = generate_saving_dir(target_dir)
    max_threads: int = args.thread
    processed_urls: list[str] = []
    async with aiohttp.ClientSession() as session:
        async for _ in process_loop(session, args):
            # do nothing
            pass


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
    asyncio.run(main(args))
