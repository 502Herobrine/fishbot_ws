import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument
from launch.actions import EmitEvent
from launch.actions import RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def shutdown_if_microros_agent_exits(_event, context):
    """仅在Agent主动或异常退出时关闭launch，正常Ctrl+C期间不重复发送关闭事件."""
    if context.is_shutdown:
        return None

    return [
        EmitEvent(
            event=Shutdown(
                reason='micro-ROS Agent已经退出，关闭整套bringup以避免残留进程'
            )
        )
    ]


def generate_launch_description():
    fishbot_bringup_dir = get_package_share_directory(
        'fishbot_bringup')
    ydlidar_ros2_dir = get_package_share_directory(
        'ydlidar')

    urdf2tf = launch.actions.IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [fishbot_bringup_dir, '/launch', '/urdf2tf.launch.py']),
    )

    odom2tf = launch_ros.actions.Node(
        package='fishbot_bringup',
        executable='odom2tf',
        output='screen'
    )

    # micro-ROS Agent必须由当前launch统一管理，不能在退出后留下一个仍占用UDP端口的后台进程。
    # start_micro_ros_agent为false时，表示用户明确选择复用外部已经启动的Agent；
    # 此时当前launch既不会重复占用端口，也不会在退出时终止那个外部Agent。
    microros_agent = launch_ros.actions.Node(
        package='micro_ros_agent',
        executable='micro_ros_agent',
        arguments=[
            'udp4',
            '--port',
            LaunchConfiguration('micro_ros_agent_port'),
        ],
        output='screen',
        condition=IfCondition(LaunchConfiguration('start_micro_ros_agent')),
    )

    # Agent承载ESP32与ROS 2之间的全部话题通信。若它提前退出，继续保留里程计、
    # 雷达和Gazebo等节点只会形成一套无法接收底盘数据的残缺系统，并在下次启动时
    # 引发端口或Gazebo资源冲突。因此无论Agent是异常退出、端口占用后退出，还是被
    # 手动终止，都让同一顶层launch执行完整关闭，下一次启动便不再需要sudo pkill。
    shutdown_when_microros_agent_exits = RegisterEventHandler(
        OnProcessExit(
            target_action=microros_agent,
            on_exit=shutdown_if_microros_agent_exits,
        )
    )

    ros_serial2wifi = launch_ros.actions.Node(
        package='ros_serial2wifi',
        executable='tcp_server',
        parameters=[{'serial_port': '/tmp/tty_laser'}],
        output='screen'
    )

    ydlidar = launch.actions.IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [ydlidar_ros2_dir, '/launch', '/ydlidar_launch.py']),
    )

    # 使用 TimerAction 启动后 5 秒执行 ydlidar 节点
    ydlidar_delay = launch.actions.TimerAction(period=5.0, actions=[ydlidar])

    # Agent进程启动后先留出很短的端口初始化时间。若端口已被占用，Agent会在此期间
    # 退出并触发上面的完整关闭，其他节点不会刚启动就收到SIGINT；若选择复用外部
    # Agent，该定时器同样会在0.5秒后正常启动其余节点，不改变原有使用方式。
    remaining_nodes_delay = launch.actions.TimerAction(
        period=0.5,
        actions=[
            urdf2tf,
            odom2tf,
            ros_serial2wifi,
            ydlidar_delay,
        ],
    )

    return launch.LaunchDescription([
        DeclareLaunchArgument(
            'start_micro_ros_agent',
            default_value='true',
            description='是否由当前bringup启动并管理micro-ROS Agent'),
        DeclareLaunchArgument(
            'micro_ros_agent_port',
            default_value='8888',
            description='micro-ROS Agent监听的UDP端口'),
        # 必须先注册退出事件，再启动Agent，避免Agent因端口占用而立即退出时漏掉事件。
        shutdown_when_microros_agent_exits,
        microros_agent,
        remaining_nodes_delay,
    ])
