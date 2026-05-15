"""
数据库模块
负责记录推送历史，避免重复推送
"""
import sqlite3
import logging
from datetime import datetime
from config import config


logger = logging.getLogger(__name__)


class MerchantDatabase:
    """商品推送记录数据库类"""
    
    def __init__(self):
        self.db_path = config.DB_PATH
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建推送历史记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS push_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                refresh_time TEXT NOT NULL,
                items_text TEXT NOT NULL,
                has_precious INTEGER NOT NULL,
                push_time TEXT NOT NULL,
                push_success INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引，加速查询
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_refresh_time 
            ON push_history(refresh_time)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成：{self.db_path}")
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def is_already_pushed(self, refresh_time, items):
        """
        检查是否已经推送过这批货物
        
        Args:
            refresh_time: 刷新时间
            items: 商品列表
            
        Returns:
            bool: 是否已推送
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 将商品列表转换为字符串用于比较
        items_text = self._items_to_text(items)
        
        # 查询是否已存在相同刷新时间和商品的记录
        cursor.execute('''
            SELECT COUNT(*) as count 
            FROM push_history 
            WHERE refresh_time = ? AND items_text = ?
        ''', (refresh_time, items_text))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] > 0
    
    def add_push_record(self, refresh_time, items, has_precious, push_success):
        """
        添加推送记录
        
        Args:
            refresh_time: 刷新时间
            items: 商品列表
            has_precious: 是否有珍贵道具
            push_success: 推送是否成功
            
        Returns:
            int: 新记录的 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        items_text = self._items_to_text(items)
        push_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO push_history 
            (refresh_time, items_text, has_precious, push_time, push_success)
            VALUES (?, ?, ?, ?, ?)
        ''', (refresh_time, items_text, 1 if has_precious else 0, push_time, 1 if push_success else 0))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"添加推送记录：ID={record_id}, 刷新时间={refresh_time}, 珍贵道具={has_precious}")
        return record_id
    
    def _items_to_text(self, items):
        """
        将商品列表转换为排序后的文本字符串
        
        Args:
            items: 商品列表
            
        Returns:
            str: 排序后的商品文本
        """
        # 排序后转换，确保相同商品生成相同的文本
        sorted_items = sorted(items, key=lambda x: x['name'])
        return "|".join([f"{item['name']}x{item.get('quantity', '1')}" for item in sorted_items])
    
    def get_recent_pushes(self, days=7):
        """
        获取最近 N 天的推送记录
        
        Args:
            days: 天数
            
        Returns:
            list: 推送记录列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT * FROM push_history 
            WHERE created_at >= ?
            ORDER BY created_at DESC
        ''', (start_date,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_statistics(self, days=30):
        """
        获取统计数据
        
        Args:
            days: 统计天数
            
        Returns:
            dict: 统计数据
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 总推送次数
        cursor.execute('''
            SELECT COUNT(*) as total FROM push_history 
            WHERE created_at >= ?
        ''', (start_date,))
        total = cursor.fetchone()['total']
        
        # 珍贵道具推送次数
        cursor.execute('''
            SELECT COUNT(*) as precious_count FROM push_history 
            WHERE created_at >= ? AND has_precious = 1
        ''', (start_date,))
        precious_count = cursor.fetchone()['precious_count']
        
        # 推送成功率
        cursor.execute('''
            SELECT COUNT(*) as success_count FROM push_history 
            WHERE created_at >= ? AND push_success = 1
        ''', (start_date,))
        success_count = cursor.fetchone()['success_count']
        
        conn.close()
        
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'precious_count': precious_count,
            'success_count': success_count,
            'success_rate': success_rate
        }
    
    def clear_old_records(self, days=3):
        """
        清理 N 天前的旧记录
        
        Args:
            days: 保留的天数（默认 3 天）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            DELETE FROM push_history 
            WHERE created_at < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"清理了 {deleted_count} 条旧记录")
        return deleted_count


def test_database():
    """测试数据库功能"""
    db = MerchantDatabase()
    
    # 测试添加记录
    test_items = [
        {'name': '国王球', 'quantity': '5'},
        {'name': '棱镜球', 'quantity': '3'}
    ]
    
    # 检查是否已推送
    is_pushed = db.is_already_pushed("2026-05-15 08:00", test_items)
    print(f"是否已推送：{is_pushed}")
    
    # 添加新记录
    record_id = db.add_push_record(
        refresh_time="2026-05-15 08:00",
        items=test_items,
        has_precious=True,
        push_success=True
    )
    print(f"添加记录 ID: {record_id}")
    
    # 获取统计数据
    stats = db.get_statistics(days=30)
    print(f"统计数据：{stats}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_database()
