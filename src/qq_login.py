#!/usr/bin/env python3
"""
QQ Login Simulator - Clean implementation following Linus's philosophy:
1. Simple data structures (qrsig -> ptqrtoken -> status)
2. No special cases, no unnecessary abstraction
3. Solve the real problem, not imaginary ones
"""

import requests
import re
import time


def hash33_ptqrtoken(s):
    """
    Hash33 algorithm to calculate ptqrtoken from qrsig.
    JavaScript: e = 0, then e += (e << 5) + charCodeAt(i)
    """
    e = 0
    for c in s:
        e += (e << 5) + ord(c)
    return e & 0x7fffffff


def hash33_gtk(s):
    """
    Hash33 algorithm to calculate g_tk from p_skey.
    JavaScript: hash = 5381, then hash += (hash << 5) + charCodeAt(i)
    """
    e = 5381
    for c in s:
        e += (e << 5) + ord(c)
    return e & 0x7fffffff


def calculate_g_tk(p_skey):
    """
    Calculate g_tk from p_skey cookie.
    """
    return hash33_gtk(p_skey)


class QQLogin:
    def __init__(self, proxy=None, progress_callback=None):
        self.session = requests.Session()
        self.qrsig = None
        self.ptqrtoken = None
        self.progress_callback = progress_callback  # GUI回调函数

        # 配置代理
        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
            self._log(f"[+] 使用代理: {proxy}")

        # Fixed headers from the real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })

    def _log(self, message):
        """统一日志输出"""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(message)

    def get_qrcode(self):
        """
        Step 1: Fetch QR code and extract qrsig from cookies.
        Returns binary QR code image data.
        """
        url = 'https://xui.ptlogin2.qq.com/ssl/ptqrshow'
        params = {
            'appid': '716027609',
            'e': '2',
            'l': 'M',
            's': '3',
            'd': '72',
            'v': '4',
            't': '0.3760789986155184',
            'daid': '383',
            'pt_3rd_aid': '101491592',
            'u1': 'https://graph.qq.com/oauth2.0/login_jump'
        }

        headers = {
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=716027609&daid=383&style=33&login_text=%E7%99%BB%E5%BD%95&hide_title_bar=1&hide_border=1&target=self&s_url=https%3A%2F%2Fgraph.qq.com%2Foauth2.0%2Flogin_jump&pt_3rd_aid=101491592&pt_feedback_link=https%3A%2F%2Fsupport.qq.com%2Fproducts%2F77942%3FcustomInfo%3Dmilo.qq.com.appid101491592&theme=2&verify_theme=',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-origin'
        }

        response = self.session.get(url, params=params, headers=headers)

        if response.status_code == 200:
            # Extract qrsig from cookies
            self.qrsig = self.session.cookies.get('qrsig', domain='ptlogin2.qq.com')
            if not self.qrsig:
                # 尝试不指定domain
                self.qrsig = self.session.cookies.get('qrsig')

            if self.qrsig:
                # Calculate ptqrtoken using hash33_ptqrtoken (初始值 = 0)
                self.ptqrtoken = hash33_ptqrtoken(self.qrsig)
                self._log(f"[+] qrsig: {self.qrsig[:32]}...")
                self._log(f"[+] ptqrtoken: {self.ptqrtoken}")
                return response.content
            else:
                raise Exception("获取 qrsig cookie 失败")
        else:
            raise Exception(f"获取二维码失败: {response.status_code}")

    def check_qr_status(self):
        """
        Step 2: Poll QR code scan status.
        Returns the status response from ptuiCB().
        """
        if not self.ptqrtoken:
            raise Exception("ptqrtoken 不可用，请先调用 get_qrcode()")

        if not self.qrsig:
            raise Exception("qrsig 不可用，请先调用 get_qrcode()")

        url = 'https://xui.ptlogin2.qq.com/ssl/ptqrlogin'
        params = {
            'u1': 'https://graph.qq.com/oauth2.0/login_jump',
            'ptqrtoken': str(self.ptqrtoken),
            'ptredirect': '0',
            'h': '1',
            't': '1',
            'g': '1',
            'from_ui': '1',
            'ptlang': '2052',
            'action': f'0-0-{int(time.time() * 1000)}',
            'js_ver': '25100115',
            'js_type': '1',
            'login_sig': '',
            'pt_uistyle': '40',
            'aid': '716027609',
            'daid': '383',
            'pt_3rd_aid': '101491592',
            'o1vId': '1634c2d803a9d8b684ba497019cebfa3',
            'pt_js_version': '28d22679'
        }

        headers = {
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Referer': 'https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=716027609&daid=383&style=33&login_text=%E7%99%BB%E5%BD%95&hide_title_bar=1&hide_border=1&target=self&s_url=https%3A%2F%2Fgraph.qq.com%2Foauth2.0%2Flogin_jump&pt_3rd_aid=101491592&pt_feedback_link=https%3A%2F%2Fsupport.qq.com%2Fproducts%2F77942%3FcustomInfo%3Dmilo.qq.com.appid101491592&theme=2&verify_theme=',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-origin'
        }

        response = self.session.get(url, params=params, headers=headers)

        if response.status_code == 200:
            # Parse ptuiCB() response
            # Format: ptuiCB('66','0','','0','二维码未失效。', '')
            text = response.text

            # Extract parameters from ptuiCB
            match = re.search(r"ptuiCB\('(\d+)','(\d+)','([^']*)','(\d+)','([^']*)'", text)
            if match:
                status_code = match.group(1)
                return {
                    'status_code': status_code,
                    'param2': match.group(2),
                    'param3': match.group(3),
                    'param4': match.group(4),
                    'message': match.group(5),
                    'raw': text
                }
            return {'raw': text}
        else:
            raise Exception(f"检查状态失败: {response.status_code}")

    def oauth_authorize(self, client_id='101491592', redirect_uri='https://milo.qq.com/comm-htdocs/login/qc_redirect.html', parent_domain='https://rocom.qq.com'):
        """
        Step 4: POST to authorize to get qc_code
        """
        # 获取必要的cookies (不指定domain)
        p_skey = self.session.cookies.get('p_skey')
        ui = self.session.cookies.get('ui')

        if not p_skey:
            raise Exception("p_skey cookie不存在，无法继续OAuth流程")

        # 计算g_tk
        g_tk = calculate_g_tk(p_skey)
        self._log(f"[+] 计算 g_tk: {g_tk}")

        url = 'https://graph.qq.com/oauth2.0/authorize'

        # 构建完整的redirect_uri
        full_redirect_uri = f"{redirect_uri}?parent_domain={parent_domain}&isMiloSDK=1&isPc=1"

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://graph.qq.com',
            'Referer': f'https://graph.qq.com/oauth2.0/show?which=Login&display=pc&response_type=code&state=STATE&client_id={client_id}&redirect_uri={full_redirect_uri}',
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1'
        }

        data = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': full_redirect_uri,
            'scope': '',
            'state': 'STATE',
            'switch': '',
            'from_ptlogin': '1',
            'src': '1',
            'update_auth': '1',
            'openapi': '1010',
            'g_tk': str(g_tk),
            'auth_time': str(int(time.time() * 1000)),
            'ui': ui or ''
        }

        # 禁用自动重定向以获取Location header
        response = self.session.post(url, headers=headers, data=data, allow_redirects=False)
        self._log(f"[+] authorize 响应状态码: {response.status_code}")

        if response.status_code == 302:
            location = response.headers.get('Location', '')
            self._log(f"[+] 重定向: {location}")

            # 提取code参数
            match = re.search(r'[?&]code=([^&]+)', location)
            if match:
                qc_code = match.group(1)
                self._log(f"[+] 获取到 qc_code: {qc_code}")
                return qc_code
            else:
                raise Exception("未在重定向URL中找到code参数")
        else:
            raise Exception(f"authorize失败，状态码: {response.status_code}")

    def exchange_code_for_token(self, qc_code, client_id='101491592', redirect_uri='https://milo.qq.com/comm-htdocs/login/qc_redirect.html'):
        """
        Step 5: Exchange qc_code for openid and access_token
        """
        url = 'https://ams.game.qq.com/ams/userLoginSvr'

        params = {
            'a': 'qcCodeToOpenId',
            'qc_code': qc_code,
            'appid': client_id,
            'redirect_uri': redirect_uri,
            'callback': 'miloJsonpCb_32411',
            '_': str(int(time.time() * 1000))
        }

        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://rocom.qq.com/',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-site'
        }

        response = self.session.get(url, params=params, headers=headers)
        self._log(f"[+] qcCodeToOpenId 响应状态码: {response.status_code}")

        if response.status_code == 200:
            text = response.text
            # 解析JSONP响应: miloJsonpCb_32411({...})
            match = re.search(r'miloJsonpCb_\d+\(({.*?})\)', text)
            if match:
                import json
                data = json.loads(match.group(1))

                if data.get('iRet') == '0':
                    openid = data.get('openid')
                    access_token = data.get('access_token')
                    expires_in = data.get('expires_in')

                    self._log(f"[+] ✓ 获取到 openid: {openid}")
                    self._log(f"[+] ✓ 获取到 access_token: {access_token}")
                    self._log(f"[+] ✓ 过期时间: {expires_in}秒")

                    return {
                        'openid': openid,
                        'access_token': access_token,
                        'expires_in': expires_in
                    }
                else:
                    raise Exception(f"qcCodeToOpenId失败: {data.get('sMsg')}")
            else:
                raise Exception(f"无法解析响应: {text}")
        else:
            raise Exception(f"请求失败，状态码: {response.status_code}")

    def login(self, max_poll_seconds=120, poll_interval=2, qr_callback=None):
        """
        完整登录流程 - 获取二维码→轮询扫码→获取Cookie

        Args:
            max_poll_seconds: 最大轮询时长(秒)
            poll_interval: 轮询间隔(秒)
            qr_callback: 二维码回调函数 callback(qr_image_bytes)

        Returns:
            Cookie字符串 (格式: "acctype=qc; openid=...; access_token=...; appid=101491592; ieg_ams_token=")

        Raises:
            Exception: 登录失败时抛出异常
        """
        # Step 1: 获取二维码
        self._log("[*] 步骤 1: 获取二维码...")
        qr_image = self.get_qrcode()
        self._log(f"[+] 二维码图片大小: {len(qr_image)} 字节")

        # 调用回调显示二维码
        if qr_callback:
            qr_callback(qr_image)

        # Step 2: 轮询二维码状态
        self._log("[*] 步骤 2: 等待扫码...")
        max_attempts = max_poll_seconds // poll_interval

        for attempt in range(1, int(max_attempts) + 1):
            status = self.check_qr_status()
            status_code = status.get('status_code', '')
            message = status.get('message', '')

            if status_code == '66':
                # 二维码未失效，继续等待
                self._log(f"[{attempt}/{int(max_attempts)}] {message}")
            elif status_code == '67':
                # 二维码认证中
                self._log(f"[+] {message}")
            elif status_code == '0':
                # 登录成功
                self._log(f"[+] {message}")
                redirect_url = status.get('param3', '')

                if not redirect_url:
                    raise Exception("未获取到重定向URL")

                # Step 3: 访问check_sig获取OAuth cookies
                self._log("[*] 步骤 3: 访问 check_sig...")
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Referer': 'https://xui.ptlogin2.qq.com/',
                    'Sec-Fetch-Site': 'same-site',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Dest': 'iframe',
                    'Upgrade-Insecure-Requests': '1',
                    'Connection': 'keep-alive'
                }

                check_sig_response = self.session.get(redirect_url, headers=headers, allow_redirects=False)
                self._log(f"[+] check_sig 响应状态码: {check_sig_response.status_code}")

                if check_sig_response.status_code == 302:
                    login_jump_url = check_sig_response.headers.get('Location', '')
                    self._log(f"[+] 302重定向到: {login_jump_url}")
                    self.session.get(login_jump_url, headers=headers)

                # 检查OAuth cookies
                p_skey = self.session.cookies.get('p_skey')
                pt4_token = self.session.cookies.get('pt4_token')

                if not (p_skey and pt4_token):
                    raise Exception("未获取到 OAuth cookies (p_skey, pt4_token)")

                self._log("[+] ✓ 已获取 OAuth cookies")

                # Step 4: OAuth authorize获取qc_code
                self._log("[*] 步骤 4: OAuth authorize...")
                qc_code = self.oauth_authorize()

                # Step 5: 换取openid和access_token
                self._log("[*] 步骤 5: 换取 openid 和 access_token...")
                token_info = self.exchange_code_for_token(qc_code)

                # 构建Cookie字符串
                cookie_str = f"acctype=qc; openid={token_info['openid']}; access_token={token_info['access_token']}; appid=101491592; ieg_ams_token="

                self._log("[+] 🎉 登录成功!")
                return cookie_str

            else:
                # 其他状态码(如65=二维码失效)
                raise Exception(f"状态码 {status_code}: {message}")

            # 等待后继续轮询
            if attempt < max_attempts:
                time.sleep(poll_interval)

        raise Exception("超时: 二维码未被扫描")


