from pathlib import Path
import math
import subprocess
from typing import List

from PIL import Image

def concat_to_grid(keyframes: List[Image.Image]):
    """concat several keyframes to a grid image.
    Columns and rows count are determined by the 
    number of keyframes smartly."""
    
    total_images = len(keyframes)
    grid_cols = math.ceil(math.sqrt(total_images))
    grid_rows = math.ceil(total_images / grid_cols)
    
    grid_width, grid_height = keyframes[0].size
    grid_image = Image.new(
        mode="RGB",
        size=(grid_width * grid_cols, grid_height * grid_rows),
        color=(255, 255, 255),
    )
    
    for index, frame in enumerate(keyframes):
        x = index % grid_cols * grid_width
        y = index // grid_cols * grid_height
        grid_image.paste(frame, (x, y))
    
    return grid_image


keyframe_path = Path("keyframes")
subprocess.run(["rm", "-rf", "./grid/*"], check=True)
keyframes = []
keyframe_files = sorted(keyframe_path.iterdir())

for keyframe_file in keyframe_files:
    keyframes.append(Image.open(keyframe_file))

Image.Image.save(concat_to_grid(keyframes), "grid/keyframes_grid.png")
