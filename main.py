import os
import cv2
import json
import copy
from src.layout import Layout
import numpy as np

def main():

    file_path = './data/test_1.json'
    with open(file_path, 'r', encoding='utf8')as fp:
        description = json.load(fp)
    Layout(description)
    pass


if __name__ == "__main__":
    main()
