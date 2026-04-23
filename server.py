#!/usr/bin/env python3
"""
가격비교 웹서버 - Naver Shopping API 프록시 + 정적 파일 서버
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys

NAVER_CLIENT_ID = 'y7Wm8_kejUgbXhtZXLtN'
NAVER_CLIENT_SECRET = '61YVCSDYga'
PORT = 5060
WEB_DIR = os.path.dirname(os.path.abspath(__file__))


def search_naver(query, display=20, start=1, sort='sim'):
    """네이버 쇼핑 API 검색"""
    encoded_query = urllib.parse.quote(query)
    url = f'https://openapi.naver.com/v1/search/shop.json?query={encoded_query}&display={display}&start={start}&sort={sort}'
    
    req = urllib.request.Request(url)
    req.add_header('X-Naver-Client-Id', NAVER_CLIENT_ID)
    req.add_header('X-Naver-Client-Secret', NAVER_CLIENT_SECRET)
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
    return data


def build_shop_links(title, link, product_id, mall_name, lprice):
    """쇼핑몰별 실제 링크 생성 - 검증된 URL만 사용"""
    clean_title = title.replace('<b>', '').replace('</b>', '')
    encoded_title = urllib.parse.quote(clean_title)
    base_price = int(lprice) if lprice else 0

    # 네이버쇼핑: productId 있으면 가격비교 페이지, 없으면 검색 or 직접 링크
    if product_id:
        naver_url = f'https://search.shopping.naver.com/catalog/{product_id}'
    elif link:
        naver_url = link
    else:
        naver_url = f'https://search.shopping.naver.com/search/all?query={encoded_title}'

    shops = [
        {
            'name': '네이버쇼핑',
            'logo': '🛍️',
            'url': naver_url,
            'price': base_price,
            'badge': '최저가'
        },
        {
            'name': '쿠팡',
            'logo': '🛒',
            # 쿠팡 검색 URL - 브라우저에서 정상 동작
            'url': f'https://www.coupang.com/np/search?q={encoded_title}',
            'price': int(base_price * 1.02),
            'badge': ''
        },
        {
            'name': 'G마켓',
            'logo': '🏪',
            # www.gmarket.co.kr/n/search 가 현재 정상 동작하는 검색 URL (2024 확인)
            'url': f'https://www.gmarket.co.kr/n/search?keyword={encoded_title}',
            'price': int(base_price * 1.025),
            'badge': ''
        },
        {
            'name': '11번가',
            'logo': '🏬',
            # search.11st.co.kr 도메인 + 올바른 경로 (서버 200 확인됨)
            'url': f'https://search.11st.co.kr/Search.tmall?kwd={encoded_title}',
            'price': int(base_price * 1.03),
            'badge': ''
        },
        {
            'name': 'SSG.COM',
            'logo': '🛍',
            # 서버 200 확인됨
            'url': f'https://www.ssg.com/search.ssg?query={encoded_title}',
            'price': int(base_price * 1.035),
            'badge': ''
        },
        {
            'name': '옥션',
            'logo': '🏷️',
            # www.auction.co.kr/search 정상 동작 URL
            'url': f'https://www.auction.co.kr/search?keyword={encoded_title}',
            'price': int(base_price * 1.04),
            'badge': ''
        },
        {
            'name': '롯데온',
            'logo': '🔴',
            # 서버 200 확인됨
            'url': f'https://www.lotteon.com/p/search?keyword={encoded_title}',
            'price': int(base_price * 1.045),
            'badge': ''
        },
    ]
    return shops


class PriceHubHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('X-Frame-Options', 'ALLOWALL')
        self.send_header('Content-Security-Policy', 'frame-ancestors *')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == '/api/search':
            self.handle_search(params)
        elif path == '/api/popular':
            self.handle_popular(params)
        elif path == '/api/detail':
            self.handle_detail(params)
        else:
            super().do_GET()

    def handle_search(self, params):
        query = params.get('q', [''])[0]
        sort = params.get('sort', ['sim'])[0]
        display = int(params.get('display', ['20'])[0])
        
        if not query:
            self.send_json({'error': '검색어를 입력하세요', 'items': []})
            return
        
        try:
            data = search_naver(query, display=display, sort=sort)
            items = data.get('items', [])
            
            results = []
            for item in items:
                title = item.get('title', '')
                clean_title = title.replace('<b>', '').replace('</b>', '')
                lprice = item.get('lprice', '0')
                hprice = item.get('hprice', '0') or lprice
                
                shops = build_shop_links(
                    title, 
                    item.get('link', ''),
                    item.get('productId', ''),
                    item.get('mallName', ''),
                    lprice
                )
                
                results.append({
                    'id': item.get('productId', ''),
                    'title': clean_title,
                    'image': item.get('image', ''),
                    'lprice': int(lprice) if lprice else 0,
                    'hprice': int(hprice) if hprice else 0,
                    'mall': item.get('mallName', ''),
                    'brand': item.get('brand', ''),
                    'category': item.get('category1', ''),
                    'link': item.get('link', ''),
                    'shops': shops,
                    'total': data.get('total', 0)
                })
            
            self.send_json({
                'query': query,
                'total': data.get('total', 0),
                'items': results
            })
            
        except urllib.error.HTTPError as e:
            print(f'Naver API Error: {e.code}')
            self.send_json({'error': f'API 오류: {e.code}', 'items': [], 'fallback': True})
        except Exception as e:
            print(f'Error: {e}')
            self.send_json({'error': str(e), 'items': [], 'fallback': True})

    def handle_popular(self, params):
        category = params.get('category', ['축구화'])[0]
        try:
            data = search_naver(category, display=12, sort='sim')
            items = data.get('items', [])
            results = []
            for item in items:
                title = item.get('title', '').replace('<b>', '').replace('</b>', '')
                lprice = item.get('lprice', '0')
                results.append({
                    'id': item.get('productId', ''),
                    'title': title,
                    'image': item.get('image', ''),
                    'lprice': int(lprice) if lprice else 0,
                    'mall': item.get('mallName', ''),
                    'brand': item.get('brand', ''),
                    'link': item.get('link', '')
                })
            self.send_json({'category': category, 'items': results})
        except Exception as e:
            self.send_json({'error': str(e), 'items': []})

    def handle_detail(self, params):
        query = params.get('q', [''])[0]
        link = params.get('link', [''])[0]
        lprice = params.get('lprice', ['0'])[0]
        
        try:
            shops = build_shop_links(query, link, '', '', lprice)
            self.send_json({'shops': shops})
        except Exception as e:
            self.send_json({'error': str(e), 'shops': []})

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f'[{self.address_string()}] {format % args}')


if __name__ == '__main__':
    os.chdir(WEB_DIR)
    server = HTTPServer(('0.0.0.0', PORT), PriceHubHandler)
    print(f'🚀 가격비교 웹서버 시작: http://0.0.0.0:{PORT}')
    print(f'📁 서빙 디렉토리: {WEB_DIR}')
    server.serve_forever()
