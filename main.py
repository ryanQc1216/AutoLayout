import os
import cv2
import json
import copy
from src.layout import Layout
import numpy as np

config_dict = {
    'ratio_standard': 3/4,
    'max_cols_contains': 4
}

def get_file_name(file_path):
    index = file_path.rfind('/')
    return file_path[index+1:]

def main():

    file_path = './data/test_1.json'
    out_path = './out/'
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    with open(file_path, 'r', encoding='utf8')as fp:
        description = json.load(fp)

    ins_layout = Layout(description, config_dict)
    image = ins_layout.render()

    filename = get_file_name(file_path)
    save_path = out_path + filename.replace('json', 'jpg')
    cv2.imshow('canvas', image)
    cv2.imwrite(save_path, image)
    cv2.waitKey(0)

    pass


if __name__ == "__main__":
    main()
