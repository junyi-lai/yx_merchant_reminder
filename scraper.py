"""
网页抓取模块
负责从远行商人网页获取商品信息
"""
import requests
import logging
from config import config


logger = logging.getLogger(__name__)


class MerchantScraper:
    """远行商人 API 抓取类"""
    
    def __init__(self):
        # 使用 API 接口而不是 HTML 页面
        self.api_url = "https://roco.dayun.cool/api/merchant"
        self.headers = config.HEADERS
        self.timeout = config.REQUEST_TIMEOUT
        self.max_retries = config.MAX_RETRIES
    
    def fetch_merchant_data(self):
        """
        获取远行商人商品数据
        
        Returns:
            dict: 包含商品列表和刷新时间的字典
            {
                'items': [{'name': '商品名'}, ...],
                'refresh_time': '刷新时间'
            }
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"正在访问远行商人 API (尝试 {attempt + 1}/{self.max_retries})")
                
                response = requests.get(
                    self.api_url,
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                data = response.json()
                
                if not data.get('success'):
                    logger.error(f"API 返回失败：{data}")
                    continue
                
                # 从 API 响应中提取数据
                items = self._parse_api_response(data)
                refresh_time = self._extract_refresh_time_from_api(data)
                
                logger.info(f"成功获取 {len(items)} 个商品")
                
                return {
                    'items': items,
                    'refresh_time': refresh_time,
                    'raw_data': data  # 保留原始数据供参考
                }
                
            except requests.exceptions.RequestException as e:
                logger.error(f"网络请求失败：{e}")
                if attempt == self.max_retries - 1:
                    raise
                continue
            except Exception as e:
                logger.error(f"解析数据失败：{e}")
                if attempt == self.max_retries - 1:
                    raise
                continue
        
        return {'items': [], 'refresh_time': '未知', 'raw_data': {}}
    
    def _parse_api_response(self, data):
        """
        解析 API 响应数据
        
        Args:
            data: API 返回的 JSON 数据
            
        Returns:
            list: 商品列表 [{'name': '商品名'}, ...]
        """
        items = []
        
        # 优先使用 itemDetails（包含图标等详细信息）
        if 'itemDetails' in data and data['itemDetails']:
            for item_detail in data['itemDetails']:
                items.append({
                    'name': item_detail.get('name', ''),
                    'icon_url': item_detail.get('icon_url', '')
                })
        # 回退到 items（只有商品名）
        elif 'items' in data and data['items']:
            for item_name in data['items']:
                items.append({
                    'name': item_name
                })
        
        return items
    
    def _extract_refresh_time_from_api(self, data):
        """
        从 API 响应中提取刷新时间
        
        Args:
            data: API 返回的 JSON 数据
            
        Returns:
            str: 刷新时间字符串
        """
        from datetime import datetime
        
        # 尝试从 roundInfo 提取
        if 'roundInfo' in data and data['roundInfo']:
            round_info = data['roundInfo']
            current = round_info.get('current', '')  # 例如："12:00 - 16:00"
            date = round_info.get('date', '')  # 例如："2026-05-15"
            
            if current and date:
                # 提取开始时间
                start_time = current.split(' - ')[0]  # "12:00"
                return f"{date} {start_time}"
        
        # 如果没找到，返回当前时间
        return datetime.now().strftime('%Y-%m-%d %H:%M')


def test_scraper():
    """测试抓取功能"""
    scraper = MerchantScraper()
    result = scraper.fetch_merchant_data()
    
    print("=" * 50)
    print("抓取结果：")
    print(f"刷新时间：{result.get('refresh_time', '未知')}")
    print(f"商品数量：{len(result.get('items', []))}")
    print("\n商品列表：")
    for item in result.get('items', []):
        print(f"  - {item['name']}")
    print("=" * 50)
    
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_scraper()
