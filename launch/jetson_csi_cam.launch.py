from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'sensor_id', default_value='0',
            description='Sensor ID of the camera'
        ),
        DeclareLaunchArgument(
            'cam_name', default_value='csi_cam_0',
            description='Name of the camera (corresponds to camera info)'
        ),
        DeclareLaunchArgument(
            'frame_id', default_value='csi_cam_0_link',
            description='TF frame ID for the camera'
        ),
        DeclareLaunchArgument(
            'parent_frame', default_value='map',
            description='Parent TF frame for the camera'
        ),
        DeclareLaunchArgument(
            'sync_sink', default_value='false',
            description='Synchronize the app sink'
        ),
        DeclareLaunchArgument(
            'width', default_value='1920',
            description='Image width'
        ),
        DeclareLaunchArgument(
            'height', default_value='1080',
            description='Image height'
        ),
        DeclareLaunchArgument(
            'fps', default_value='30',
            description='Desired framerate'
        ),
        DeclareLaunchArgument(
            'camera_device', default_value='/dev/video0',
            description='V4L2 camera device path'
        ),
        DeclareLaunchArgument(
            'pipeline', default_value='',
            description='Full GStreamer pipeline (overrides auto-generated one)'
        ),
        DeclareLaunchArgument(
            'encoding', default_value='jpeg',
            description='Image encoding: raw (uncompressed BGR) or jpeg (hardware JPEG via nvjpegenc)'
        ),
        DeclareLaunchArgument(
            'jpeg_quality', default_value='75',
            description='JPEG quality 1-100 (lower = smaller frames, less network traffic)'
        ),

        OpaqueFunction(function=lambda context: _launch_nodes(context)),
    ])


def _launch_nodes(context):
    cam_name = context.launch_configurations['cam_name']
    frame_id = context.launch_configurations['frame_id']
    parent_frame = context.launch_configurations['parent_frame']
    sensor_id = context.launch_configurations['sensor_id']
    sync_sink = context.launch_configurations['sync_sink'].lower() in ('true', '1', 'yes')
    pipeline = context.launch_configurations['pipeline']
    encoding = context.launch_configurations['encoding']
    jpeg_quality = context.launch_configurations['jpeg_quality']

    if not pipeline:
        width = context.launch_configurations['width']
        height = context.launch_configurations['height']
        fps = context.launch_configurations['fps']

        if encoding == 'jpeg':
            pipeline = (
                f'nvarguscamerasrc sensor-id={sensor_id} ! '
                f'video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1 ! '
                f'nvjpegenc quality={jpeg_quality} ! image/jpeg'
            )
        else:
            pipeline = (
                f'nvarguscamerasrc sensor-id={sensor_id} ! '
                f'video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1 ! '
                f'nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! video/x-raw,format=BGR'
            )

    parameters = {
        'camera_name': cam_name,
        'frame_id': frame_id,
        'sync_sink': sync_sink,
        'gscam_config': pipeline,
        'camera_info_url': f'package://jetson_csi_cam/calib/{cam_name}.yaml',
    }

    remappings = [
        ('/set_camera_info', [cam_name, '/set_camera_info']),
        ('camera/camera_info', [cam_name, '/camera_info']),
    ]

    if encoding == 'jpeg':
        parameters['image_encoding'] = 'jpeg'
        remappings.append(('camera/image_raw/compressed', [cam_name, '/image_raw/compressed']))
    else:
        remappings.append(('camera/image_raw', [cam_name, '/image_raw']))

    nodes = []

    gscam_node = Node(
        package='gscam',
        executable='gscam_node',
        name=cam_name,
        output='screen',
        parameters=[parameters],
        remappings=remappings,
    )
    nodes.append(gscam_node)

    tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name=[cam_name, '_tf'],
        arguments=['0', '0', '0', '0', '0', '0', parent_frame, frame_id],
        output='screen',
    )
    nodes.append(tf_node)

    return nodes
