import carla
import random
import time
import numpy as np
import cv2

client = carla.Client('localhost', 2000)
client.set_timeout(2.0)
world = client.get_world()
bp_library = world.get_blueprint_library()
bp = random.choice(bp_library.filter('vehicle'))
spawn_point = random.choice(world.get_map().get_spawn_points())
vehicle = world.spawn_actor(bp, spawn_point)
print("✅ car spwaned in carla")
vehicle.set_autopilot(True)

# camera set up
camera_bp = bp_library.find('sensor.camera.rgb')
camera_bp.set_attribute('image_size_x', '800')
camera_bp.set_attribute('image_size_y', '600')
camera_bp.set_attribute('fov', '90')
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
	
# process camera img
def show_front_camera(image):
	img = np.frombuffer(image.raw_data, dtype=np.uint8)
	img = np.reshape(img, (image.height, image.width, 4))[:, :, :3]
	cv2.imshow("front camera", img)
	cv2.waitKey(1)

front_camera.listen(lambda img: show_front_camera(img))
print("System active. Cruise control on!")

try:
    while True:
        simulate_traffic_signs()
        adjust_speed(vehicle, target_speed)
except KeyboardInterrupt:
    print("🛑 Closing...")
    front_camera.stop()
    vehicle.destroy()
    cv2.destroyAllWindows()