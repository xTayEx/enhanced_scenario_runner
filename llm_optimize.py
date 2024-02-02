import math
import subprocess
import time
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

import carla
import cv2
import numpy as np
import requests
from Katna.video import Video
from Katna.writer import KeyFrameDiskWriter
from PIL import Image
import jinja2
from icecream import ic

from utils import check_process_running, encode_image

client = carla.Client("localhost", 2000)

API_KEY = "sk-wneAEhU4CRoiDszaAcD16f7a04704010A34cB98cC2DaEc8a"
BASE_URL = "https://oneapi.xty.app/v1/chat/completions"
jinja_env = jinja2.Environment()

param_examples = []


def draw_overview(carla_client: carla.Client):
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    video_writer = cv2.VideoWriter("overview.avi", fourcc, 20.0, (400, 400))

    def save_video(image):
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        video_writer.write(array)

    world: carla.World = carla_client.get_world()

    camera_bp = world.get_blueprint_library().find("sensor.camera.rgb")
    camera_bp.set_attribute("image_size_x", "400")
    camera_bp.set_attribute("image_size_y", "400")
    camera_bp.set_attribute("fov", "90")
    transform = carla.Transform(
        carla.Location(z=10.0), carla.Rotation(pitch=-90)
    )

    ego = None
    while True:
        try:
            ego = world.get_actors().filter("vehicle.lincoln.mkz_2017")[0]
            break
        except IndexError:
            print("can't find ego vehicle")
            time.sleep(1)

    camera = world.spawn_actor(camera_bp, transform, attach_to=ego)
    camera.listen(save_video)

    while True:
        try:
            world.get_actors().filter("vehicle.lincoln.mkz_2017")[0]
        except IndexError:
            break

    camera.destroy()
    video_writer.release()


def extract_keyframes(video_path: Path, clean_dst: bool = True):
    if clean_dst:
        for file in Path("./keyframes").iterdir():
            file.unlink()
    vd = Video(ordered=True)
    diskwriter = KeyFrameDiskWriter(location="keyframes")
    vd.extract_video_keyframes(
        no_of_frames=9, file_path=str(video_path), writer=diskwriter
    )


def combine_to_grid_image(image_paths: Path):
    image_files = sorted(image_paths.iterdir())
    images = []
    for file in image_files:
        images.append(Image.open(file))

    total_images = len(images)
    grid_cols = math.ceil(math.sqrt(total_images))
    grid_rows = math.ceil(total_images / grid_cols)

    grid_width, grid_height = images[0].size
    grid_image = Image.new(
        mode="RGB",
        size=(grid_width * grid_cols, grid_height * grid_rows),
        color=(255, 255, 255),
    )

    for index, frame in enumerate(images):
        x = index % grid_cols * grid_width
        y = index // grid_cols * grid_height
        grid_image.paste(frame, (x, y))

    return grid_image


def simulate(ego_speed, other_speed, other_gostraight_duration):
    xml_path = "/home/xtayex/Downloads/enhanced_scenario_runner/test_cases_behavior_tree/test.xml"
    tree = ET.parse(xml_path)
    basic_agent_behavior_node = tree.find(".//ego/BasicAgentBehavior")
    keep_velocity_node = tree.find(".//other/Sequence/KeepVelocity")
    basic_agent_behavior_node.attrib["target_speed"] = str(ego_speed)
    keep_velocity_node.attrib["duration"] = str(other_gostraight_duration)
    keep_velocity_node.attrib["target_velocity"] = str(other_speed)
    tree.write(xml_path)

    cmd = (
        "python3 scenario_runner.py --llm LLM_1 --bt-path"
        " /home/xtayex/Downloads/enhanced_scenario_runner/test_cases_behavior_tree/test.xml"
    )

    while True:
        try:
            while not check_process_running("CarlaUE4"):
                print("Carla is not running. We will wait for 1s.")
                time.sleep(1)
            subprocess.Popen(cmd.split(" "))
            draw_overview(carla_client=client)
            extract_keyframes(Path("./overview.avi"), clean_dst=True)
            grid_image = combine_to_grid_image(image_paths=Path("keyframes"))
            Image.Image.save(
                grid_image,
                f"grid/keyframes_grid-{time.strftime('%Y-%m-%d_%H_%M_%S')}.png",
            )
            return grid_image

        except subprocess.CalledProcessError as e:
            print(
                f"Cannot run the scenario due to {e}. We will retry it after"
                " 30s."
            )
            time.sleep(30)


def _ic_output_to_file(debug_log: str):
    with open("ic.log", "a", encoding="utf-8") as log_f:
        log_f.write(f"{debug_log}\n")


def send_request(messages: List[Dict]):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": messages,
        "max_tokens": 500,
    }
    retry_time = 3
    for _ in range(retry_time):
        try:
            response = requests.post(
                BASE_URL, headers=headers, json=payload, timeout=1000
            )
            break
        except requests.exceptions.ConnectionError:
            print("ConnectionError. We will retry it after 1s.")
            time.sleep(1)

    ic.configureOutput(outputFunction=_ic_output_to_file)
    ic(messages)
    ic(response.json())
    response_message = response.json()["choices"][0]["message"]
    return response_message


def has_collision():
    with open("collision_status.txt", "r", encoding="utf-8") as f:
        status = f.read()

    print(status)

    return status == "FAILURE"


def gpt_optimize():
    # startup
    with open(
        "llm_optimizer_startup_prompt.j2", "r", encoding="utf-8"
    ) as startup_prompt_f:
        startup_prompt = startup_prompt_f.read()

    startup_message = [
        {"role": "user", "content": [{"type": "text", "text": startup_prompt}]}
    ]

    response_message = send_request(messages=startup_message)

    response_content = response_message["content"]
    response_content_json = json.loads(response_content)
    startup_ego_speed = response_content_json["speedA"]
    startup_other_speed = response_content_json["speedB"]
    startup_duration = response_content_json["duration"]

    grid_image = simulate(
        startup_ego_speed, startup_other_speed, startup_duration
    )

    # feedback
    with open(
        "llm_optimizer_feedback_prompt.j2", "r", encoding="utf-8"
    ) as feedback_prompt_f:
        feedback_prompt_template = feedback_prompt_f.read()

    feedback_messages = [
        *startup_message,
        {
            "role": "assistant",
            "content": [{"type": "text", "text": response_content}],
        },
    ]
    while True:
        feedback_prompt = jinja_env.from_string(
            feedback_prompt_template
        ).render(
            collision_status="Collision" if has_collision() else "No collision"
        )
        feedback_messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": feedback_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:image/jpeg;base64,{encode_image(grid_image)}"
                            )
                        },
                    },
                ],
            }
        )
        response_message = send_request(messages=feedback_messages)
        response_content = response_message["content"]
        response_content_json = json.loads(response_content)
        feedback_ego_speed = response_content_json["speedA"]
        feedback_other_speed = response_content_json["speedB"]
        feedback_duration = response_content_json["duration"]

        grid_image = simulate(
            feedback_ego_speed, feedback_other_speed, feedback_duration
        )
        feedback_messages.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": response_content}],
            }
        )


def gemini_optimize():
    pass


gpt_optimize()
