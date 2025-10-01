import carla
import random
import time
import numpy as np
import cv2

client = carla.Client('localhost', 2000)
client.set_timeout(5.0)
time.sleep(2)
world = client.get_world()
bp_library = world.get_blueprint_library()
for actor in world.get_actors().filter('*sensor*'):
    actor.destroy()
for actor in world.get_actors().filter('*vehicle*'):
    actor.destroy()
bp = random.choice(bp_library.filter('vehicle'))
spawn_points = world.get_map().get_spawn_points()
if not spawn_points:
    raise RuntimeError("No spawn points available!")
spawn_point = random.choice(spawn_points)

vehicle = world.spawn_actor(bp, spawn_point)
print("✅ Vehicle spawned")
vehicle.set_autopilot(True)

# camera set up
camera_bp = bp_library.find('sensor.camera.rgb')
camera_bp.set_attribute('image_size_x', '640')
camera_bp.set_attribute('image_size_y', '480')
camera_bp.set_attribute('fov', '90')
time.sleep(1)
front_cam_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
front_camera = world.spawn_actor(camera_bp, front_cam_transform, attach_to=vehicle)
target_speed = 30
last_signal_time = time.time()
	
# cruise control
        
def adjust_speed(vehicle, target_kmh):
	current_velocity = vehicle.get_velocity()
	current_speed = 3.6 * current_velocity.length()  # m/s -> km/h
	if current_speed < target_kmh - 1:
		vehicle.apply_control(carla.VehicleControl(throttle=0.5, brake=0))
	elif current_speed > target_kmh + 1:
		vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=0.3))
	else:
		vehicle.apply_control(carla.VehicleControl(throttle=0.3, brake=0))

# detect traffic signal simulation
def simulate_traffic_signs():
	global target_speed, last_signal_time
	if time.time() - last_signal_time > 15:
		target_speed = random.choice([30, 50, 70])
	print(f"🚦 New sign detecte: limit of {target_speed} km/h")
	last_signal_time = time.time()
	
latest_frame = None
# process camera img
def show_front_camera(image):
	global latest_frame
	if image is None or image.raw_data is None:
		return
	img = np.frombuffer(image.raw_data, dtype=np.uint8)
	img = np.reshape(img, (image.height, image.width, 4))[:, :, :3]
	latest_frame = img

front_camera.listen(lambda img: show_front_camera(img))
print("System active. Cruise control on!")

try:
	while True:
		simulate_traffic_signs()
		adjust_speed(vehicle, target_speed)
		if latest_frame is not None:
			cv2.imshow("front camera", latest_frame)
			if cv2.waitKey(1) == 27:
				break
except KeyboardInterrupt:
    print("🛑 Closing...")
    front_camera.stop()
    vehicle.destroy()
    cv2.destroyAllWindows()