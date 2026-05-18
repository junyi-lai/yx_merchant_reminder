"""
定时任务调度模块
负责在指定时间触发商品检测任务
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import logging
from config import config
from scraper import MerchantScraper
from notifier import WechatNotifier
from database import MerchantDatabase


logger = logging.getLogger(__name__)

# 重试配置
RETRY_INTERVAL_MINUTES = 5  # 重试间隔（分钟）
MAX_RETRY_HOURS = 2  # 最大重试时间范围（小时）


class MerchantScheduler:
    """商品检测任务调度器"""
    
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.scraper = MerchantScraper()
        self.notifier = WechatNotifier()
        self.database = MerchantDatabase()
        self.failed_jobs = {}  # 存储失败的任务信息 {job_id: {'check_time': ..., 'retry_count': ...}}
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
                misfire_grace_time=60,  # 如果错过执行时间，60 秒内补执行
                kwargs={
                    'check_hour': hour,
                    'check_minute': minute
                }
            )
            
            logger.info(f"添加定时任务：每天 {hour:02d}:{minute:02d} 检测远行商人")
    
    def _check_merchant(self, check_hour=None, check_minute=None, is_retry=False, retry_count=0):
        """
        执行商品检测任务
        
        Args:
            check_hour: 检测时间（小时），用于重试场景
            check_minute: 检测时间（分钟），用于重试场景
            is_retry: 是否为重试任务
            retry_count: 当前重试次数
        
        流程：
        1. 抓取网页获取商品数据
        2. 判断是否有珍贵道具
        3. 检查是否已推送过
        4. 发送微信通知
        5. 记录推送历史
        """
        now = datetime.now()
        
        # 确定检测时间（用于刷新时间显示）
        if check_hour is not None and check_minute is not None:
            detect_time_str = f"{check_hour:02d}:{check_minute:02d}"
            retry_tag = f"[重试{retry_count}次]" if is_retry else ""
        else:
            detect_time_str = now.strftime('%H:%M')
            retry_tag = ""
        
        logger.info("=" * 50)
        logger.info(f"开始执行远行商人检测任务 {retry_tag}")
        logger.info(f"检测时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")
        
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
            # 如果是原定时任务失败，调度重试
            if not is_retry and check_hour is not None:
                self._schedule_retries(check_hour, check_minute)
        
        logger.info("=" * 50)
    
    def _schedule_retries(self, check_hour, check_minute):
        """
        调度重试任务
        
        Args:
            check_hour: 原定检测时间（小时）
            check_minute: 原定检测时间（分钟）
        
        逻辑：
        - 原时间 + 5分钟后开始重试
        - 每5分钟重试一次
        - 最多重试到原时间 + 2小时
        - 第25次重试（+120分钟）仍失败则发失败通知
        """
        now = datetime.now()
        base_time = now.replace(hour=check_hour, minute=check_minute, second=0, microsecond=0)
        
        # 如果原定时间已过，base_time 应该是今天的那个时间
        if base_time < now:
            # 如果当前时间已经超过了原定时间的2小时窗口，不再调度重试
            if now > base_time + timedelta(hours=MAX_RETRY_HOURS):
                logger.warning(f"原定时间 {check_hour:02d}:{check_minute:02d} 已超过2小时，跳过重试调度")
                self._send_failure_notification(check_hour, check_minute)
                return
        
        job_id = f"retry_{check_hour:02d}{check_minute:02d}"
        
        # 计算下一次重试时间
        next_retry_time = base_time + timedelta(minutes=RETRY_INTERVAL_MINUTES)
        
        # 如果下一次重试时间已经过了，从当前时间开始
        if next_retry_time < now:
            # 计算从现在开始还需要调度几个重试点
            minutes_since_original = int((now - base_time).total_seconds() / 60)
            retry_offset = ((minutes_since_original // RETRY_INTERVAL_MINUTES) + 1) * RETRY_INTERVAL_MINUTES
            next_retry_time = base_time + timedelta(minutes=retry_offset)
        
        # 检查是否超过2小时限制
        deadline = base_time + timedelta(hours=MAX_RETRY_HOURS)
        
        if next_retry_time > deadline:
            # 已达重试上限，发送失败通知
            logger.warning(f"重试次数已达上限（{MAX_RETRY_HOURS}小时），发送失败通知")
            self._send_failure_notification(check_hour, check_minute)
            return
        
        # 调度重试任务
        trigger = DateTrigger(run_date=next_retry_time)
        retry_count = int((next_retry_time - base_time).total_seconds() / 60 / RETRY_INTERVAL_MINUTES)
        
        self.scheduler.add_job(
            func=self._retry_check,
            trigger=trigger,
            id=job_id,
            name=f"远行商人检测重试 - {next_retry_time.strftime('%H:%M')}",
            replace_existing=True,
            misfire_grace_time=300,
            kwargs={
                'check_hour': check_hour,
                'check_minute': check_minute,
                'retry_count': retry_count
            }
        )
        
        logger.info(f"已调度重试任务：{next_retry_time.strftime('%H:%M')} (第{retry_count}次重试)")
        
        # 记录失败任务信息
        if job_id not in self.failed_jobs:
            self.failed_jobs[job_id] = {
                'check_hour': check_hour,
                'check_minute': check_minute,
                'retry_count': retry_count
            }
    
    def _retry_check(self, check_hour, check_minute, retry_count):
        """
        执行重试检测任务
        
        Args:
            check_hour: 原定检测时间（小时）
            check_minute: 原定检测时间（分钟）
            retry_count: 当前重试次数
        """
        logger.info(f"=" * 50)
        logger.info(f"执行远行商人检测重试 [第{retry_count}次]")
        
        try:
            # 1. 抓取商品数据
            merchant_data = self.scraper.fetch_merchant_data()
            items = merchant_data.get('items', [])
            refresh_time = merchant_data.get('refresh_time', '未知')
            
            if not items:
                logger.warning("未获取到商品数据，继续重试")
                # 调度下一次重试
                self._schedule_retries(check_hour, check_minute)
                return
            
            # 2. 判断是否有珍贵道具
            has_precious = self._has_precious_items(items)
            
            # 3. 检查是否已推送过这批货物
            if self.database.is_already_pushed(refresh_time, items):
                logger.info(f"这批货物已推送过（刷新时间：{refresh_time}），跳过")
                # 清除失败记录
                job_id = f"retry_{check_hour:02d}{check_minute:02d}"
                self.failed_jobs.pop(job_id, None)
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
            
            # 6. 清除失败记录
            job_id = f"retry_{check_hour:02d}{check_minute:02d}"
            self.failed_jobs.pop(job_id, None)
            
            # 7. 输出检测结果
            self._log_result(items, has_precious, push_success)
            
        except Exception as e:
            logger.error(f"重试检测任务执行失败：{e}", exc_info=True)
            # 继续调度下一次重试
            self._schedule_retries(check_hour, check_minute)
        
        logger.info(f"=" * 50)
    
    def _send_failure_notification(self, check_hour, check_minute):
        """
        发送失败通知（仅发送给第一个SCKEY）
        
        Args:
            check_hour: 原定检测时间（小时）
            check_minute: 原定检测时间（分钟）
        """
        try:
            title = "获取失败"
            content = f"获取失败"
            # 仅向第一个SCKEY发送
            success = self.notifier.send_notification_to_first_sckey(title, content)
            if success:
                logger.info(f"已发送失败通知至管理员")
            else:
                logger.error(f"发送失败通知失败")
        except Exception as e:
            logger.error(f"发送失败通知异常：{e}")
    
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
