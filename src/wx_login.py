#!/usr/bin/env python3
"""
微信登录模拟器 - 遵循 Linus 的简洁哲学：
1. 简单的数据结构 (eas_sid -> uuid -> wxcode -> credentials)
2. 没有特殊情况，没有不必要的抽象
3. 解决真实问题，而不是假想的问题
"""

import requests
import re
import time
import random
from html.parser import HTMLParser


def generate_eas_sid():
    """
    生成 eas_sid cookie 值。
    来自 wxlogin.md 的 JavaScript 逻辑：
    - 字符集: A-Za-z0-9 (62个字符)
    - 格式: 13次循环 [随机字符 + 时间戳字符]
    - 返回: 26字符字符串
    """
    charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    n = len(charset)
    result = ""

    # 获取时间戳字符串
    timestamp = str(int(time.time() * 1000))

    # 确保有足够的数字
    if len(timestamp) < 13:
        # 备用方案: 生成随机数字
        timestamp = str(random.randint(10**12, 10**13 - 1))

    # 构建 eas_sid: 交替放置随机字符和时间戳数字
    for i in range(13):
        random_char = charset[random.randint(0, n - 1)]
        result += random_char + timestamp[i]

    return result


class ImgSrcParser(HTMLParser):
    """
    最小化 HTML 解析器，用于提取 <img class="js_qrcode_img web_qrcode_img" src="...">
    """
    def __init__(self):
        super().__init__()
        self.qrcode_src = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.qrcode_src:
            attrs_dict = dict(attrs)
            class_value = attrs_dict.get('class', '')
            if 'js_qrcode_img' in class_value and 'web_qrcode_img' in class_value:
                self.qrcode_src = attrs_dict.get('src')


