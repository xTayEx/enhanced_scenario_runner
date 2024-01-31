import time
import carla
import cv2
import numpy as np


fourcc = cv2.VideoWriter_fourcc(*"XVID")
out = cv2.VideoWriter("output.avi", fourcc, 20.0, (400, 400))


def save_video(image):
    array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.height, image.width, 4))
    array = array[:, :, :3]
    out.write(array)


client = carla.Client("localhost", 2000)
world: carla.World = client.get_world()

camera_bp = world.get_blueprint_library().find("sensor.camera.rgb")
camera_bp.set_attribute("image_size_x", "400")
camera_bp.set_attribute("image_size_y", "400")
camera_bp.set_attribute("fov", "90")
transform = carla.Transform(carla.Location(z=10.0), carla.Rotation(pitch=-90))

# wait for ego
ego = None
while True:
    try:
        ego = world.get_actors().filter("vehicle.lincoln.mkz_2017")[0]
        break
    except Exception:
        print("can't find ego vehicle")
        time.sleep(1)

camera: carla.Actor = world.spawn_actor(camera_bp, transform, attach_to=ego)
camera.listen(lambda image: save_video(image))

# wait until ego is destroyed
while True:
    try:
        world.get_actors().filter("vehicle.lincoln.mkz_2017")[0]
    except Exception:
        break


out.release()
