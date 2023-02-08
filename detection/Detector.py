import cv2
import os
from os.path import join as pjoin
import json

import detection.detect_text.text_detection as text
import detection.detect_compo.ip_region_proposal as ip
import detection.detect_merge.merge as merge
import grouping.lib.draw as draw


class Detector:
    def __init__(self, img_file, img_resize_longest_side=800, output_dir='data/output'):
        self.img_file = img_file
        self.img_org = cv2.imread(img_file)
        self.img_reshape = self.resize_by_longest_side(img_resize_longest_side=img_resize_longest_side)
        self.img_resized = cv2.resize(self.img_org, (self.img_reshape[1], self.img_reshape[0]))
        self.file_name = img_file.replace('\\', '/').split('/')[-1][:-4]

        self.output_dir = output_dir
        self.ocr_dir = pjoin(self.output_dir, 'ocr')
        self.non_text_dir = pjoin(self.output_dir, 'ip')
        self.merge_dir = pjoin(self.output_dir, 'uied')
        self.detection_result_file = pjoin(self.merge_dir, self.file_name + '.json')

        self.detection_result_img = {'text': None, 'non-text': None, 'merge': None}  # visualized detection result
        self.compos_json = None  # {'img_shape':(), 'compos':[]}, detection result

        self.key_params = {'min-grad': 10, 'ffl-block': 5, 'min-ele-area': 50, 'merge-contained-ele': True,
                           'max-word-inline-gap': 10, 'max-line-ingraph-gap': 4, 'remove-ui-bar': True}

    def resize_by_longest_side(self, img_resize_longest_side=800):
        height, width = self.img_org.shape[:2]
        if height > width:
            width_re = int(img_resize_longest_side * (width / height))
            return img_resize_longest_side, width_re, self.img_org.shape[2]
        else:
            height_re = int(img_resize_longest_side * (height / width))
            return height_re, img_resize_longest_side, self.img_org.shape[2]

    '''
    *****************************
    *** GUI Element Detection ***
    *****************************
    '''
    def detect_element(self, is_ocr=True, is_non_text=True, is_merge=True, show=False):
        if is_ocr:
            self.detection_result_img['text'] = text.text_detection(self.img_file, self.ocr_dir, show=show)
        elif os.path.isfile(pjoin(self.ocr_dir, self.file_name + '.jpg')):
            self.detection_result_img['text'] = cv2.imread(pjoin(self.ocr_dir, self.file_name + '.jpg'))

        if is_non_text:
            self.detection_result_img['non-text'] = ip.compo_detection(self.img_file, self.non_text_dir, self.key_params, resize_by_height=self.img_reshape[0], show=show)
        elif os.path.isfile(pjoin(self.non_text_dir, self.file_name + '.jpg')):
            self.detection_result_img['non-text'] = cv2.imread(pjoin(self.non_text_dir, self.file_name + '.jpg'))

        if is_merge:
            os.makedirs(self.merge_dir, exist_ok=True)
            compo_path = pjoin(self.non_text_dir, self.file_name + '.json')
            ocr_path = pjoin(self.ocr_dir, self.file_name + '.json')
            self.detection_result_img['merge'], self.compos_json = merge.merge(self.img_file, compo_path, ocr_path, self.merge_dir, is_remove_bar=True, is_paragraph=True, show=show)

    def load_detection_result(self):
        '''
        Load json detection result from json file
        '''
        self.compos_json = json.load(open(self.detection_result_file))
        self.img_reshape = self.compos_json['img_shape']
        self.img_resized = cv2.resize(self.img_org, (self.img_reshape[1], self.img_reshape[0]))
        self.draw_element_detection()

    '''
    *********************
    *** Visualization ***
    *********************
    '''
    def draw_element_detection(self, line=2):
        board_text = self.img_resized.copy()
        board_nontext = self.img_resized.copy()
        board_all = self.img_resized.copy()
        colors = {'Text': (0, 0, 255), 'Compo': (0, 255, 0), 'Block': (0, 166, 166)}
        for compo in self.compos_json['compos']:
            position = compo['position']
            if compo['class'] == 'Text':
                draw.draw_label(board_text, [position['column_min'], position['row_min'], position['column_max'], position['row_max']], colors[compo['class']], line=line)
            else:
                draw.draw_label(board_nontext, [position['column_min'], position['row_min'], position['column_max'], position['row_max']], colors[compo['class']], line=line)
            draw.draw_label(board_all, [position['column_min'], position['row_min'], position['column_max'], position['row_max']], colors[compo['class']], line=line)
        self.detection_result_img['text'] = board_text
        self.detection_result_img['non-text'] = board_nontext
        self.detection_result_img['merge'] = board_all

    def visualize_element_detection(self):
        cv2.imshow('text', cv2.resize(self.detection_result_img['text'], (500, 800)))
        cv2.imshow('non-text', cv2.resize(self.detection_result_img['non-text'], (500, 800)))
        cv2.imshow('merge', cv2.resize(self.detection_result_img['merge'], (500, 800)))
        cv2.waitKey()
        cv2.destroyAllWindows()

