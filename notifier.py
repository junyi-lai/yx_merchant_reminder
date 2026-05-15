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
        self.sckeys = config.SCKEYS
        self.push_url_template = config.PUSH_URL
    
    def _push_single(self, sckey, title, content):
        """向单个账户推送消息"""
        try:
            push_url = self.push_url_template.format(skey=sckey)
            params = {
                'title': title,
                'desp': content
            }
            
            response = requests.post(
                push_url,
                data=params,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 0 or result.get('errno') == 0:
                return True
            else:
                logger.error(f"SCKEY {sckey[:8]}... 推送失败：{result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"SCKEY {sckey[:8]}... 推送异常：{e}")
            return False
    
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
        # 标题直接使用商品列表内容，方便在微信列表中查看
        if has_precious:
            title = self._format_precious_message(items, refresh_time)
            content = title
        else:
            title = self._format_normal_message(items, refresh_time)
            content = title
        
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
        
        # 构建消息内容：只在最前面加【珍贵】标记
        item_list = [item['name'] for item in items]
        content = "【珍贵】" + "、".join(item_list)
        
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
        # 构建消息内容：直接罗列商品名
        item_list = [item['name'] for item in items]
        content = "、".join(item_list)
        
        return content
    
    def _push_to_wechat(self, title, content):
        """
        调用 Server 酱 API 向所有账户推送消息
        
        Args:
            title: 消息标题
            content: 消息内容
            
        Returns:
            bool: 推送是否成功（至少一个成功即为成功）
        """
        logger.info(f"正在发送微信推送：{title}")
        
        if not self.sckeys:
            logger.error("没有配置任何 SCKEY")
            return False
        
        # 向所有账户发送
        success_count = 0
        for sckey in self.sckeys:
            if self._push_single(sckey, title, content):
                success_count += 1
        
        if success_count > 0:
            logger.info(f"微信推送成功，已发送至 {success_count}/{len(self.sckeys)} 个账户")
            return True
        else:
            logger.error("微信推送失败，所有账户均未成功")
            return False
    
    def test_push(self):
        """
        测试推送功能
        
        Returns:
            bool: 测试是否成功
        """
        test_items = [
            {'name': '国王球', 'quantity': '5'},
            {'name': '高级药水', 'quantity': '10'},
            {'name': '血脉秘药', 'quantity': '3'},
            {'name': '面包', 'quantity': '20'}
        ]
        
        success = self.send_notification(
            items=test_items,
            refresh_time="2026-05-15 08:00",
            has_precious=True
        )
        
        if success:
            print("✅ 推送测试成功！")
            print("微信消息内容：[珍贵] 国王球、高级药水、[珍贵] 血脉秘药、面包")
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
