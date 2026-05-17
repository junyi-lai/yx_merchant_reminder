"""
洛克王国世界远行商人提醒系统 - 主程序入口

功能：
1. 定时检测远行商人商品刷新
2. 识别珍贵道具并推送微信通知
3. 记录推送历史，避免重复推送

运行方式：
1. 正常启动：python main.py
2. 手动检测：python main.py --manual
3. 测试推送：python main.py --test-push
"""
import sys
import logging
from logging.handlers import RotatingFileHandler
import os
from config import config
from scheduler import MerchantScheduler


def setup_logging():
    """配置日志系统"""
    # 确保日志目录存在
    log_dir = os.path.dirname(config.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # 日志格式
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（轮转，最大 5MB，保留 3 个文件，约 3 天日志）
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding=config.LOG_ENCODING
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logging.info("日志系统初始化完成")


def validate_config():
    """验证配置"""
    try:
        config.validate()
        logging.info("配置验证通过")
        return True
    except ValueError as e:
        logging.error(f"配置验证失败：{e}")
        return False


def run_manual_check():
    """运行手动检测"""
    logging.info("=" * 60)
    logging.info("洛克王国远行商人提醒系统 - 手动检测模式")
    logging.info("=" * 60)
    
    scheduler = MerchantScheduler()
    result = scheduler.add_manual_check()
    
    if result['success']:
        logging.info("=" * 60)
        logging.info("✅ 检测完成")
        logging.info(f"刷新时间：{result['refresh_time']}")
        logging.info(f"商品数量：{len(result['items'])}")
        logging.info(f"珍贵道具：{'是' if result['has_precious'] else '否'}")
        logging.info(f"推送结果：{'成功' if result['push_success'] else '失败'}")
        logging.info("=" * 60)
        
        # 打印商品列表
        logging.info("商品列表：")
        for item in result['items']:
            precious_mark = "🔥" if any(p in item['name'] for p in config.PRECIOUS_ITEMS) else "  "
            logging.info(f"  {precious_mark} {item['name']}")
        logging.info("=" * 60)
        
        return 0
    else:
        logging.error(f"❌ 检测失败：{result.get('message')}")
        return 1


def run_test_push():
    """运行推送测试"""
    logging.info("=" * 60)
    logging.info("洛克王国远行商人提醒系统 - 推送测试模式")
    logging.info("=" * 60)
    
    from notifier import WechatNotifier
    
    notifier = WechatNotifier()
    success = notifier.test_push()
    
    return 0 if success else 1


def run_scheduler():
    """运行定时任务调度器"""
    logging.info("=" * 60)
    logging.info("洛克王国远行商人提醒系统 - 自动运行模式")
    logging.info("=" * 60)
    
    scheduler = MerchantScheduler()
    scheduler.start()
    
    return 0


def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("  洛克王国世界远行商人提醒系统")
    print("  版本：1.0.0")
    print("  功能：定时检测 + 微信推送")
    print("=" * 60)
    print()


def main():
    """主函数"""
    # 打印欢迎横幅
    print_banner()
    
    # 配置日志
    setup_logging()
    
    # 验证配置
    if not validate_config():
        logging.error("配置验证失败，程序退出")
        return 1
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--manual':
            # 手动检测模式
            return run_manual_check()
        elif sys.argv[1] == '--test-push':
            # 推送测试模式
            return run_test_push()
        elif sys.argv[1] == '--help':
            # 帮助信息
            print("用法：python main.py [选项]")
            print()
            print("选项:")
            print("  --manual      手动检测一次")
            print("  --test-push   测试微信推送功能")
            print("  --help        显示帮助信息")
            print("  (无参数)      启动定时任务调度器")
            return 0
    
    # 默认：启动定时任务调度器
    return run_scheduler()


if __name__ == '__main__':
    sys.exit(main())
