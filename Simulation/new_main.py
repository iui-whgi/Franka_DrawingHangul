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
from new_korean import generate_korean_character

import numpy as np
import h5py


class DrawingApp:
    def __init__(self, character_list, original_position, draw_scale=1.5):
        self.simulation_app = simulation_app
        self.world = None
        self.my_task = None
        self.my_franka = None
        self.my_controller = None
        self.ee_drawer = None
        self.paper_drawer = None
        self.character_list = character_list
        self.original_position = np.array(original_position)
        self.draw_scale = draw_scale
        self.current_stroke = 0
        self.reset_needed = False
        
        self.recorded_qpos = []
        self.ee_pose_data = []


    def setup_world(self):
        """Initializes the Isaac Sim world and sets up the camera."""
        self.world = World(stage_units_in_meters=1.0)
        eye_position = [1.0, 0.0, 0.8]
        target_position = [0.0, 0.0, 0.0]
        camera_prim_path = "/OmniverseKit_Persp"
        set_camera_view(
            eye=eye_position, target=target_position, camera_prim_path=camera_prim_path
        )

    def setup_task(self):
        """Adds the FR3Follow task to the world."""
        self.my_task = FR3Follow(name="drawing_task", target_position=self.original_position)
        self.world.add_task(self.my_task)
        self.world.reset()
        task_params = self.world.get_task("drawing_task").get_params()
        franka_name = task_params["robot_name"]["value"]
        self.target_name = task_params["target_name"]["value"]
        self.my_franka = self.world.scene.get_object(franka_name)
        joints_default_positions = np.array(
            [0.0, -0.3, 0.0, -1.8, 0.0, 1.5, 0.7, 0.04, 0.04]
        )
        self.my_franka.set_joints_default_state(positions=joints_default_positions)

    def setup_controllers(self):
        """Initializes the RMPFlow controller."""
        self.my_controller = RMPFlowController(
            name="target_follower_controller", robot_articulation=self.my_franka
        )

    def setup_drawers(self):
        """Initializes the trajectory drawers."""
        self.ee_drawer = TrajectoryDrawer()
        self.ee_drawer.initialize()
        self.paper_drawer = TrajectoryDrawer()
        self.paper_drawer.initialize()

    def get_end_effector_position(self):
        """FR3 로봇의 엔드 이펙터 위치 가져오기"""
        stage = get_current_stage()
        ee_prim = get_prim_at_path("/World/FR3/fr3_hand_tcp")
        if ee_prim:
            xform = UsdGeom.Xformable(ee_prim)
            world_transform = xform.ComputeLocalToWorldTransform(0)
            return world_transform.ExtractTranslation()
        return None

    def record_step(self):
        qpos = self.my_franka.get_joint_positions()
        qpos = qpos[:-1]

        ee_pos = self.get_end_effector_position()
        self.ee_pose_data.append(ee_pos)
        self.recorded_qpos.append(qpos)
    
    def save_dataset(self, filename='dataset.h5'):
        print("Checking recorded image shapes...")
        all_shapes_match = True
        if all_shapes_match:
            try:
                qpos_array = np.array(self.recorded_qpos, dtype=np.float64)
                ee_pose_array = np.array(self.ee_pose_data ,dtype=np.float64)

                with h5py.File(filename, 'w') as f:
                    f.create_dataset('action', data=qpos_array, dtype='float64')
                    f.create_dataset('ee_pose', data=ee_pose_array , dtype='float64')
                print(f"Dataset saved to {filename}")
            except Exception as e:
                print(f"Error during saving: {e}")
        else:
            print("Dataset not saved due to image shape mismatch.")

    def run(self):
        """Main simulation loop."""
        self.setup_world()
        self.setup_task()
        self.setup_controllers()
        self.setup_drawers()
        articulation_controller = self.my_franka.get_articulation_controller()
        while self.simulation_app.is_running():
            self.world.step(render=True)

            if self.world.is_stopped() and not self.reset_needed:
                self.reset_needed = True

            if self.world.is_playing():
                if self.reset_needed:
                    self.world.reset()
                    self.my_controller.reset()
                    self.reset_needed = False
                    self.current_stroke = 0

                observations = self.world.get_observations()
 
                ee_pos = self.get_end_effector_position()
                if ee_pos is not None:
                    self.ee_drawer.update_drawing(ee_pos)
                    if ee_pos[2] < 0.205:
                        self.paper_drawer.update_drawing(ee_pos)

                    trajectory, is_stroke_complete ,len_char = generate_korean_character(
                        self.character_list,
                        current_stroke=self.current_stroke,
                        draw_scale=self.draw_scale,
                        ee_pos=ee_pos,
                        original_position=self.original_position,
                    )
                    if trajectory is not None:
                        self.my_task.set_cube_pose(trajectory)
                        actions = self.my_controller.forward(
                            target_end_effector_position=trajectory,
                            target_end_effector_orientation=observations[self.target_name][
                                "orientation"
                            ],
                        )
                        articulation_controller.apply_action(actions)
                        self.record_step()
                        
                    if is_stroke_complete:
                        self.current_stroke += 1
                        print(f"[STROKE UPDATE] current_stroke: {self.current_stroke}")
                        print(f"[STROKE UPDATE] length_stroke: {len_char}")

                        if self.current_stroke == len_char:
                            print("Saving the dataset...")
                            self.save_dataset(filename='joints_state.h5')
                            print("Simulation run completed. Data saved.")
                            is_stroke_complete = False
                            self.simulation_app.close()


if __name__ == "__main__":
    character_list = ["융", "합", "프", "로", "젝", "트", "공", "모", "전"]
    original_position = [0.5, 0, 0.2]
    drawing_app = DrawingApp(character_list, original_position)
    drawing_app.run()