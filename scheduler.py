"""
定时任务调度模块
负责在指定时间触发商品检测任务
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from config import config
from scraper import MerchantScraper
from notifier import WechatNotifier
from database import MerchantDatabase


logger = logging.getLogger(__name__)


class MerchantScheduler:
    """商品检测任务调度器"""
    
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.scraper = MerchantScraper()
        self.notifier = WechatNotifier()
        self.database = MerchantDatabase()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """设置定时任务"""
        # 为每个检测时间添加定时任务
        for check_time in config.CHECK_TIMES:
            hour = check_time["hour"]
            minute = check_time["minute"]
            
            # 使用 Cron 触发器，每天在指定时间执行
            trigger = CronTrigger(hour=hour, minute=minute, second=0)
            
            self.scheduler.add_job(
                func=self._check_merchant,
                trigger=trigger,
                id=f"merchant_check_{hour:02d}{minute:02d}",
                name=f"远行商人检测 - {hour:02d}:{minute:02d}",
                replace_existing=True,
                misfire_grace_time=60  # 如果错过执行时间，60 秒内补执行
            )
            
            logger.info(f"添加定时任务：每天 {hour:02d}:{minute:02d} 检测远行商人")
    
    def _check_merchant(self):
        """
        执行商品检测任务
        
        流程：
        1. 抓取网页获取商品数据
        2. 判断是否有珍贵道具
        3. 检查是否已推送过
        4. 发送微信通知
        5. 记录推送历史
        """
        from datetime import datetime
        
        logger.info("=" * 50)
        logger.info("开始执行远行商人检测任务")
        logger.info(f"检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 1. 抓取商品数据
            merchant_data = self.scraper.fetch_merchant_data()
            items = merchant_data.get('items', [])
            refresh_time = merchant_data.get('refresh_time', '未知')
            
            if not items:
                logger.warning("未获取到商品数据，跳过本次检测")
                return
            
            # 2. 判断是否有珍贵道具
            has_precious = self._has_precious_items(items)
            
            # 3. 检查是否已推送过这批货物
            if self.database.is_already_pushed(refresh_time, items):
                logger.info(f"这批货物已推送过（刷新时间：{refresh_time}），跳过")
                return
            
            # 4. 发送微信通知
            push_success = self.notifier.send_notification(items, refresh_time, has_precious)
            
            # 5. 记录推送历史
            self.database.add_push_record(
                refresh_time=refresh_time,
                items=items,
                has_precious=has_precious,
                push_success=push_success
            )
            
            # 6. 输出检测结果
            self._log_result(items, has_precious, push_success)
            
        except Exception as e:
            logger.error(f"检测任务执行失败：{e}", exc_info=True)
        
        logger.info("=" * 50)
    
    def _has_precious_items(self, items):
        """
        判断是否有珍贵道具
        
        Args:
            items: 商品列表
            
        Returns:
            bool: 是否有珍贵道具
        """
        for item in items:
            item_name = item['name']
            for precious in config.PRECIOUS_ITEMS:
                if precious in item_name:
                    return True
        return False
    
    def _log_result(self, items, has_precious, push_success):
        """
        输出检测结果日志
        
        Args:
            items: 商品列表
            has_precious: 是否有珍贵道具
            push_success: 推送是否成功
        """
        logger.info(f"商品数量：{len(items)}")
        logger.info(f"珍贵道具：{'是' if has_precious else '否'}")
        logger.info(f"推送结果：{'成功' if push_success else '失败'}")
        
        logger.info("商品列表：")
        for item in items:
            precious_mark = "🔥" if any(p in item['name'] for p in config.PRECIOUS_ITEMS) else "  "
            logger.info(f"  {precious_mark} {item['name']}")
    
    def start(self):
        """启动调度器"""
        logger.info("启动远行商人检测调度器...")
        logger.info("程序将 24 小时运行，在以下时间检测：")
        for check_time in config.CHECK_TIMES:
            logger.info(f"  - {check_time['hour']:02d}:{check_time['minute']:02d}")
        
        # 启动时立即执行一次检测
        logger.info("")
        logger.info("=" * 60)
        logger.info("程序启动，立即执行首次检测...")
        logger.info("=" * 60)
        self._check_merchant()
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("调度器已停止")
    
    def add_manual_check(self):
        """
        添加手动检测功能（用于测试）
        
        Returns:
            dict: 检测结果
        """
        logger.info("执行手动检测...")
        
        try:
            # 抓取商品数据
            merchant_data = self.scraper.fetch_merchant_data()
            items = merchant_data.get('items', [])
            refresh_time = merchant_data.get('refresh_time', '未知')
            
            if not items:
                return {
                    'success': False,
                    'message': '未获取到商品数据'
                }
            
            # 判断是否有珍贵道具
            has_precious = self._has_precious_items(items)
            
            # 发送通知
            push_success = self.notifier.send_notification(items, refresh_time, has_precious)
            
            # 记录推送历史
            self.database.add_push_record(
                refresh_time=refresh_time,
                items=items,
                has_precious=has_precious,
                push_success=push_success
            )
            
            return {
                'success': True,
                'items': items,
                'refresh_time': refresh_time,
                'has_precious': has_precious,
                'push_success': push_success
            }
            
        except Exception as e:
            logger.error(f"手动检测失败：{e}", exc_info=True)
            return {
                'success': False,
                'message': str(e)
            }


def test_scheduler():
    """测试调度器"""
    scheduler = MerchantScheduler()
    
    print("=" * 50)
    print("测试手动检测功能")
    print("=" * 50)
    
    result = scheduler.add_manual_check()
    
    if result['success']:
        print(f"✅ 检测成功")
        print(f"刷新时间：{result['refresh_time']}")
        print(f"商品数量：{len(result['items'])}")
        print(f"珍贵道具：{'是' if result['has_precious'] else '否'}")
        print(f"推送结果：{'成功' if result['push_success'] else '失败'}")
    else:
        print(f"❌ 检测失败：{result.get('message')}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_scheduler()
