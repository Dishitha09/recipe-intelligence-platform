import json
import os
from datetime import datetime


def save_raw_record(data, source_type):

    folder = f"data/raw/{source_type}"

    os.makedirs(folder, exist_ok=True)


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")


    file_path = f"{folder}/{timestamp}.json"


    with open(file_path, "w", encoding="utf-8") as f:

        json.dump(

            data,

            f,

            indent=4,

            ensure_ascii=False

        )


    return file_path