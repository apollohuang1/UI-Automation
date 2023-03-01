import os
import cv2
import json
import pandas as pd
from os.path import join as pjoin

from classification.IconClassifier import IconClassifier
from classification.IconCaption import IconCaption

import sys
sys.path.append('classification')


class GUIData:
    def __init__(self, gui_img_file, gui_json_file):
        self.img_file = gui_img_file
        self.json_file = gui_json_file
        self.gui_name = gui_img_file.replace('/', '\\').split('\\')[-1].split('.')[0]

        self.img = cv2.resize(cv2.imread(gui_img_file), (1080, 2280))      # resize the image to be consistent with the vh
        self.json = json.load(open(gui_json_file, 'r', encoding='utf-8'))  # json data, the view hierarchy of the GUI

        self.element_id = 0
        self.elements = []          # list of element in dictionary {'id':, 'class':...}
        self.elements_leaves = []   # leaf nodes that does not have children

        self.model_icon_caption = None   # IconCaption

    '''
    ************************
    *** Extract Elements ***
    ************************
    '''
    def extract_elements_from_vh(self):
        '''
        Extract elements from raw view hierarchy Json file and store them as dictionaries
        '''
        element_root = self.json['activity']['root']
        self.prone_invalid_children(element_root)
        self.extract_children_elements(element_root)

        self.inherit_clickablility()
        self.gather_leaf_elements()

    def extract_children_elements(self, element):
        '''
        Recursively extract children from an element
        '''
        element['id'] = self.element_id
        self.elements.append(element)
        if 'children' in element:
            element['children-id'] = []
            for child in element['children']:
                self.element_id += 1
                element['children-id'].append(self.element_id)
                self.extract_children_elements(child)
            # replace wordy 'children' with 'children-id'
            del element['children']
        if 'ancestors' in element:
            del element['ancestors']

    def prone_invalid_children(self, element):
        '''
        Prone invalid children elements
        Leave valid children and prone their children recursively
        Take invalid children's children as its own directly
        '''
        valid_children = []
        if 'children' in element:
            for child in element['children']:
                if self.check_if_element_valid(child):
                    valid_children.append(child)
                    self.prone_invalid_children(child)
                else:
                    valid_children += self.prone_invalid_children(child)
            element['children'] = valid_children
        return valid_children

    def check_if_element_valid(self, element, min_length=5):
        '''
        Check if the element is valid and should be kept
        '''
        if (element['bounds'][0] >= element['bounds'][2] - min_length or element['bounds'][1] >= element['bounds'][3] - min_length) or \
                ('layout' in element['class'].lower() and not element['clickable']):
            return False
        return True

    '''
    ************************
    *** Elements Process ***
    ************************
    '''
    def inherit_clickablility(self):
        '''
        If a node's parent is clickable, make it clickable
        '''
        for ele in self.elements:
            if ele['clickable'] and 'children-id' in ele:
                for c_id in ele['children-id']:
                    self.elements[c_id - self.elements[0]['id']]['clickable'] = True

    def gather_leaf_elements(self):
        for ele in self.elements:
            if 'children-id' not in ele:
                self.elements_leaves.append(ele)

    def get_caption_for_leaf_captions(self):
        if self.model_icon_caption is None:
            self.model_icon_caption = IconCaption(vocab_path='classification/model_results/vocab_idx2word.json',
                                                  model_path='classification/model_results/labeldroid.pt')
        clips = []
        for ele in self.elements_leaves:
            bound = ele['bounds']
            clips.append(self.img[bound[1]: bound[3], bound[0]:bound[2]])
        captions = self.model_icon_caption.predict_images(clips)
        for ele in self.elements_leaves:
            ele['caption'] = captions

    '''
    *********************
    *** Visualization ***
    *********************
    '''
    def show_each_element(self, only_leaves=False):
        board = self.img.copy()
        if only_leaves:
            elements = self.elements_leaves
            print(len(elements))
        else:
            elements = self.elements
        for ele in elements:
            print(ele['id'], ele['class'])
            print(ele, '\n')
            bounds = ele['bounds']
            clip = self.img[bounds[1]: bounds[3], bounds[0]: bounds[2]]
            color = (0,255,0) if not ele['clickable'] else (0,0,255)
            cv2.rectangle(board, (bounds[0], bounds[1]), (bounds[2], bounds[3]), color, 3)
            cv2.imshow('clip', cv2.resize(clip, (clip.shape[1] // 3, clip.shape[0] // 3)))
            cv2.imshow('ele', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
            if cv2.waitKey() == ord('q'):
                break
        cv2.destroyAllWindows()

    def show_all_elements(self, only_leaves=False):
        board = self.img.copy()
        if only_leaves:
            elements = self.elements_leaves
        else:
            elements = self.elements
        for ele in elements:
            bounds = ele['bounds']
            color = (0,255,0) if not ele['clickable'] else (0,0,255)
            cv2.rectangle(board, (bounds[0], bounds[1]), (bounds[2], bounds[3]), color, 3)
        cv2.imshow('elements', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
        cv2.waitKey()
        cv2.destroyWindow('elements')

    def show_element(self, element):
        board = self.img.copy()
        color = (0,255,0) if not element['clickable'] else (0,0,255)
        bounds = element['bounds']
        cv2.rectangle(board, (bounds[0], bounds[1]), (bounds[2], bounds[3]), color, 3)
        cv2.imshow('element', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
        cv2.waitKey()
        cv2.destroyWindow('element')

    def show_screen(self):
        cv2.imshow('screen', self.img)
        cv2.waitKey()
        cv2.destroyWindow('screen')


if __name__ == '__main__':
    gui = GUIData('data/emulator-5554.png', 'data/emulator-5554.json')
    gui.extract_elements_from_vh()
    gui.show_all_elements()
    gui.inherit_clickablility()
    gui.show_all_elements()
