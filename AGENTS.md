# FishBot 上位机开发约定

本文档适用于 `/home/nbclass/SRTP/fishbot_ws` 及其下的 ROS 2 上位机代码。它记录项目
所有者在开发过程中反复确认的要求、当前系统事实和联调习惯。新代码必须同时遵守本
文档和各目录下更具体的约定；如果用户在当前任务中明确提出了新要求，以用户要求为准，
并在完成后更新本文件中已经失效的内容。

## 1. 沟通和工作方式

- 默认使用中文沟通。涉及技术决策时，先说明现象、根因、影响范围和方案，再实施修改。
- 对跨文件或有运行风险的任务，先列出简短计划；执行过程中及时报告关键发现、假设和
  验证结果。
- 不要凭文件名猜测实现。修改前先阅读相关 launch、URDF/xacro、节点、配置和被调用的
  库；如果项目提供了官方或历史参考实现，先对照参考实现。
- 用户重视干净、可维护、符合原有风格的实现。不要为了快速验证而复制一套临时 API、
  重复发布者或重复节点。
- 不确定且无法从源码、日志或运行状态安全推断的信息，才向用户提问；其余情况根据当前
  项目结构做最小且可回退的假设，并明确说明。
- 默认保留用户已有的未提交修改、子模块状态和实验文件。不要因为本任务而执行
  `git reset --hard`、`git checkout --`、批量删除或覆盖操作。
- 用户没有要求提交时不要擅自提交；报告修改文件、验证命令和仍存在的既有问题即可。

## 2. 当前平台和系统边界

- 当前目标平台是 ROS 2 Humble、Gazebo Classic 和 PlatformIO/micro-ROS ESP32 小车。
  如果实际环境变更，先确认发行版、Gazebo 版本、RMW 实现和固件传输方式，再使用对应
  API；不要把别的 ROS 发行版的旧 launch 写法直接移植过来。
- 配套单片机工程根目录为
  `/home/nbclass/Documents/PlatformIO/Projects/motor_control`。需要确认编码器、运动学、
  PID、固件话题或硬件引脚时，必须到该目录阅读实际源码和 `lib`，不要在上位机工作区
  猜测固件实现。
- 上位机工作空间包含 `fishbot_bringup`、`fishbot_description`、
  `fishbot_navigation2`、`ydlidar_ros2`、`ros_serial2wifi`、`micro_ros_msgs`
  等包。修改一个包时只触及必要依赖，不要顺手重构无关包。
- 上位机与固件的边界必须清楚：上位机负责 ROS 2、Gazebo、TF、导航和通信代理；固件
  负责电机、编码器、运动学、PID 和 micro-ROS 客户端。除非用户明确授权，不要因为
  上位机问题改动固件源码。

## 3. 关键话题和数据链路

- 真机模式的 `/joint_states` 来自 ESP32 的编码器数据。`urdf2tf.launch.py` 只负责
  `robot_state_publisher`，测试用的默认 `joint_state_publisher` 默认关闭，避免与固件
  同时发布同一话题。不要再添加第二个默认轮角发布者。
- `/joint_states` 中的名称必须与 URDF 完全一致：
  `left_wheel_joint`、`right_wheel_joint`。名称、数组顺序和左右轮含义都不能随意交换。
- Gazebo 的 `libgazebo_set_joint_positions_plugin.so` 订阅 `/joint_states`（插件配置中的
  `topic_name` 为 `joint_states`），把真实轮角写入同名关节；第二个
  `libgazebo_ros_joint_state_publisher.so` 只用于把 Gazebo 实际关节状态发布到
  `/gazebo_joint_states`，用于观察和排查。修改 URDF 时必须保留这两个插件，除非用户
  明确要求删除或替换。
- `/cmd_vel`、`/odom`、`/joint_states` 的 QoS 必须和另一端匹配。排查“能看到话题但收不
  到消息”时，使用 `ros2 topic info -v <topic>` 检查发布者、订阅者和 QoS，不要直接
  猜测通信故障。
- `/odom` 和真实轮角消息使用 micro-ROS 时间同步后的主机时间。改变时间源或
  `use_sim_time` 前，说明会影响哪些 TF、传感器和导航节点。

## 4. URDF、TF 和 Gazebo 约定

- 使用 REP-103 坐标约定：`base_link` 的 X 轴朝前、Y 轴朝左、Z 轴朝上。
- 当前 FishBot 参考模型中，左轮位于 `+Y`、右轮位于 `-Y`；这两个位置不是通过交换
  关节名称来修正转向的。左右轮关节的旋转轴按官方 FishBot 模型使用 `0 1 0`。
- 轮子圆柱默认沿 Z 轴，轮子视觉和碰撞体的 `rpy="1.5707963 0 0"` 用于将轮轴放到
  Y 方向。若调整轮子姿态、原点或轴，必须同时检查视觉、碰撞、惯性、色标和
  `JointState` 角度正方向。
