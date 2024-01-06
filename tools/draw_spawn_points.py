"""make pylint happy"""
import argparse
import carla

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--port", type=int, default=2000)
parser.add_argument("--map", type=str, default="Town04")
args = parser.parse_args()

client = carla.Client(host=args.host, port=args.port)
client.load_world(args.map)

world = client.get_world()
spawn_points = world.get_map().get_spawn_points()
for spawn_point in spawn_points:
    world.debug.draw_point(spawn_point.location)
    world.debug.draw_string(
        spawn_point.location + carla.Location(z=1.0),
        f"({spawn_point.location.x:.2f}, {spawn_point.location.y:.2f}, {spawn_point.location.z:.2f})",
        draw_shadow=False,
        life_time=100000.0,
    )
