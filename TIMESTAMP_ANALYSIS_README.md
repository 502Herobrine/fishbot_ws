# Fishbot 时间戳分析 - 完整指南

本目录包含对 Fishbot 系统中 `/scan` 和 `/odom` 话题时间戳来源的详细分析。

## 📄 文档索引

### 1. **总体分析** 
📌 [`timestamp_analysis.md`](timestamp_analysis.md)
- 两个话题的时间戳来源对比
- 时间戳生成的详细代码分析
- 时间同步机制说明
- 诊断和改进方案

**快速结论**：
```
/scan  → 直接采用主机系统时间 (CLOCK_REALTIME)
/odom  → 通过 micro-ROS WiFi 同步的主机系统时间
两者理论上应该同步 ✅
```

### 2. **ESP32 主控板指南**
📌 [`ESP32_TIMESTAMP_GUIDE.md`](ESP32_TIMESTAMP_GUIDE.md)
- ESP32 代码的详细解析
- 时间戳生成流程图
- WiFi 配置参数
- 问题排查指南

**核心代码**：
```cpp
// ESP32 在 callback_publisher() 中
int64_t stamp = rmw_uros_epoch_millis();  // 🔑 关键！
odom_msg.header.stamp.sec = stamp / 1000;
odom_msg.header.stamp.nanosec = (stamp % 1000) * 1e6;
```

### 3. **时间戳监听工具**
🔧 [`src/fishbot_bringup/scripts/timestamp_monitor.py`](src/fishbot_bringup/scripts/timestamp_monitor.py)

实时监控和对比两个话题的时间戳：

```bash
# 使用方法
cd ~/SRTP/fishbot_ws
source install/setup.bash
python3 src/fishbot_bringup/scripts/timestamp_monitor.py

# 预期输出
时间戳统计 (最近100条): 平均差异=-5.32ms, 范围=[-50.12, 20.45]ms
✅ 时间戳同步状态良好
```

## 🔍 关键发现

### 时间戳来源链路

```
主机系统时间
    ↓
    ├─→ [/scan] ydlidar_node → clock_gettime(CLOCK_REALTIME)
    │
    └─→ [/odom] micro_ros_agent
            ↑
        micro_ros_platformio (ESP32)
            ↑
        rmw_uros_epoch_millis()  ← 与主机同步
```

### 时间同步机制

| 步骤 | 组件 | 函数 | 说明 |
|------|------|------|------|
| 1 | ESP32 | WiFi 连接 | 连接到网络 |
| 2 | ESP32 | `rmw_uros_sync_session()` | 请求主机时间 |
| 3 | 主机 | `micro_ros_agent` | 响应系统时间 |
| 4 | ESP32 | `rmw_uros_epoch_millis()` | 返回同步时间 |
| 5 | ESP32 | 发布 `/odom` | 使用同步时间戳 |

## 🛠️ 快速开始

### 验证时间戳同步

1. **查看两个话题的实时时间戳**：
   ```bash
   # 终端 1：查看雷达时间戳
   source install/setup.bash && ros2 topic echo /scan --field header.stamp | head -5
   
   # 终端 2：查看里程计时间戳
   source install/setup.bash && ros2 topic echo /odom --field header.stamp | head -5
   ```

2. **运行自动对比工具**：
   ```bash
   python3 src/fishbot_bringup/scripts/timestamp_monitor.py
   ```

3. **查看 ESP32 连接状态**：
   ```bash
   source install/setup.bash
   ros2 node list  # 应该看到 /fishbot_motion_control
   ros2 topic list # 应该看到 /odom 话题
   ```

## 📍 源代码位置

### ROS 2 部分
```
~/SRTP/fishbot_ws/
├── src/ydlidar_ros2/
│   ├── src/ydlidar_node.cpp        ← /scan 发布者
│   └── sdk/core/base/timer.cpp     ← 时间戳获取
└── src/fishbot_bringup/
    └── src/odom2tf.cpp              ← /odom 订阅者
```

### ESP32 部分
```
~/Documents/PlatformIO/Projects/motor_control/
├── src/main.cpp                     ← /odom 发布者 (ESP32)
│   ├── callback_publisher()         ← 时间戳设置
│   ├── twist_callback()             ← 速度控制
│   └── micro_ros_task()             ← 初始化和时间同步
├── lib/Kinematics/
│   └── Kinematics.cpp              ← 运动学计算
└── platformio.ini                   ← WiFi 配置
```

## ✅ 检查清单

- [ ] 两份分析文档已阅读（`timestamp_analysis.md` 和 `ESP32_TIMESTAMP_GUIDE.md`）
- [ ] 了解 `rmw_uros_epoch_millis()` 的作用
- [ ] 知道 WiFi 配置 (SSID, 密码, IP, 端口)
- [ ] 能够查看 ESP32 串口输出
- [ ] 运行过 `timestamp_monitor.py` 工具
- [ ] 理解时间同步流程

## 🚨 常见问题

### Q: `/odom` 时间戳与 `/scan` 差距很大？
A: 检查 WiFi 连接和时间同步状态。运行 `timestamp_monitor.py` 诊断。

### Q: 如何修改时间戳同步周期？
A: 修改 ESP32 `platformio.ini` 中的同步参数或在代码中调用 `rmw_uros_sync_session()` 的频率。

### Q: ESP32 连接失败怎么办？
A: 
1. 检查 IP: `hostname -I`
2. 更新 ESP32 代码中的 IP 地址
3. 确保主机 WiFi 网卡已启动
4. 验证 micro_ros_agent 进程在运行

### Q: 如何离线测试时间戳？
A: 修改 ESP32 代码，使用 `millis()` 替代 `rmw_uros_epoch_millis()` 进行本地时间测试。

## 📚 参考资源

- [micro-ROS 官方文档](https://micro-ros.github.io/)
- [ROS 2 时间戳机制](https://docs.ros.org/en/humble/Concepts/About-Time.html)
- [micro_ros_platformio 库](https://github.com/micro-ROS/micro_ros_platformio)
- [Fishbot 项目文档](../README.md)

---

**最后更新**：2026年4月14日  
**分析状态**：✅ 完成  
**验证工具**：✅ 已提供
