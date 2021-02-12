import os
import cv2
import json
import copy
from src.layout import Layout
import numpy as np

# def test_text_size():
#     image = np.zeros((480, 640, 3))
#     text_size, baseline = cv2.getTextSize('0000', fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=0.6, thickness=1)
#     text_width = text_size[0]
#     text_height = text_size[1]
#
#
#
#     cv2.
#
#     cv2.imshow('image', image)
#     cv2.waitKey(0)

def main():

    file_path = './data/data.json'
    with open(file_path, 'r', encoding='utf8')as fp:
        description = json.load(fp)
    Layout(description)
    pass


if __name__ == "__main__":
    main()
