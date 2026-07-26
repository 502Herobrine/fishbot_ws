from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # 默认使用专门的零重力世界，只显示真实轮子状态，不让Gazebo物理引擎驱动车体移动
    default_world = PathJoinSubstitution([
        FindPackageShare('fishbot_bringup'),
        'worlds',
        'wheel_mirror.world',
    ])

    # 启动真实小车的完整bringup，其中包含micro-ROS Agent和robot_state_publisher。
    # micro-ROS Agent的启动开关和端口继续传给被包含的launch，保证顶层launch可以
    # 明确选择“由本次启动统一管理Agent”或“复用外部Agent”，不会隐式启动第二个实例。
    real_robot_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('fishbot_bringup'),
                'launch',
                'bringup.launch.py',
            ])
        ),
        condition=IfCondition(LaunchConfiguration('start_robot_bringup')),
        launch_arguments={
            'start_micro_ros_agent': LaunchConfiguration(
                'start_micro_ros_agent'),
            'micro_ros_agent_port': LaunchConfiguration(
                'micro_ros_agent_port'),
        }.items(),
    )

    # 启动Gazebo Classic，并允许通过gui参数选择是否打开图形界面
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'),
                'launch',
                'gazebo.launch.py',
            ])
        ),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'gui': LaunchConfiguration('gui'),
        }.items(),
    )

    # robot_state_publisher会以TRANSIENT_LOCAL方式发布robot_description，
    # spawn_entity会等待Gazebo工厂服务和该话题就绪后再创建模型，不需要使用固定延时
    spawn_fishbot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_fishbot_wheel_mirror',
        arguments=[
            '-entity', LaunchConfiguration('model_name'),
            '-topic', '/robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.0',
        ],
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'start_robot_bringup',
            default_value='true',
            description='是否同时启动真实小车bringup'),
        DeclareLaunchArgument(
            'start_micro_ros_agent',
            default_value='true',
            description='是否由本次bringup启动并管理micro-ROS Agent'),
        DeclareLaunchArgument(
            'micro_ros_agent_port',
            default_value='8888',
            description='micro-ROS Agent监听的UDP端口'),
        DeclareLaunchArgument(
            'gui',
            default_value='true',
            description='是否打开Gazebo图形界面'),
        DeclareLaunchArgument(
            'model_name',
            default_value='fishbot',
            description='Gazebo中的模型名称'),
        DeclareLaunchArgument(
            'world',
            default_value=default_world,
            description='Gazebo世界文件的绝对路径'),
        real_robot_bringup,
        gazebo,
        spawn_fishbot,
    ])
