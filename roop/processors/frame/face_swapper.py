from typing import Any, List, Callable
import cv2
import insightface
import threading
import requests
import os
import time

import roop.globals
import roop.processors.frame.core
from roop.core import update_status
from roop.face_analyser import get_one_face, get_many_faces
from roop.typing import Face, Frame
from roop.utilities import conditional_download, resolve_relative_path, is_image, is_video

FACE_SWAPPER = None
THREAD_LOCK = threading.Lock()
NAME = 'ROOP.FACE-SWAPPER'


def get_face_swapper() -> Any:
    global FACE_SWAPPER

    with THREAD_LOCK:
        if FACE_SWAPPER is None:
            
            model_path = resolve_relative_path('../inswapper_128.onnx')
            found = os.path.exists(model_path)
            print("La ruta se encontró:", found)
            time.sleep(4)

            if found is True: 
                print("Es verdad que la ruta si se encontró...")
            else:
                print("La ruta no se encontró por cierto...")
                time.sleep(5)
                print("Lo bajaré remotamente...")
                #Ésta es la forma de bajarlo si no se encuentra en su ruta.
                url = "https://huggingface.co/countfloyd/deepfake/resolve/main/inswapper_128.onnx"
                response = requests.get(url)
                content = response.content
                path = "inswapper_128.onnx"
                with open(path, "wb") as f:
                    f.write(content)
                model_path = os.path.join(os.getcwd(), path)

            #También Probar cuando esté arriba en huggingface, si con la ruta relativa llega. 
  

            FACE_SWAPPER = insightface.model_zoo.get_model(model_path, providers=roop.globals.execution_providers)

    return FACE_SWAPPER


def pre_check() -> bool:
    download_directory_path = resolve_relative_path('../content/roop')
    #Al parecer ésto no se usa.
    conditional_download(download_directory_path, ['https://huggingface.co/countfloyd/deepfake/resolve/main/inswapper_128.onnx'])
    return True


def pre_start() -> bool:
    if not is_image(roop.globals.source_path):
        update_status('Select an image for source path.', NAME)
        return False
    elif not get_one_face(cv2.imread(roop.globals.source_path)):
        update_status('No face in source path detected.', NAME)
        return False
    if not is_image(roop.globals.target_path) and not is_video(roop.globals.target_path):
        update_status('Select an image or video for target path.', NAME)
        return False
    return True


def post_process() -> None:
    global FACE_SWAPPER

    FACE_SWAPPER = None


def swap_face(source_face: Face, target_face: Face, temp_frame: Frame) -> Frame:
    return get_face_swapper().get(temp_frame, target_face, source_face, paste_back=True)


def process_frame(source_face: Face, temp_frame: Frame) -> Frame:
    if roop.globals.many_faces:
        if many_faces := get_many_faces(temp_frame):
            for target_face in many_faces:
                temp_frame = swap_face(source_face, target_face, temp_frame)
    elif target_face := get_one_face(temp_frame):
        temp_frame = swap_face(source_face, target_face, temp_frame)
    return temp_frame


def process_frames(source_path: str, temp_frame_paths: List[str], update: Callable[[], None]) -> None:
    source_face = get_one_face(cv2.imread(source_path))
    for temp_frame_path in temp_frame_paths:
        temp_frame = cv2.imread(temp_frame_path)
        result = process_frame(source_face, temp_frame)
        cv2.imwrite(temp_frame_path, result)
        if update:
            update()


def process_image(source_path: str, target_path: str, output_path: str) -> None:
    source_face = get_one_face(cv2.imread(source_path))
    target_frame = cv2.imread(target_path)
    result = process_frame(source_face, target_frame)
    cv2.imwrite(output_path, result)


def process_video(source_path: str, temp_frame_paths: List[str]) -> None:
    roop.processors.frame.core.process_video(source_path, temp_frame_paths, process_frames)
