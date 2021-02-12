import os
import cv2
import json
import copy
from src.layout import Layout


def main():
    file_path = './data/data.json'
    with open(file_path, 'r', encoding='utf8')as fp:
        description = json.load(fp)
    Layout(description)
    pass


if __name__ == "__main__":
    main()
