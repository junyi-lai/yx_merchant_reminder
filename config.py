"""
配置文件模块
负责加载和管理所有配置项
"""
import os
import configparser
from datetime import datetime


class Config:
    """配置管理类"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """从 config.ini 加载配置"""
        config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        config.read(config_path, encoding='utf-8')
        
        # 网站配置
        self.MERCHANT_URL = config.get('website', 'url', fallback='https://roco.dayun.cool/?mode=obs1')
        self.REQUEST_TIMEOUT = config.getint('website', 'timeout', fallback=10)
        self.MAX_RETRIES = config.getint('website', 'max_retries', fallback=3)
        
        # 检测时间配置（刷新后 2 分钟检测）
        # 远行商人刷新时间：8:00, 12:00, 16:00, 20:00
        self.CHECK_TIMES = [
            {"hour": 8, "minute": 2},
            {"hour": 12, "minute": 2},
            {"hour": 16, "minute": 2},
            {"hour": 20, "minute": 2},
        ]
        
        # 珍贵道具列表
        self.PRECIOUS_ITEMS = [
            "国王球",
            "棱镜球",
            "炫彩精灵蛋",
            "祝福项坠",
            "血脉秘药",  # 包含各种血脉秘药（恶系血脉秘药、水系血脉秘药等）
        ]
        
        # Server 酱配置
        sckey_raw = config.get('serverchan', 'sckey', fallback='')
        # 支持多个 SendKey（逗号分隔）
        self.SCKEYS = [s.strip() for s in sckey_raw.split(',') if s.strip()]
        self.SCKEY = self.SCKEYS[0] if self.SCKEYS else ''
        self.PUSH_URL = "https://sctapi.ftqq.com/{skey}.send"
        
        # 日志配置
        self.LOG_LEVEL = config.get('log', 'level', fallback='INFO')
        self.LOG_ENCODING = config.get('log', 'encoding', fallback='gbk')
        # 使用原始字符串避免插值问题
        try:
            self.LOG_FORMAT = config.get('log', 'format', raw=True, 
                fallback='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        except Exception:
            self.LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.LOG_FILE = os.path.join(
            os.path.dirname(__file__), 
            'logs', 
            'reminder.log'
        )
        
        # 数据库配置
        self.DB_PATH = os.path.join(
            os.path.dirname(__file__), 
            'data', 
            'merchant.db'
        )
        
        # 请求头配置
        self.HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
    
    def validate(self):
        """验证配置是否有效"""
        if not self.SCKEY:
            raise ValueError("Server 酱 SCKEY 未配置，请在 config.ini 中填写")
        return True
    
    def get_check_time_str(self):
        """获取当前检测时间的描述"""
        now = datetime.now()
        for check_time in self.CHECK_TIMES:
            if now.hour == check_time["hour"] and now.minute == check_time["minute"]:
                return f"{check_time['hour']:02d}:{check_time['minute']:02d}"
        return "未知时间"


# 全局配置实例
config = Config()
