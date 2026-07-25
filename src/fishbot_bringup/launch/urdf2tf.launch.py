import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from launch.conditions import IfCondition


def generate_launch_description():
    # 获取默认路径
    urdf_tutorial_path = get_package_share_directory('fishbot_description')
    fishbot_model_path = urdf_tutorial_path + '/urdf/fishbot.urdf'
    # 为 Launch 声明参数
    action_declare_arg_mode_path = launch.actions.DeclareLaunchArgument(
        name='model', default_value=str(fishbot_model_path),
        description='URDF 的绝对路径')
    # 真机固件会直接发布真实编码器对应的/joint_states，默认不能再启动一个发布默认角度的节点
    action_declare_arg_joint_state_publisher = launch.actions.DeclareLaunchArgument(
        name='use_joint_state_publisher', default_value='false',
        description='是否启动用于离线测试的默认关节状态发布节点')
    # 真机消息使用ESP32与主机同步后的系统时间，因此真机模式必须使用系统时间而不是Gazebo时间
    action_declare_arg_use_sim_time = launch.actions.DeclareLaunchArgument(
        name='use_sim_time', default_value='false',
        description='是否使用仿真时间；连接真实ESP32时应保持为false')
    # 获取文件内容生成新的参数
    robot_description = launch_ros.parameter_descriptions.ParameterValue(
        launch.substitutions.Command(
            ['cat ', launch.substitutions.LaunchConfiguration('model')]),
        value_type=str)
    # 状态发布节点
    robot_state_publisher_node = launch_ros.actions.Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'publish_frequency': 50.0,
            'ignore_timestamp': False,
            'use_sim_time': launch.substitutions.LaunchConfiguration(
                'use_sim_time')
        }]
    )
    # 该节点只用于ESP32未连接时给URDF关节发布默认值，真机模式默认不启动，避免与固件争抢/joint_states
    joint_state_publisher_node = launch_ros.actions.Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        condition=IfCondition(
            launch.substitutions.LaunchConfiguration(
                'use_joint_state_publisher')),
    )
    return launch.LaunchDescription([
        action_declare_arg_mode_path,
        action_declare_arg_joint_state_publisher,
        action_declare_arg_use_sim_time,
        joint_state_publisher_node,
        robot_state_publisher_node,
    ])
