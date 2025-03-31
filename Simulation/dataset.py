
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": False})

import omni
import omni.usd
import omni.timeline
import omni.kit
import numpy as np
import cv2
from isaacsim.core.api import World
from isaacsim.robot.manipulators.examples.franka.controllers.stacking_controller import StackingController
from isaacsim.robot.manipulators.examples.franka.tasks import Stacking
from pxr import Usd, UsdGeom, Gf, UsdLux
from isaacsim.sensors.camera import Camera
from PIL import Image
import h5py
import time
import os


class StackingSimulation:
    def __init__(self):
        self.recorded_actions = []
        self.recorded_qpos = []
        self.recorded_top_images = []
        self.recorded_front_images = []
        self.setup_world()
        self.setup_stage()
        self.setup_controller()
        self.top_image_count = 0
        self.front_image_count = 0
        self.max_images = 30

        self.top_image_path = "top"
        self.front_image_path = "front"

    # Ensure directories exist
        if not os.path.exists(self.top_image_path):
            os.makedirs(self.top_image_path)
        if not os.path.exists(self.front_image_path):
            os.makedirs(self.front_image_path)

    def setup_world(self):
        self.world = World(stage_units_in_meters=1.0)
        self.task = Stacking()
        self.world.add_task(self.task)
        self.world.reset()
        self.robot_name = self.task.get_params()["robot_name"]["value"]
        self.franka = self.world.scene.get_object(self.robot_name)

    def setup_stage(self):
        self.stage = omni.usd.get_context().get_stage()
        self.create_sphere_light('/World/SphereLight', [1.0, 0.0, 3.0], (1.0, 0.8, 0.8), 1500.0, 0.2)
        self.top_camera = self.create_camera('/World/top_camera', [0.4, 0, 3.0], [0.0, 0.0, 0.0], 20)
        self.top_camera.initialize()
        self.front_camera = self.create_camera('/World/front_camera', [2.3, 0.0, 2], [0.0, 45.0, 90], 20)
        self.front_camera.initialize()

        self.reset_camera_orientation_and_translation('/World/front_camera', [2.4, 0.0, 2.0], [45.0, 0.0, 90.0])
        self.reset_camera_orientation_and_translation('/World/top_camera', [0.4, 0, 3.0], [0.0, 0.0, 0.0])
        self.adjust_light_translation()

    def adjust_light_translation(self):
        light = self.stage.GetPrimAtPath("/World/defaultGroundPlane/SphereLight")
        if light:
            xform = UsdGeom.Xformable(light)
            for op in xform.GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                    op.Set(Gf.Vec3d(1.5, 0, 2.5))
                    break

    def create_sphere_light(self, light_path, pos, color, intensity, radius):
        light = UsdLux.SphereLight.Define(self.stage, light_path)
        light.CreateIntensityAttr(intensity)
        light.CreateColorAttr(Gf.Vec3f(color))
        light.CreateRadiusAttr(radius)
        UsdGeom.XformCommonAPI(light).SetTranslate(Gf.Vec3d(pos[0], pos[1], pos[2]))

    def create_camera(self, camera_path, pos, ori, freq):
        return Camera(prim_path=camera_path, frequency=freq, resolution=(640, 480), position=pos)

    def reset_camera_orientation_and_translation(self, camera_path, pos, ori):
        camera_prim = self.stage.GetPrimAtPath(camera_path)
        if camera_prim:
            xformable = UsdGeom.Xformable(camera_prim)
            xformable.ClearXformOpOrder()
            xform_op_translation = xformable.AddTranslateOp()
            xform_op_translation.Set(Gf.Vec3f(pos))
            xform_op_orientation = xformable.AddRotateXYZOp()
            xform_op_orientation.Set(Gf.Vec3f(ori))

    def setup_controller(self):
        self.controller = StackingController(name="stacking_controller", gripper=self.franka.gripper, robot_articulation=self.franka, picking_order_cube_names=self.task.get_cube_names(), robot_observation_name=self.robot_name)
        self.articulation_controller = self.franka.get_articulation_controller()

    def resize_image(self, image, target_size=(480, 640)):
        image_pil = Image.fromarray(image)
        resized_image = image_pil.resize(target_size[::-1], Image.Resampling.LANCZOS)
        return np.array(resized_image)

    def save_image_with_opencv(self, image, filename):
        # Convert the image from RGB to BGR
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        # Save the image using OpenCV
        cv2.imwrite(filename, image_bgr)

    def generate_box(self, box_path, pos):
        # Access the camera's USD primitive
        camera_prim = self.stage.GetPrimAtPath(box_path)
        if camera_prim:
            # Get the Xformable API interface
            xformable = UsdGeom.Xformable(camera_prim)
            # Clear all existing transform operations, which effectively resets them
            xformable.ClearXformOpOrder()

            # Apply a new translation
            new_translation = Gf.Vec3f(pos)  # Set to the specified position
            xform_op_translation = xformable.AddTranslateOp()
            xform_op_translation.Set(new_translation)


    def record_step(self):
        qpos = self.franka.get_joint_positions()
        qpos = qpos[:-1]
        top_img = self.top_camera.get_rgba()
        front_img = self.front_camera.get_rgba()

        if top_img is None or top_img.size == 0:
            print("Skipping step: Top image capture failed or returned empty.")
            return
        
        if front_img is None or front_img.size == 0:
            print("Skipping step: Front image capture failed or returned empty.")
            return
        
        # Process and store the images
        top_img = self.resize_image(top_img[..., :3])
        top_rgb = cv2.cvtColor(top_img, cv2.COLOR_RGB2BGR)
        self.recorded_top_images.append(top_rgb)

        front_img = self.resize_image(front_img[..., :3])
        front_rgb = cv2.cvtColor(front_img, cv2.COLOR_RGB2BGR)

        self.recorded_front_images.append(front_rgb)
        if self.top_image_count < self.max_images:
            top_filename = os.path.join(self.top_image_path, f"top_{self.top_image_count}.jpg")
            cv2.imwrite(top_filename, top_rgb)
            self.top_image_count += 1
        
        if self.front_image_count < self.max_images:
            front_filename = os.path.join(self.front_image_path, f"front_{self.front_image_count}.jpg")
            cv2.imwrite(front_filename, front_rgb)
            self.front_image_count += 1
        # Store the joint positions
        self.recorded_actions.append(qpos)
        self.recorded_qpos.append(qpos)

    def save_dataset(self, filename='dataset.h5'):
        if not self.recorded_top_images or not self.recorded_front_images:
            print("No valid images recorded. Skipping dataset save.")
            return
        
        print("Checking recorded image shapes...")
        all_shapes_match = True
        expected_shape = (480, 640, 3)
        
        for img in self.recorded_top_images + self.recorded_front_images:
            if img.shape != expected_shape:
                all_shapes_match = False
                print(f"Mismatch found: Expected {expected_shape}, but got {img.shape}")

        if all_shapes_match:
            try:
                actions_array = np.array(self.recorded_actions, dtype=np.float64)
                qpos_array = np.array(self.recorded_qpos, dtype=np.float64)
                top_images_array = np.stack(self.recorded_top_images, axis=0).astype(np.uint8)
                front_images_array = np.stack(self.recorded_front_images, axis=0).astype(np.uint8)

                with h5py.File(filename, 'w') as f:
                    f.create_dataset('action', data=actions_array, dtype='float64')
                    obs_grp = f.create_group('observations')
                    obs_grp.create_dataset('qpos', data=qpos_array, dtype='float64')
                    images_grp = obs_grp.create_group('images')
                    images_grp.create_dataset('top', data=top_images_array, dtype='uint8')
                    images_grp.create_dataset('front', data=front_images_array, dtype='uint8')

                print(f"Dataset saved to {filename}")
            except Exception as e:
                print(f"Error during saving: {e}")
        else:
            print("Dataset not saved due to image shape mismatch.")

    def run(self):
        timeline = omni.timeline.get_timeline_interface()
        timeline.pause()
        print("Simulation will start playing after a 5-second delay...")
        time.sleep(5)
        timeline.play()
        print("Simulation is now running...")
        reset_needed = False
        start_time = time.time()
        run_duration = 30
        while timeline.is_playing():
            current_time = time.time()
            if (current_time - start_time) > run_duration:
                print("Pausing simulation...")
                timeline.pause()
                break
    
            # self.generate_box(box_path='/World/Cube' ,pos = [0.2 , 0.1 , 0.1])
            self.world.step(render=True)

            if self.world.is_stopped() and not reset_needed:
                reset_needed = True
            if self.world.is_playing():
                if reset_needed:
                    self.world.reset()
                    self.controller.reset()
                    reset_needed = False
                observations = self.world.get_observations()
                actions = self.controller.forward(observations=observations)
                self.articulation_controller.apply_action(actions)
                self.record_step()
        print("Saving the dataset...")
        self.save_dataset(filename='episode_stack_original_8.h5')
        print("Simulation run completed. Data saved.")

if __name__ == "__main__":
    simulation = StackingSimulation()
    simulation.run()