def main():
    print("[*] QQ 登录模拟器 - 启动中")

    # Initialize without proxy
    qq = QQLogin(proxy=None)

    # Step 1: Get QR code
    print("\n[*] 步骤 1: 获取二维码...")
    qr_image = qq.get_qrcode()
    print(f"[+] 二维码图片大小: {len(qr_image)} 字节")

    # Save QR code for scanning
    with open('qrcode.png', 'wb') as f:
        f.write(qr_image)
    print("[+] 二维码已保存到 qrcode.png")

    # Step 2: Poll QR code status
    print("\n[*] 步骤 2: 轮询二维码状态...")
    print("[*] 请使用手机QQ扫描 qrcode.png")

    max_attempts = 60  # 最多轮询60次 (约2分钟)
    poll_interval = 2  # 每2秒轮询一次

    for attempt in range(1, max_attempts + 1):
        try:
            status = qq.check_qr_status()
            status_code = status.get('status_code', '')
            message = status.get('message', '')

            if status_code == '66':
                # 二维码未失效，继续等待
                print(f"[{attempt}/{max_attempts}] {message}")
            elif status_code == '67':
                # 二维码认证中
                print(f"[+] {message}")
            elif status_code == '0':
                # 登录成功
                print(f"[+] {message}")
                redirect_url = status.get('param3', '')
                if redirect_url:
                    print(f"[+] 重定向URL: {redirect_url}")

                    # Step 3: 访问check_sig URL (会302重定向到login_jump并设置OAuth cookies)
                    print("\n[*] 步骤 3: 访问 check_sig...")

                    # 使用浏览器相同的headers访问check_sig
                    headers = {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br, zstd',
                        'Accept-Language': 'zh-CN,zh;q=0.9',
                        'Referer': 'https://xui.ptlogin2.qq.com/',
                        'Sec-Fetch-Site': 'same-site',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Dest': 'iframe',
                        'Upgrade-Insecure-Requests': '1',
                        'Connection': 'keep-alive'
                    }

                    # 禁用自动重定向，手动处理以确保保存302响应的cookies
                    check_sig_response = qq.session.get(redirect_url, headers=headers, allow_redirects=False)
                    print(f"[+] check_sig 响应状态码: {check_sig_response.status_code}")

                    if check_sig_response.status_code == 302:
                        login_jump_url = check_sig_response.headers.get('Location', '')
                        print(f"[+] 302重定向到: {login_jump_url}")

                        # 手动访问login_jump
                        login_jump_response = qq.session.get(login_jump_url, headers=headers)
                        print(f"[+] login_jump 响应状态码: {login_jump_response.status_code}")
                    else:
                        print(f"[!] 警告: check_sig没有返回302，而是{check_sig_response.status_code}")

                    # 检查是否获取到OAuth cookies (不指定domain)
                    p_skey = qq.session.cookies.get('p_skey')
                    pt4_token = qq.session.cookies.get('pt4_token')

                    print(f"\n[DEBUG] 当前所有cookies:")
                    for cookie in qq.session.cookies:
                        print(f"  {cookie.name} = {cookie.value[:50]}...")

                    if not (p_skey and pt4_token):
                        print(f"[!] 错误: 未获取到 OAuth cookies (p_skey, pt4_token)")
                        return False

                    print(f"[+] ✓ 已获取 OAuth cookies")

                    # Step 4: POST authorize 获取qc_code
                    print("\n[*] 步骤 4: OAuth authorize...")
                    try:
                        qc_code = qq.oauth_authorize()
                    except Exception as e:
                        print(f"[!] authorize 失败: {e}")
                        return False

                    # Step 5: 用qc_code换取openid和access_token
                    print("\n[*] 步骤 5: 换取 openid 和 access_token...")
                    try:
                        token_info = qq.exchange_code_for_token(qc_code)
                    except Exception as e:
                        print(f"[!] 换取token失败: {e}")
                        return False

                    # 打印最终登录凭证
                    print(f"\n{'='*60}")
                    print(f"[+] 🎉 登录成功!")
                    print(f"{'='*60}")
                    print(f"OpenID: {token_info['openid']}")
                    print(f"Access Token: {token_info['access_token']}")
                    print(f"过期时间: {token_info['expires_in']}秒")

                    # 构建简洁的 Cookie 字符串（固定格式，只包含必要的5个字段）
                    cookie_str = f"acctype=qc; openid={token_info['openid']}; access_token={token_info['access_token']}; appid=101491592; ieg_ams_token="

                    # 输出可直接用于浏览器/curl的Cookie字符串
                    print("\n" + "=" * 60)
                    print("完整 Cookie 字符串 (可直接用于浏览器/curl):")
                    print("=" * 60)
                    print(cookie_str)

                    # 保存到文件
                    with open('cookies.txt', 'w', encoding='utf-8') as f:
                        f.write(cookie_str)

                    print("\n[+] 完整 Cookies 已保存到 cookies.txt")
                    print("[+] 可直接复制到浏览器 DevTools 或用于 curl 请求")

                    return True
                else:
                    print("[!] 警告: 未获取到重定向URL")
                    return False
            else:
                # 其他状态码 (如65=二维码失效)
                print(f"[!] 状态码 {status_code}: {message}")
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
