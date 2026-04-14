# ESP32 主控板时间戳机制说明

## 快速总结

### 关键代码位置
- **ESP32 源代码**：`~/Documents/PlatformIO/Projects/motor_control/src/main.cpp`
- **时间戳生成**：第 50-77 行的 `callback_publisher()` 函数
- **时间同步**：第 107-110 行的时间同步代码

### 时间戳生成流程

```
ESP32 上电 
  ↓
连接 WiFi（SSID: CMCC-KDdy, 密码: 3116Herobrine）
  ↓
连接到 micro_ros_agent（192.168.10.5:8888）
  ↓
执行时间同步（rmw_uros_sync_session）
  ↓
启动 50ms 定时器
  ↓
每次定时器触发：
  1. 获取同步后的系统时间 → rmw_uros_epoch_millis()
  2. 构建 Odometry 消息
  3. 设置 header.stamp
  4. 发布到 /odom 话题
```

## 核心代码解析

### 时间戳获取
```cpp
// main.cpp 第 54 行
int64_t stamp = rmw_uros_epoch_millis();  // 获取微ROS同步的纪元时间（毫秒）

// main.cpp 第 56-58 行
odom_msg.header.stamp.sec = static_cast<int32_t>(stamp / 1000);
odom_msg.header.stamp.nanosec = static_cast<uint32_t>((stamp % 1000) * 1e6);
```

### 时间同步过程
```cpp
// main.cpp 第 107-110 行
while (!rmw_uros_epoch_synchronized()) {  // 等待同步完成
    rmw_uros_sync_session(1000);         // 尝试与主机同步（1000ms 超时）
    delay(10);
}
```

## WiFi 配置

编译参数：
- SSID：`CMCC-KDdy`
- 密码：`3116Herobrine`
- 主机 IP：`192.168.10.5`
- UDP 端口：`8888`

## 运动学数据

里程计数据来自编码器反馈：
- 编码器 0：GPIO 32, 33（左轮）
- 编码器 1：GPIO 26, 25（右轮）
- 每脉冲距离：`0.1051566` mm
- 轮子间距：`175.0` mm

## 时间同步的架构

```
ESP32 (micro-ROS 客户端)
    ↓ WiFi UDP 8888
    ↓
主机 micro_ros_agent (DDS 代理)
    ↓ (提供主机系统时间)
    ↓
rmw_uros_epoch_millis() 返回同步时间
    ↓
/odom 话题发布

同步质量：
- 首次同步：启动时必须等待 rmw_uros_epoch_synchronized() 返回 true
- 精度：±几到几十毫秒（取决于 WiFi 状况）
- 长期稳定性：可能需要周期性重新同步
```

## 验证时间戳同步

运行时间戳监听工具：
```bash
cd ~/SRTP/fishbot_ws
source install/setup.bash
python3 src/fishbot_bringup/scripts/timestamp_monitor.py
```

预期输出：
```
时间戳统计 (最近10条): 平均差异=-5.32ms, 范围=[-50.12, 20.45]ms, 标准差=25.31ms
✅ 时间戳同步状态良好
```

## 潜在问题排查

### 问题 1：时间戳差异很大（>200ms）
**原因**：可能是 WiFi 连接不稳定或时间同步失败

**解决方案**：
1. 检查 WiFi 信号强度
2. 在 ESP32 代码中验证同步状态：
   ```cpp
   bool is_synced = rmw_uros_epoch_synchronized();
   Serial.printf("Time synced: %s\n", is_synced ? "YES" : "NO");
   ```

### 问题 2：ESP32 无法连接到主机
**原因**：IP 地址或端口配置错误

**解决方案**：
1. 检查主机 IP：`hostname -I`
2. 检查micro_ros_agent 是否在运行：`ros2 node list`
3. 更新 main.cpp 中的 IP 地址

### 问题 3：`/odom` 话题不出现
**原因**：ESP32 未成功完成时间同步或连接失败

**解决方案**：
1. 查看 ESP32 串口输出（用 PlatformIO Serial Monitor）
2. 确保 micro_ros_agent 正在运行
3. 检查 WiFi 密码是否正确

## 相关文件

| 文件 | 位置 | 用途 |
|------|------|------|
| main.cpp | ~/Documents/PlatformIO/.../src/ | ESP32 主程序 |
| Kinematics.cpp | ~/Documents/PlatformIO/.../lib/Kinematics/ | 运动学计算 |
| micro_ros_platformio | 库文件 | micro-ROS 框架 |
| odom2tf.cpp | ~/fishbot_ws/src/fishbot_bringup/src/ | ROS2 订阅端 |

## 总结

✅ **ESP32 /odom 话题的时间戳来源**：
- 初始数据：ESP32 本地时间
- 最终来源：通过 micro-ROS WiFi 同步后的**主机系统时间**
- 同步方式：micro_ros_platformio 库自动处理
- 发布频率：50ms（可配置）

这确保了 `/odom` 和 `/scan` 两个话题的时间戳应该是同步的，都基于主机的系统时钟。
