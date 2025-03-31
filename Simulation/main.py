from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

from isaacsim.core.api import World
from isaacsim.core.utils.prims import get_prim_at_path
from isaacsim.core.utils.viewports import set_camera_view
from isaacsim.core.utils.stage import get_current_stage
from pxr import UsdGeom

from controllers.rmpflow_controller import RMPFlowController
from modules.visualization.trajectory_drawer import TrajectoryDrawer
from modules.robot_control.fr3_follow import FR3Follow
from korean import generate_korean_character

import numpy as np

import matplotlib.pyplot as plt
import csv, datetime


# End Effector 위치 추적 함수
def get_end_effector_position():
    """FR3 로봇의 엔드 이펙터 위치 가져오기"""
    stage = get_current_stage()
    ee_prim = get_prim_at_path("/World/FR3/fr3_hand_tcp")
    if ee_prim:
        xform = UsdGeom.Xformable(ee_prim)
        world_transform = xform.ComputeLocalToWorldTransform(0)
        return world_transform.ExtractTranslation()
    return None


# 메인 스크립트 실행
def main():
    # 월드 생성
    my_world = World(stage_units_in_meters=1.0)
    # 그래프의 y-axis 뒤집기
    plt.gca().invert_yaxis()

    # 카메라 뷰 설정
    eye_position = [1.0, 0.0, 0.8]
    target_position = [0.0, 0.0, 0.0]
    camera_prim_path = "/OmniverseKit_Persp"
    set_camera_view(
        eye=eye_position, target=target_position, camera_prim_path=camera_prim_path
    )

    # 초기화
    character_list = ["융", "합", "프", "로", "젝", "트", "공", "모", "전"]
    original_position = [0.5, 0, 0.2]  # 시작 위치
    draw_scale = 1.5  # 그리기 속도 조절 (1.0보다 크면 빠르게, 작으면 느리게)
    cnt_js, cnt_ee = 0, 0

    joints_name = [
        'base', 'fp3_joint1', 'fp3_joint2', 
        'fp3_joint3', 'fp3_joint4', 'fp3_joint5', 
        'fp3_joint6', 'fp3_joint7', 'fp3_joint8', 
    ]
    dt = datetime.datetime.now()
    dt_str = f"{dt.year}_{dt.month}_{dt.day}_{dt.hour}_{dt.minute}_{dt.microsecond}"
    f0 = open(f"endeffector_data_{dt_str}.csv", "w")
    writer0 = csv.DictWriter(f0, fieldnames=['no', 'x', 'y', 'z'])
    writer0.writeheader()

    f1 = open(f"joints_state_data_{dt_str}.csv", "w")
    fieldnames = ['no']
    for i in joints_name:
        fieldnames.extend([i + "_positions", i + "_velocities"])
    writer1 = csv.DictWriter(f1, fieldnames=fieldnames)
    writer1.writeheader()

    graph_name = f"ee_pos_{dt_str}"

    my_task = FR3Follow(name="drawing_task", target_position=original_position)
    my_world.add_task(my_task)
    my_world.reset()

    ee_drawer = TrajectoryDrawer()
    ee_drawer.initialize()
    paper_drawer = TrajectoryDrawer()
    paper_drawer.initialize()

    # Task 파라미터 가져오기
    task_params = my_world.get_task("drawing_task").get_params()
    franka_name = task_params["robot_name"]["value"]
    target_name = task_params["target_name"]["value"]
    my_franka = my_world.scene.get_object(franka_name)

    # 기본 관절 위치 설정
    joints_default_positions = np.array(
        [0.0, -0.3, 0.0, -1.8, 0.0, 1.5, 0.7, 0.04, 0.04]
    )
    my_franka.set_joints_default_state(positions=joints_default_positions)

    # 컨트롤러 설정
    my_controller = RMPFlowController(
        name="target_follower_controller", robot_articulation=my_franka
    )
    articulation_controller = my_franka.get_articulation_controller()

    # 메인 시뮬레이션 루프
    reset_needed = False
    tick = 0
    current_stroke = 0
    while simulation_app.is_running():
        my_world.step(render=True)

        if my_world.is_stopped() and not reset_needed:
            reset_needed = True

        if my_world.is_playing():
            if reset_needed:
                my_world.reset()
                my_controller.reset()
                reset_needed = False
                current_stroke = 0
                tick = 0  # 새로운 획을 위해 tick 초기화

            observations = my_world.get_observations()
            tick += 1

            # 현재 엔드 이펙터 위치 가져오기
            _joints_state = my_franka.get_joints_state()
            joints_state_list = [_joints_state.positions, _joints_state.velocities]
            joints_state_list = np.swapaxes(joints_state_list, 0, 1)
            joints_state = np.array(joints_state_list).flatten()
            
            ee_pos = get_end_effector_position()
            if ee_pos is not None:
                ee_drawer.update_drawing(ee_pos)
                if ee_pos[2] < 0.205:
                    paper_drawer.update_drawing(ee_pos)

                # 한글 문자 궤적 생성
                trajectory, is_stroke_complete = generate_korean_character(
                    character_list,
                    current_stroke=current_stroke,
                    draw_scale=draw_scale,  # 그리기 속도 전달
                    ee_pos=ee_pos,
                    original_position=np.array(original_position),
                )
                if trajectory is not None:
                    # 타겟 위치 설정
                    my_task.set_cube_pose(trajectory)

                    # 로봇 컨트롤러 업데이트
                    actions = my_controller.forward(
                        target_end_effector_position=trajectory,
                        target_end_effector_orientation=observations[target_name][
                            "orientation"
                        ],
                    )

                    # 로봇에 액션 적용
                    articulation_controller.apply_action(actions)

                # 현재 획이 완료되었는지 확인
                if is_stroke_complete:
                    current_stroke += 1
                    print(f"[STROKE UPDATE] current_stroke: {current_stroke}")
                    tick = 0  # 새로운 획을 위해 tick 초기화

            ee_x = []
            ee_y = []

            # 디버깅 그리기
            ee_pos = get_end_effector_position()
            print(f"ee_pos: {ee_pos}")
            if ee_pos is not None:
                ee_drawer.update_drawing(ee_pos)
            
            # endeffector_data.csv
            for i in ee_drawer.point_list:
                if i[2] < 0.205:
                    ee_x.append(i[0])
                    ee_y.append(i[1])
                    data = {'no': cnt_ee, 'x': i[0], 'y': i[1], 'z': i[2]}
                    cnt_ee += 1
                    writer0.writerow(data)
            
            # joints_state_data.csv
            data = {'no': cnt_js}
            cnt_js += 1
            for i in range(1, len(fieldnames) - 1):
                data.update({fieldnames[i]: joints_state[i]})
            writer1.writerow(data)

        # ee_pos fig
        plt.scatter(ee_y, ee_x, color = 'blue', s = 10)
        plt.savefig(graph_name)
    f0.close()
    f1.close()
    simulation_app.close()


if __name__ == "__main__":
    main()
