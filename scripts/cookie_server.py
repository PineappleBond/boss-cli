#!/usr/bin/env python3
"""
本地 HTTP 服务，用于接收 Chrome 扩展发送的 Cookie 并保存到 boss-cli 凭证文件。

启动方式: python scripts/cookie_server.py
端口: 9876
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 添加 boss_cli 到路径
BOSS_CLI_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BOSS_CLI_DIR))

from boss_cli.auth import Credential, save_credential, CREDENTIAL_FILE


class CookieHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        if self.path == '/import-cookies':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                data = json.loads(body)
                
                cookies = data.get('cookies', {})
                
                if not cookies:
                    self.send_error_response('没有收到 Cookie')
                    return
                
                # 保存凭证
                cred = Credential(cookies=cookies)
                save_credential(cred)
                
                # 检查关键 cookie
                has_stoken = '__zp_stoken__' in cookies
                has_wt2 = 'wt2' in cookies
                has_wbg = 'wbg' in cookies
                
                message = f'成功保存 {len(cookies)} 个 Cookie'
                if has_stoken:
                    message += '（包含 __zp_stoken__）'
                
                self.send_json_response({
                    'success': True,
                    'message': message,
                    'cookie_count': len(cookies),
                    'has_stoken': has_stoken,
                    'has_wt2': has_wt2,
                    'has_wbg': has_wbg,
                    'credential_file': str(CREDENTIAL_FILE)
                })
                
                print(f"✅ 已保存 {len(cookies)} 个 Cookie 到 {CREDENTIAL_FILE}")
                
            except Exception as e:
                self.send_error_response(f'保存失败: {str(e)}')
        else:
            self.send_error_response('未知的路径')
    
    def do_GET(self):
        if self.path == '/status':
            try:
                from boss_cli.auth import get_credential
                cred = get_credential()
                if cred:
                    self.send_json_response({
                        'success': True,
                        'has_credentials': True,
                        'cookie_count': len(cred.cookies),
                        'cookie_names': list(cred.cookies.keys())
                    })
                else:
                    self.send_json_response({
                        'success': True,
                        'has_credentials': False
                    })
            except Exception as e:
                self.send_error_response(f'获取状态失败: {str(e)}')
        else:
            self.send_error_response('未知的路径')
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': False, 'error': message}, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        # 不打印日志（避免干扰）
        pass


def main():
    port = 9876
    server = HTTPServer(('127.0.0.1', port), CookieHandler)
    
    print(f"""
╔════════════════════════════════════════════╗
║   Boss直聘 Cookie 导入服务                 ║
║   端口: {port}                              ║
║   状态: 运行中                              ║
╚════════════════════════════════════════════╝

💡 使用方式:
   1. 在 Chrome 扩展中点击 "🚀 执行 boss login"
   2. Cookie 会自动保存到本地凭证文件
   3. 然后执行: boss status 检查登录状态

按 Ctrl+C 停止服务
""")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.shutdown()


if __name__ == '__main__':
    main()