import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS  # temp folder used by PyInstaller
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
