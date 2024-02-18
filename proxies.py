__host_ip = '172.25.32.1'

http_proxy = f'http://{__host_ip}:7890'
https_proxy = f'http://{__host_ip}:7890'

proxies = {
    'http': http_proxy,
    'https': https_proxy,
}
