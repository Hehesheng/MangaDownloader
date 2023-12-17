import os
import argparse
import json

import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, unquote
from tqdm import tqdm

from proxies import proxies


def request_url_dir(url: str, query_body: dict, api_path: str = '/api/public/path') -> requests.Response:
    headers = {'Content-Type': 'application/json'}
    query_body_json = json.dumps(query_body)

    response = requests.post(
        url+api_path, headers=headers, data=query_body_json, proxies=proxies)
    if response.status_code != 200:
        print(
            f"request {url}, response:{response.status_code}, check network")
        return None
    return response


def download_file(url: str, filename: str, saving_path: str):
    response = requests.get(url, stream=True, proxies=proxies)

    if response.status_code == 200:
        pbar = tqdm(total=int(response.headers['Content-Length'])//1024,
                    desc=f"Downloading {filename}", unit="kB")
        file_path = saving_path+'/' + filename
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
                    pbar.update()
        pbar.close()


def get_download_list(url: str, query_path: str, page_num: int = 1, page_size: int = 20) -> list:
    query_body = {
        "path": query_path,
        "password": "",
        "page_num": page_num,
        "page_size": page_size,
    }
    response = request_url_dir(url, query_body)
    if response is None:
        return None

    response_content = json.loads(response.content)
    if response_content['code'] != 200 and response_content['message'] != 'success':
        print(f"loads reponse error:{response.content}, check request param")
        return None

    meta_data = response_content['data']['meta']
    files: list = response_content['data']['files']
    if meta_data['total'] > page_num*page_size:
        files += get_download_list(url, query_path,
                                   page_num=page_num+1, page_size=page_size)
    return files


def download_core(base_url: str, path: str, saving_dir: str, threads: int = 8):
    files = get_download_list(base_url, path)
    if files is None:
        return

    if not os.path.exists(saving_dir):
        os.makedirs(saving_dir)
        print(f"mkdir:{saving_dir}")

    pbar = tqdm(total=len(files),
                desc=f"Downloading {path}", unit="file")
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for i, file in enumerate(files):
            file_type = file['type']
            if file_type != 0:
                continue
            filename = file['name']
            file_url = args.base_url + "/d/" + path + "/" + filename
            executor.submit(download_file, file_url, filename, saving_dir).add_done_callback(
                lambda p: pbar.update())
    pbar.close()

    for i, file in enumerate(files):
        file_type = file['type']
        if file_type != 1:
            continue
        download_core(base_url, path+'/'+file['name'],
                      saving_dir+'/'+file['name'], threads=threads)


def main(args):
    download_core(args.base_url, args.path,
                  args.saving_dir+args.path, args.threads)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='download scripe', description='Download files from a given URL.')
    parser.add_argument('url', default="", type=str,
                        help='The URL to download images from.')
    args = parser.parse_args()

    args.threads = 8
    args.saving_dir = './download'

    parsed_url = urlparse(args.url)
    args.base_url = parsed_url.scheme + "://" + parsed_url.netloc
    args.path_url = parsed_url.path
    args.path = unquote(parsed_url.path)

    main(args)
