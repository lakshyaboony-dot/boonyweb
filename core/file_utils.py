import os

def get_next_recording_path(base_dir, prefix):
    os.makedirs(base_dir, exist_ok=True)
    index = 1
    while os.path.exists(os.path.join(base_dir, f"{prefix}_{index}.wav")):
        index += 1
    return os.path.join(base_dir, f"{prefix}_{index}.wav")