- 轮子外侧色标是观察实际角度变化的实验辅助，不要在没有验证左右轮含义前删除或交换。
- 优先参考：
  `~/SRTP/ROS2_Notes/chapt6/chapt6_ws/src/fishbot_description/urdf`。
  参考文件用于确认坐标和命名，不表示可以不加分析地覆盖当前项目已有的尺寸、插件或
  联调配置。
- 修改 URDF 后必须重新生成/重启 Gazebo 模型；已经 spawn 的实体不会自动读取磁盘上的
  新 URDF。至少执行 `check_urdf`，并在运行时观察对应关节和 TF。

## 5. Launch 文件要求

- 使用 ROS 2 Python launch API：`generate_launch_description()`、显式
  `DeclareLaunchArgument`、`LaunchConfiguration`、`FindPackageShare` 或
  `PathJoinSubstitution`。不要硬编码其他机器的绝对安装路径。
- 大型系统优先通过 `IncludeLaunchDescription` 组合已有 launch，而不是把所有节点堆进一
  个新文件。参数、条件和启动顺序要写在 launch 中，并用中文注释说明原因。
- micro-ROS Agent 默认由当前顶层 bringup 启动和管理，默认端口为 8888。若 Agent 退出、
  端口冲突或被终止，整套 bringup 应收尾，不能留下占端口的孤儿进程。正常退出使用
  `Ctrl+C`，不要把 `sudo pkill -f micro_ros_agent` 当作启动流程。
- 如果确实需要复用外部 Agent，使用已有的 `start_micro_ros_agent:=false` 参数，并确认
  不会同时启动第二套 Gazebo、TCP 服务或底盘节点。不要在 launch 内加入针对全机的
  `pkill`、`kill -9` 或模糊进程匹配。
- 对端口冲突、硬件不可用、Gazebo 服务不存在等启动错误，优先通过 launch 生命周期、
  条件和事件处理解决；不要静默忽略错误，也不要通过无限重启掩盖根因。
- launch 文件中的延时只能用于明确的初始化依赖，并注明原因。不要用固定延时替代本来
  可以使用的服务等待、话题等待或事件依赖。

## 6. 代码实现和注释风格

- 先复用已有节点、库函数、消息和参数；只有现有抽象确实不能表达需求时才新增 API。
- 新函数必须放在它所属的库或模块中，不能为了一个调用点把实现塞进不相关的 launch、
  节点入口或脚本。声明和实现保持同一模块的原有组织方式。
- 中文注释要像现有 URDF 和 launch 一样解释“为什么”，尤其是坐标轴、单位、QoS、
  话题来源、线程/任务边界、启动顺序和插件回路；不要写与代码重复的空泛注释。
- 保持原有命名、缩进和文件组织。修改已有代码时，尽量只改变需求相关的最小范围，
  不要顺手格式化整棵目录。
- 不要复制一个“看起来能用”的新实现来绕开已有 API；如果发现现有 API 不足，先说明
  缺口，再在正确的库文件中补充并让调用方复用。

## 7. 推荐开发流程

1. 查看 `git status`，识别用户已有改动、子模块和当前运行实例。
2. 阅读目标文件、直接依赖和参考实现，梳理话题、TF、QoS、单位和生命周期。
3. 先列方案和风险，选最小修改面；涉及真车、电机或 Gazebo 实体时明确哪些动作会
   改变外部状态。
4. 修改后进行静态检查和构建。常用检查包括：

   ```bash
   source /opt/ros/humble/setup.bash
   colcon build --packages-select <package> --symlink-install
   check_urdf <absolute-path-to-urdf>
   ros2 launch <package> <launch-file>.launch.py --show-args
   git diff --check
   ```

5. 运行时先确认只有一套顶层 launch、Gazebo、Agent 和 TCP 服务；用 `Ctrl+C` 完整退出。
   修改 launch 或 URDF 后重启相关进程，再验证实际话题和 Gazebo 关节。
6. 报告时区分“本次修改导致的问题”和“测试发现的既有问题”。不要把未运行过的硬件
   实验描述成已验证。

## 8. 真车和仿真安全

- 真车联调前先确认轮子离地、目标速度为零、急停手段可用；不要在没有用户明确要求时
  发送运动指令或启用电机输出。
- 只观察轮子编码器同步时，优先使用 `/gazebo_joint_states` 和
  `sensor_msgs/msg/JointState` 检查角度、名称、时间戳和方向；不要同时打开一个会发布
  默认轮角的测试节点。
- 任何会让电机保持上次速度、改变 PID、改变编码器符号或改变网络地址的修改都属于
  高风险变更，必须先解释影响并得到明确授权。
