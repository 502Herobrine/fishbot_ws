#!/usr/bin/env python3
"""
时间戳监听工具 - 对比 /scan 和 /odom 话题的时间戳差异
用法: python3 timestamp_monitor.py
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from collections import deque
import statistics

class TimestampMonitor(Node):
    def __init__(self):
        super().__init__('timestamp_monitor')
        
        # 订阅两个话题
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        
        # 存储最近的时间戳
        self.last_scan_time = None
        self.last_odom_time = None
        
        # 时间戳差异记录（最多保存100个）
        self.time_diffs = deque(maxlen=100)
        
        # 计数器
        self.scan_count = 0
        self.odom_count = 0
        
        self.get_logger().info('时间戳监听器已启动')
        self.get_logger().info('等待 /scan 和 /odom 话题...')
        
    def scan_callback(self, msg):
        """处理激光扫描消息"""
        self.scan_count += 1
        scan_stamp = msg.header.stamp
        self.last_scan_time = (scan_stamp.sec, scan_stamp.nanosec)
        
        self._print_diff()
    
    def odom_callback(self, msg):
        """处理里程计消息"""
        self.odom_count += 1
        odom_stamp = msg.header.stamp
        self.last_odom_time = (odom_stamp.sec, odom_stamp.nanosec)
        
        self._print_diff()
    
    def _print_diff(self):
        """计算并打印时间戳差异"""
        if self.last_scan_time is None or self.last_odom_time is None:
            return
        
        # 转换为纳秒进行比较
        scan_ns = self.last_scan_time[0] * 1e9 + self.last_scan_time[1]
        odom_ns = self.last_odom_time[0] * 1e9 + self.last_odom_time[1]
        
        # 计算差异（毫秒）
        diff_ms = (scan_ns - odom_ns) / 1e6
        self.time_diffs.append(diff_ms)
        
        # 每10条消息打印一次统计
        total_msgs = self.scan_count + self.odom_count
        if total_msgs % 10 == 0:
            self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        if not self.time_diffs:
            return
        
        diffs = list(self.time_diffs)
        avg_diff = statistics.mean(diffs)
        max_diff = max(diffs)
        min_diff = min(diffs)
        
        if len(diffs) > 1:
            std_dev = statistics.stdev(diffs)
        else:
            std_dev = 0
        
        self.get_logger().info(
            f'时间戳统计 (最近{len(diffs)}条): '
            f'平均差异={avg_diff:.2f}ms, '
            f'范围=[{min_diff:.2f}, {max_diff:.2f}]ms, '
            f'标准差={std_dev:.2f}ms | '
            f'扫描数={self.scan_count}, 里程计数={self.odom_count}')
        
        # 判断同步状态
        if abs(avg_diff) < 50:  # 50ms 以内认为同步良好
            self.get_logger().info('✅ 时间戳同步状态良好')
        elif abs(avg_diff) < 200:
            self.get_logger().warn('⚠️  时间戳可能存在延迟')
        else:
            self.get_logger().error('❌ 时间戳差异过大，需要检查同步机制')


def main():
    rclpy.init()
    monitor = TimestampMonitor()
    
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        monitor.get_logger().info('监听器已停止')
    finally:
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
