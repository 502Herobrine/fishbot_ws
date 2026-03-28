import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # 参数定义
    frame_id = 'fishbot_camera' 
    rgb_topic = '/fishbot_camera_raw'
    camera_info_yaml = '/home/nbclass/SRTP/fishbot_ws/src/fishbot_navigation2/config/camera_info.yaml'

    # RTAB-Map 核心参数
    parameters = {
        'frame_id': frame_id,
        'subscribe_depth': False,      # 单目相机关闭深度订阅
        'subscribe_rgbd': True,       # 通过同步节点订阅 rgbd_image 话题
        'approx_sync': True,          # 异步对齐
        # 单目建图关键参数
        'Mem/StereoFromMotion': 'true', # 允许从单目运动中三角化 3D 点
        'Vis/EstimationType': '2',      # 使用 2D-2D 极线几何估计位姿（无深度图时的标准配置）
        'Vis/MinInliers': '20',         # 特征匹配最小内点数
    }

    remappings = [
        ('rgb/image', rgb_topic),
        ('rgb/camera_info', '/camera/camera_info'),
        ('rgbd_image', 'rgbd_image')
    ]

    return LaunchDescription([
        # 1. 发布 CameraInfo 话题（手动加载内参）
        Node(
            package='rtabmap_util',
            executable='yaml_to_camera_info.py',
            parameters=[{'yaml_path': camera_info_yaml}],
            remappings=[('image', rgb_topic),
                        ('camera_info', '/camera/camera_info')]
        ),

        # 2. RGB 同步节点：将单目图像和内参打包成 rgbd_image
        # 注意：这里使用的是 rgb_sync 而不是 rgbd_sync
        Node(
            package='rtabmap_sync',
            executable='rgb_sync',
            output='screen',
            parameters=[{'approx_sync': True}],
            remappings=remappings
        ),

        # 3. 视觉里程计节点 (单目模式)
        Node(
            package='rtabmap_odom',
            executable='rgbd_odometry',
            output='screen',
            parameters=[parameters],
            remappings=remappings
        ),

        # 4. RTAB-Map SLAM 主节点
        Node(
            package='rtabmap_slam',
            executable='rtabmap',
            output='screen',
            parameters=[parameters],
            remappings=remappings,
            arguments=['-d'] # 启动时删除旧数据库
        ),

        # 5. 可视化界面 (可选)
        Node(
            package='rtabmap_viz',
            executable='rtabmap_viz',
            output='screen',
            parameters=[parameters],
            remappings=remappings
        ),
    ])