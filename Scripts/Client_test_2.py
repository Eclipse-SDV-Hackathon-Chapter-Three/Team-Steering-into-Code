import carla
import random
import time
import numpy as np
import cv2

# Connect to CARLA server
client = carla.Client('100.95.17.117', 2000)
client.set_timeout(5.0)
time.sleep(2)

world = client.get_world()
bp_library = world.get_blueprint_library()

# Clean up existing sensors and vehicles
for actor in world.get_actors().filter('*sensor*'):
    actor.destroy()
for actor in world.get_actors().filter('*vehicle*'):
    actor.destroy()

# Spawn vehicle
bp = random.choice(bp_library.filter('vehicle'))
spawn_points = world.get_map().get_spawn_points()
if not spawn_points:
    raise RuntimeError("No spawn points available!")

spawn_point = random.choice(spawn_points)
vehicle = world.spawn_actor(bp, spawn_point)
print("✅ Vehicle spawned")

# Set up camera
camera_bp = bp_library.find('sensor.camera.rgb')
camera_bp.set_attribute('image_size_x', '640')
camera_bp.set_attribute('image_size_y', '480')
camera_bp.set_attribute('fov', '90')

time.sleep(1)
front_cam_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
front_camera = world.spawn_actor(camera_bp, front_cam_transform, attach_to=vehicle)

# Cruise control variables
target_speed = 30  # km/h
last_signal_time = time.time()
last_announced_speed = target_speed
latest_frame = None

# Enable autopilot for Traffic Manager to handle steering
vehicle.set_autopilot(True)
tm = client.get_trafficmanager()
tm.ignore_lights_percentage(vehicle, 100)
tm.ignore_signs_percentage(vehicle, 100)


def adjust_speed_with_tm(vehicle, target_kmh):
    """
    Adjust vehicle speed using Traffic Manager's target speed
    This works better with autopilot enabled
    """
    # Set target speed as percentage difference from speed limit
    # Traffic Manager uses speed limit as base, so we calculate offset
    current_velocity = vehicle.get_velocity()
    current_speed = 3.6 * current_velocity.length()  # m/s -> km/h
    
    # Get speed limit from Traffic Manager (default is usually 30 km/h in towns)
    speed_limit = vehicle.get_speed_limit()
    if speed_limit == 0:
        speed_limit = 30  # default fallback
    
    # Calculate percentage to reach target speed
    # Negative percentage = go slower, positive = go faster
    percentage = ((target_kmh - speed_limit) / speed_limit) * 100
    
    tm.vehicle_percentage_speed_difference(vehicle, -percentage)
    
    return current_speed


def simulate_traffic_signs():
    """Simulate detecting new speed limit signs"""
    global target_speed, last_signal_time, last_announced_speed
    
    current_time = time.time()
    
    # Check if 3-5 seconds have passed (randomize the interval)
    time_threshold = random.uniform(3.0, 5.0)
    
    if current_time - last_signal_time > time_threshold:
        # Detect new speed limit
        new_speed = random.choice([30, 50, 70, 90])
        
        if new_speed != last_announced_speed:
            target_speed = new_speed
            print(f"🚦 New speed limit detected: {new_speed} km/h")
            print(f"   Adjusting cruise control from {last_announced_speed} to {new_speed} km/h")
            last_announced_speed = new_speed
        
        last_signal_time = current_time


def show_front_camera(image):
    """Process camera images"""
    global latest_frame
    if image is None or image.raw_data is None:
        return
    
    img = np.frombuffer(image.raw_data, dtype=np.uint8)
    img = np.reshape(img, (image.height, image.width, 4))[:, :, :3]
    latest_frame = img


# Start camera feed
front_camera.listen(lambda img: show_front_camera(img))

print("🚗 System active. Cruise control enabled with autopilot!")
print("   The vehicle will steer automatically while following speed limits.")
print("   Press ESC in the camera window to quit.\n")

try:
    while True:
        # Simulate detecting new speed limit signs
        simulate_traffic_signs()
        
        # Adjust speed using Traffic Manager
        current_speed = adjust_speed_with_tm(vehicle, target_speed)
        
        # Display current status every second
        if int(time.time()) % 1 == 0:
            print(f"⏱️  Current: {current_speed:.1f} km/h | Target: {target_speed} km/h")
        
        # Display camera feed
        if latest_frame is not None:
            cv2.imshow("Front Camera - Cruise Control Active", latest_frame)
            if cv2.waitKey(1) == 27:  # ESC key
                break
        
        time.sleep(0.05)  # Small delay to prevent CPU overload

except KeyboardInterrupt:
    print("\n🛑 Shutting down...")

finally:
    # Clean up
    print("Cleaning up actors...")
    front_camera.stop()
    front_camera.destroy()
    vehicle.destroy()
    cv2.destroyAllWindows()
    print("✅ Done!")