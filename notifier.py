"""
微信推送模块
负责通过 Server 酱发送微信消息
"""
import requests
import logging
from config import config


logger = logging.getLogger(__name__)


class WechatNotifier:
    """微信推送通知类"""
    
    def __init__(self):
        self.sckey = config.SCKEY
        self.push_url = config.PUSH_URL.format(skey=self.sckey)
    
    def send_notification(self, items, refresh_time, has_precious):
        """
        发送微信通知
        
        Args:
            items: 商品列表 [{'name': '商品名', 'quantity': '数量'}, ...]
            refresh_time: 刷新时间字符串
            has_precious: 是否有珍贵道具 (bool)
            
        Returns:
            bool: 推送是否成功
        """
        if has_precious:
            # 有珍贵道具：使用紧急提醒标题
            title = "🚨【珍贵道具提醒】洛克王国远行商人刷新"
            content = self._format_precious_message(items, refresh_time)
        else:
            # 无珍贵道具：使用普通标题
            title = "📋【日常刷新】洛克王国远行商人刷新"
            content = self._format_normal_message(items, refresh_time)
        
        return self._push_to_wechat(title, content)
    
    def _format_precious_message(self, items, refresh_time):
        """
        格式化珍贵道具消息
        
        Args:
            items: 商品列表
            refresh_time: 刷新时间
            
        Returns:
            str: 格式化的消息内容
        """
        from config import config
        
        # 筛选珍贵道具
        precious_items = [
            item for item in items 
            if any(precious in item['name'] for precious in config.PRECIOUS_ITEMS)
        ]
        
        # 构建消息内容
        content = f"刷新时间：{refresh_time}\n\n"
        content += "🔥 珍贵道具：\n"
        
        for item in precious_items:
            content += f"  ✅ {item['name']} x {item.get('quantity', '1')}\n"
        
        content += "\n📦 全部商品：\n"
        item_list = ", ".join([f"{item['name']} x {item.get('quantity', '1')}" for item in items])
        content += f"  {item_list}\n\n"
        content += "请及时查看！"
        
        return content
    
    def _format_normal_message(self, items, refresh_time):
        """
        格式化普通消息
        
        Args:
            items: 商品列表
            refresh_time: 刷新时间
            
        Returns:
            str: 格式化的消息内容
        """
        content = f"刷新时间：{refresh_time}\n\n"
        content += "📦 全部商品：\n"
        
        item_list = ", ".join([f"{item['name']} x {item.get('quantity', '1')}" for item in items])
        content += f"  {item_list}\n\n"
        content += "暂无珍贵道具，可跳过查看"
        
        return content
    
    def _push_to_wechat(self, title, content):
        """
        调用 Server 酱 API 推送消息
        
        Args:
            title: 消息标题
            content: 消息内容
            
        Returns:
            bool: 推送是否成功
        """
        try:
            logger.info(f"正在发送微信推送：{title}")
            
            params = {
                'title': title,
                'desp': content
            }
            
            response = requests.post(
                self.push_url,
                data=params,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') == 0 or result.get('errno') == 0:
                logger.info("微信推送成功")
                return True
            else:
                logger.error(f"微信推送失败：{result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"微信推送异常：{e}")
            return False
    
    def test_push(self):
        """
        测试推送功能
        
        Returns:
            bool: 测试是否成功
        """
        test_items = [
            {'name': '国王球', 'quantity': '5'},
            {'name': '高级药水', 'quantity': '10'}
        ]
        
        success = self.send_notification(
            items=test_items,
            refresh_time="2026-05-15 08:00",
            has_precious=True
        )
        
        if success:
            print("✅ 推送测试成功！")
        else:
            print("❌ 推送测试失败，请检查 SCKEY 是否正确")
        
        return success


def test_notifier():
    """测试推送功能"""
    notifier = WechatNotifier()
    notifier.test_push()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_notifier()
