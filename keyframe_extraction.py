from Katna.video import Video
from Katna.writer import KeyFrameDiskWriter

vd = Video(ordered=True)
diskwriter = KeyFrameDiskWriter(location="keyframes")
vd.extract_video_keyframes(no_of_frames=9, file_path="./output.avi", writer=diskwriter)
