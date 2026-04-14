# Fishbot 话题时间戳来源分析

## `/scan` 话题时间戳来源

**发布节点**: `ydlidar_node` (ydlidar_ros2 包)

**时间戳来源**: **主机的系统时间**

### 详细说明

1. **驱动代码位置**: [src/ydlidar_ros2/src/ydlidar_node.cpp](src/ydlidar_ros2/src/ydlidar_node.cpp#L180)

2. **时间戳设置方式**:
   ```cpp
   // 第180行
   scan_msg->header.stamp.sec = RCL_NS_TO_S(scan.stamp);
   scan_msg->header.stamp.nanosec = scan.stamp - RCL_S_TO_NS(scan_msg->header.stamp.sec);
   ```

3. **scan.stamp 来源** (ydlidar_ros2/sdk 中):
   - 在 `TiaLidarDriver::getScanData()` 中: `nodes[index].stamp = stamp ? stamp : getTime();`
   - 其他雷达驱动类似: `(*node).stamp = getTime();`

4. **getTime() 函数定义** ([ydlidar_ros2/sdk/core/base/timer.h](src/ydlidar_ros2/sdk/core/base/timer.h)):
   ```cpp
   #define getTime() impl::getCurrentTime()
   ```

5. **getCurrentTime() 实现** ([ydlidar_ros2/sdk/core/base/timer.cpp](src/ydlidar_ros2/sdk/core/base/timer.cpp)):
   ```cpp
   uint64_t getCurrentTime() {
       #if HAS_CLOCK_GETTIME
       struct timespec tim;
       clock_gettime(CLOCK_REALTIME, &tim);  // ← 使用系统实时时钟
       return static_cast<uint64_t>(tim.tv_sec) * 1000000000LL + tim.tv_nsec;
       #else
       struct timeval timeofday;
       gettimeofday(&timeofday, NULL);
       return static_cast<uint64_t>(timeofday.tv_sec) * 1000000000LL + 
              static_cast<uint64_t>(timeofday.tv_usec) * 1000LL;
       #endif
   }
   ```

**结论**: `/scan` 话题的时间戳与主机（Linux 系统）的系统时间同步。

---

## `/odom` 话题时间戳来源

**发布节点**: `micro_ros_agent` (micro_ros_agent 包)

**时间戳来源**: **ESP32 主控板的时间**

### 详细说明

1. **微控制器连接路径**:
   - ESP32 主控板 → UART/以太网 → `micro_ros_agent` → ROS 2 主机

2. **micro-ROS 的工作原理**:
   - `micro_ros_agent` 是一个通信代理，接收来自 ESP32 的 micro-ROS 消息
   - `/odom` (Odometry) 消息由 ESP32 上的 micro-ROS 应用程序发布
   - 消息中的时间戳来自 **ESP32 的本地时间** (通常是 ESP32 的滴答计数或实时时钟)

3. **订阅方式** ([src/fishbot_bringup/src/odom2tf.cpp](src/fishbot_bringup/src/odom2tf.cpp)):
   ```cpp
   odom_subscribe_ = this->create_subscription<nav_msgs::msg::Odometry>(
       "odom", rclcpp::SensorDataQoS(),
       std::bind(&OdomTopic2TF::odom_callback_, this, std::placeholders::_1));
   
   // odom_callback_ 中直接使用消息的时间戳
   transform.header = msg->header;  // 使用原始消息的时间戳
   ```

4. **通信路径**:
   - ESP32 → `ros_serial2wifi` UDP 桥接
   - UDP → `micro_ros_agent` 
   - `micro_ros_agent` → ROS 2 话题 `/odom`

**结论**: `/odom` 话题的时间戳来自 **ESP32 主控板的本地时间**。

---

## 总结表格

| 话题 | 发布者 | 时间戳来源 | 特点 |
|------|--------|----------|------|
| `/scan` | ydlidar_node | 主机系统时间 (CLOCK_REALTIME) | 与主机系统时间同步 |
| `/odom` | micro_ros_agent (from ESP32) | ESP32 本地时间 | 独立于主机时间，取决于 ESP32 时间精度 |

---

## 时间同步建议

如果需要两个话题的时间戳一致:
1. **方案 A**: 主机通过 NTP 同步，ESP32 通过某种方式获取主机时间（e.g., ROS TimeSync）
2. **方案 B**: 在 `odom2tf` 节点中拦截消息并替换时间戳为主机时间（但会失去原始时间戳信息）
3. **方案 C**: 使用主机端的时间作为标准，并检查 ESP32 时间是否与主机同步