class WeChatLogin:
    def __init__(self, proxy=None):
        self.session = requests.Session()
        self.eas_sid = None
        self.uuid = None

        # 配置代理
        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
            print(f"[+] 使用代理: {proxy}")

        # 浏览器固定请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })

    def get_qrcode_page(self):
        """
        步骤1: 请求二维码登录页面，从 img src 中提取 uuid。
        返回轮询所需的 uuid。
        """
        # 生成 eas_sid cookie
        self.eas_sid = generate_eas_sid()
        print(f"[+] 生成 eas_sid: {self.eas_sid}")

        # 设置 cookie
        self.session.cookies.set('eas_sid', self.eas_sid, domain='qq.com', path='/')

        url = 'https://open.weixin.qq.com/connect/qrconnect'
        params = {
            'appid': 'wxfa0c35392d06b82f',
            'scope': 'snsapi_login',
            'redirect_uri': 'https://iu.qq.com/comm-htdocs/login/milosdk/wx_pc_redirect.html?appid=wxfa0c35392d06b82f&sServiceType=undefined&originalUrl=https%3A%2F%2Frocom.qq.com%2Fact%2Fa20250901certification%2Findex.html&oriOrigin=https%3A%2F%2Frocom.qq.com',
            'state': '1',
            'login_type': 'jssdk',
            'self_redirect': 'true',
            'style': 'black'
        }

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'upgrade-insecure-requests': '1',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'iframe',
            'referer': 'https://rocom.qq.com/',
            'priority': 'u=0, i'
        }

        response = self.session.get(url, params=params, headers=headers)

        if response.status_code == 200:
            html = response.text

            # 解析 HTML 提取二维码 src
            parser = ImgSrcParser()
            parser.feed(html)

            if parser.qrcode_src:
                # 从 src 中提取 uuid: /connect/qrcode/071dS1dZ2ZqX0w3i
                match = re.search(r'/connect/qrcode/([^"]+)', parser.qrcode_src)
                if match:
                    self.uuid = match.group(1)
                    print(f"[+] 提取 uuid: {self.uuid}")
                    print(f"[+] 二维码 src: {parser.qrcode_src}")
                    return self.uuid
                else:
                    raise Exception("无法从 src 提取 uuid")
            else:
                raise Exception("HTML 中未找到二维码 img 标签")
        else:
            raise Exception(f"获取二维码页面失败: {response.status_code}")

    def get_qrcode_image(self):
        """
        步骤2: 使用 uuid 获取实际的二维码图片。
        返回二维码图片的二进制数据。
        """
        if not self.uuid:
            raise Exception("uuid 不可用，请先调用 get_qrcode_page()")

        url = f'https://open.weixin.qq.com/connect/qrcode/{self.uuid}'

        headers = {
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-dest': 'image',
            'referer': f'https://open.weixin.qq.com/connect/qrconnect?appid=wxfa0c35392d06b82f&scope=snsapi_login&redirect_uri=https%3A%2F%2Fiu.qq.com%2Fcomm-htdocs%2Flogin%2Fmilosdk%2Fwx_pc_redirect.html%3Fappid%3Dwxfa0c35392d06b82f%26sServiceType%3Dundefined%26originalUrl%3Dhttps%253A%252F%252Frocom.qq.com%252Fact%252Fa20250901certification%252Findex.html%26oriOrigin%3Dhttps%253A%252F%252Frocom.qq.com&state=1&login_type=jssdk&self_redirect=true&style=black',
            'priority': 'u=2, i'
        }

        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            print(f"[+] 二维码图片大小: {len(response.content)} 字节")
            return response.content
        else:
            raise Exception(f"获取二维码图片失败: {response.status_code}")

    def check_scan_status(self):
        """
        步骤3: 轮询检查二维码是否已被扫描。
        返回状态信息，登录成功时包含 wxcode。
        """
        if not self.uuid:
            raise Exception("uuid 不可用，请先调用 get_qrcode_page()")

        url = f'https://lp.open.weixin.qq.com/connect/l/qrconnect'
        params = {
            'uuid': self.uuid
        }

        headers = {
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-dest': 'script',
            'referer': 'https://open.weixin.qq.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }

        response = self.session.get(url, params=params, headers=headers)

        if response.status_code == 200:
            text = response.text
            # 解析响应: window.wx_errcode=408;window.wx_code='';

            errcode_match = re.search(r'window\.wx_errcode=(\d+)', text)
            code_match = re.search(r"window\.wx_code='([^']*)'", text)

            if errcode_match:
                errcode = errcode_match.group(1)
                wxcode = code_match.group(1) if code_match else ''

                return {
                    'errcode': errcode,
                    'wxcode': wxcode,
                    'raw': text
                }

            return {'raw': text}
        else:
            raise Exception(f"检查扫码状态失败: {response.status_code}")

    def exchange_code_for_credentials(self, wxcode, callback=None):
        """
        步骤4: 用 wxcode 换取 access_token 和 openid。
        返回凭证字典。
        """
        if not callback:
            # 生成随机 callback 名称，如 miloJsonpCb_5928
            callback = f"miloJsonpCb_{random.randint(1000, 99999)}"

        url = 'https://apps.game.qq.com/ams/ame/codeToOpenId.php'

        params = {
            'callback': callback,
            'appid': 'wxfa0c35392d06b82f',
            'wxcode': wxcode,
            'originalUrl': 'https://rocom.qq.com/act/a20250901certification/index.html',
            'wxcodedomain': 'iu.qq.com',
            'acctype': 'wx',
            'sServiceType': 'undefined',
            '_': str(int(time.time() * 1000))
        }

        headers = {
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-dest': 'script',
            'referer': 'https://rocom.qq.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }

        response = self.session.get(url, params=params, headers=headers)

        if response.status_code == 200:
            text = response.text
            # 解析 JSONP: miloJsonpCb_41463({...})
            match = re.search(r'miloJsonpCb_\d+\(({.*?})\)', text)
            if match:
                import json
                data = json.loads(match.group(1))

                if data.get('iRet') == 0:
                    # 解析 sMsg，它包含实际的凭证信息
                    smsg = data.get('sMsg', '{}')
                    credentials = json.loads(smsg)

                    print(f"[+] ✓ 获取到 openid: {credentials.get('openid')}")
                    print(f"[+] ✓ 获取到 access_token: {credentials.get('access_token')}")
                    print(f"[+] ✓ 获取到 unionid: {credentials.get('unionid')}")
                    print(f"[+] ✓ 过期时间: {credentials.get('expires_in')}秒")

                    return credentials
                else:
                    raise Exception(f"codeToOpenId 失败: iRet={data.get('iRet')}, sMsg={data.get('sMsg')}")
            else:
                raise Exception(f"无法解析 JSONP 响应: {text}")
        else:
            raise Exception(f"请求失败，状态码: {response.status_code}")


def main():
    print("[*] 微信登录模拟器 - 启动中")

    # 不使用代理初始化
    wx = WeChatLogin(proxy=None)

    # 步骤1: 获取二维码页面并提取 uuid
    print("\n[*] 步骤 1: 获取二维码页面并提取 uuid...")
    try:
        uuid = wx.get_qrcode_page()
    except Exception as e:
        print(f"[!] 获取二维码页面失败: {e}")
        return False

    # 步骤2: 获取实际的二维码图片
    print("\n[*] 步骤 2: 获取二维码图片...")
    try:
        qr_image = wx.get_qrcode_image()
        # 保存二维码供扫描
        with open('wx_qrcode.png', 'wb') as f:
            f.write(qr_image)
        print("[+] 二维码已保存到 wx_qrcode.png")
    except Exception as e:
        print(f"[!] 获取二维码图片失败: {e}")
        return False

    # 步骤3: 轮询二维码扫描状态
    print("\n[*] 步骤 3: 轮询扫码状态...")
    print("[*] 请使用微信扫描 wx_qrcode.png")

    max_attempts = 60  # 最多轮询 60 次 (约2分钟)
    poll_interval = 2  # 每 2 秒轮询一次

    for attempt in range(1, max_attempts + 1):
        try:
            status = wx.check_scan_status()
            errcode = status.get('errcode', '')
            wxcode = status.get('wxcode', '')

            if errcode == '408':
                # 等待扫码
                print(f"[{attempt}/{max_attempts}] 等待扫码...")
            elif errcode == '404':
                # 二维码已扫描，等待确认
                print(f"[+] 二维码已扫描，请在手机上确认登录...")
            elif errcode == '405':
                # 登录成功
                print(f"[+] 登录成功!")
                if wxcode:
                    print(f"[+] 获取到 wxcode: {wxcode}")

                    # 步骤4: 用 wxcode 换取凭证
                    print("\n[*] 步骤 4: 换取 access_token 和 openid...")
                    try:
                        credentials = wx.exchange_code_for_credentials(wxcode)
                    except Exception as e:
                        print(f"[!] 换取凭证失败: {e}")
                        return False

                    # 打印最终登录凭证
                    print(f"\n{'='*60}")
                    print(f"[+] 🎉 登录成功!")
                    print(f"{'='*60}")
                    print(f"OpenID: {credentials.get('openid')}")
                    print(f"UnionID: {credentials.get('unionid')}")
                    print(f"Access Token: {credentials.get('access_token')}")
                    print(f"Refresh Token: {credentials.get('refresh_token')}")
                    print(f"过期时间: {credentials.get('expires_in')}秒")

                    # 构建 Cookie 字符串（参考 wxlogin.md 步骤4的格式）
                    cookie_str = (
                        f"acctype=wx; "
                        f"openid={credentials.get('openid')}; "
                        f"access_token={credentials.get('access_token')}; "
                        f"appid=wxfa0c35392d06b82f; "
                        f"ieg_ams_token=; "
                        f"ieg_ams_session_token=; "
                        f"ieg_ams_token_time=; "
                        f"ieg_ams_sign="
                    )

                    # 输出可直接用于浏览器/curl 的 Cookie 字符串
                    print("\n" + "=" * 60)
                    print("完整 Cookie 字符串 (可直接用于浏览器/curl):")
                    print("=" * 60)
                    print(cookie_str)

                    # 保存到文件
                    with open('wx_cookies.txt', 'w', encoding='utf-8') as f:
                        f.write(cookie_str)

                    print("\n[+] 完整 Cookies 已保存到 wx_cookies.txt")
                    print("[+] 可直接复制到浏览器 DevTools 或用于 curl 请求")

                    return True
                else:
                    print("[!] 警告: 未获取到 wxcode")
                    return False
            else:
                # 其他状态码
                print(f"[!] 未知状态码 {errcode}: {status.get('raw')}")
                return False

        except Exception as e:
            print(f"[!] 检查状态出错: {e}")
            return False

        # 如果未成功，等待后继续轮询
        if attempt < max_attempts:
            time.sleep(poll_interval)

    print("[!] 超时: 二维码未被扫描")
    return False


if __name__ == '__main__':
    main()
