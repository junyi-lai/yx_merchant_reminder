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

    # 名称简化映射
    NAME_REPLACEMENTS = {
        '炫彩精灵蛋': '炫彩蛋',
        '神奇的蛋': '神奇蛋',
        '黑晶琉璃': '黑矿',
        '黄石榴石': '黄矿',
        '蓝晶碧玺': '蓝矿',
        '紫莲刚玉': '紫矿',
        '能力钥匙': '银钥',
        '残缺魔镜': '银镜',
        '适格钥匙': '金钥',
        '祝福项坠': '项坠',
    }

    def __init__(self):
        self.sckeys = config.SCKEYS
        self.push_url_template = config.PUSH_URL

    def _simplify_name(self, name):
        """
        简化道具名称

        Args:
            name: 原始道具名称

        Returns:
            str: 简化后的名称
        """
        # 1. 精确匹配替换
        if name in self.NAME_REPLACEMENTS:
            return self.NAME_REPLACEMENTS[name]

        # 2. xxx血脉秘药 → xxx药
        if '血脉秘药' in name:
            return name.replace('血脉秘药', '药')

        # 3. xxx粉尘 → xxx粉
        if name.endswith('粉尘'):
            return name[:-2] + '粉'

        return name
    
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
        simple_names = [self._simplify_name(item['name']) for item in items]
        full_names = [item['name'] for item in items]
        title = "、".join(simple_names)
        content = "、".join(full_names)
        
        # 如果有珍贵道具，在标题前添加【!】标签
        if has_precious:
            title = "【!】" + title
        
        return self._push_to_wechat(title, content)
    
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
            {'name': '冰系粉尘'},
            {'name': '黑晶琉璃'},
            {'name': '虫系血脉秘药'},
            {'name': '光合球'},
            {'name': '炫彩精灵蛋'},
        ]
        
        success = self.send_notification(
            items=test_items,
            refresh_time="2026-05-15 08:00",
            has_precious=True
        )
        
        if success:
            print("[OK] 推送测试成功！")
        else:
            print("❌ 推送测试失败，请检查 SCKEY 是否正确")
        
        return success
    
    def send_notification_to_first_sckey(self, title, content):
        """
        仅向第一个 SCKEY 发送通知（用于失败通知）
        
        Args:
            title: 消息标题
            content: 消息内容
            
        Returns:
            bool: 推送是否成功
        """
        if not self.sckeys:
            logger.error("没有配置任何 SCKEY")
            return False
        
        first_sckey = self.sckeys[0]
        logger.info(f"正在向管理员发送通知：{title}")
        
        success = self._push_single(first_sckey, title, content)
        if success:
            logger.info("管理员通知发送成功")
        else:
            logger.error("管理员通知发送失败")
        
        return success


def test_notifier():
    """测试推送功能"""
    notifier = WechatNotifier()
    notifier.test_push()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_notifier()
