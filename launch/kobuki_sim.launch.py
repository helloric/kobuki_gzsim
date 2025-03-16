# Copyright 2022 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution

from launch_ros.actions import Node

import xacro


def generate_launch_description():
    """Configure ROS nodes for launch."""
    # Setup project paths
    pkg_kobuki_desc = get_package_share_directory('kobuki_description')
    pkg_kobuki_gzsim = get_package_share_directory('kobuki_gzsim')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    # Set gz-sim resource path
    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH', value=[
            os.path.join(pkg_kobuki_desc, os.pardir), ':',
            os.path.join(pkg_kobuki_gzsim, "models")
        ])

    # Setup to launch the simulator and Gazebo world
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': [
                '-r -v4 ',
                PathJoinSubstitution(
                    [
                        pkg_kobuki_gzsim,
                        'worlds',
                        'simple_room.world'])],
            'on_exit_shutdown': 'true'
        }.items(),
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'kobuki',
            '-topic', '/robot_description',
            '-x', '0',
            '-y', '0',
            '-z', '0.01'
        ]
    )

    bridge_path = os.path.join(
        pkg_kobuki_gzsim, 'config', 'ros_gz_bridge.yaml')
    # Bridge ROS topics and Gazebo messages for establishing communication
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[
            {'config_file': bridge_path},
            {'qos_overrides./tf_static.publisher.durability':
                'transient_local'}
        ],
        output='screen'
    )

    robot_xacro_path = os.path.join(
        pkg_kobuki_gzsim, 'urdf', 'kobuki_standalone_gz_sim.urdf.xacro')
    if not os.path.isfile(robot_xacro_path):
        raise RuntimeError(
            f'URDF description for kobuki base not found {pkg_kobuki_gzsim}')
    robot_description = xacro.process_file(str(robot_xacro_path))
    # Robot state description
    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {'use_sim_time': True},
            {'publish_frequency': 5.0},
            {'robot_description': robot_description.toxml()}
        ],
        # remappings=[
        #     ('/tf', ['/', robot_name, '/tf']),
        #     ('/tf_static', ['/', robot_name, '/tf_static'])]
    )
    return LaunchDescription([
        state_publisher,
        gz_resource_path,
        gz_sim,
        bridge,
        spawn_robot,
    ])
