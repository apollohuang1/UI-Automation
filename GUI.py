import time
from os.path import join as pjoin
import cv2
import json
time.clock = time.time

from detection.Detector import Detector
from classification.IconClassifier import IconClassifier
from Element import Element


class GUI:
    def __init__(self, img_file, output_dir='data/output', img_resize_longest_side=800):
        self.img_file = img_file
        self.img = cv2.imread(img_file)
        self.file_name = img_file.replace('\\', '/').split('/')[-1][:-4]
        self.output_dir = output_dir

        self.Detector = Detector(self.img_file, img_resize_longest_side, self.output_dir)            # GUI Element Detection
        self.Classifier = None

        self.img_reshape = self.Detector.img_reshape  # image reshape for element detection
        self.img_resized = self.Detector.img_resized  # resized image by img_reshape

        self.elements = []  # list of Element objects
        self.color_map = {'Compo': (0,255,0), 'Text':(0,0,255),  # element class
                          'Text Button':(0,0,255), 'Input':(166,0,0), 'Switch':(166,166,0), 'Image':(0,166,166), 'Icon':(255,255,0), 'Checkbox':(255,0,166)}  # compo class

        self.detection_result_img = {'text': None, 'non-text': None, 'merge': None}     # visualized detection result

    '''
    *****************************
    *** GUI Element Detection ***
    *****************************
    '''
    def detect_element(self, is_ocr=True, is_non_text=True, is_merge=True, show=True):
        self.Detector.detect_element(is_ocr, is_non_text, is_merge)
        self.cvt_elements()
        if show:
            self.show_element_detection()

    def load_detection_result(self):
        self.Detector.load_detection_result()
        self.cvt_elements()

    def cvt_elements(self):
        '''
        Convert detection result to Element objects
        '''
        compos = self.Detector.compos_json['compos']
        for compo in compos:
            pos = compo['position']
            element = Element(compo['id'], pos['column_min'], pos['row_min'], pos['column_max'], pos['row_max'])
            element.attributes.element_class = compo['class']
            element.get_clip(self.img_resized)
            self.elements.append(element)

    '''
    **********************************
    *** GUI Element Classification ***
    **********************************
    '''
    def classify_compo(self):
        '''
        Classify non-text element's compo_class: ['Text Button', 'Input', 'Switch', 'Image', 'Icon', 'Checkbox']
        :saveto: element.attributes.compo_class
        '''
        self.Classifier = IconClassifier(model_path='classification/model/best-0.93.pt',
                                         class_path='classification/model/iconModel_labels.json')
        compos = []
        for ele in self.elements:
            if ele.attributes.element_class == 'Compo':
                compos.append(ele)
        compos_clips = [compo.clip for compo in compos]
        labels = self.Classifier.predict_images(compos_clips)
        for i, compo in enumerate(compos):
            compo.attributes.compo_class = labels[i][0]

    '''
    *********************
    *** Visualization ***
    *********************
    '''
    def show_element_detection(self):
        self.Detector.visualize_element_detection()

    def show_elements(self):
        board = self.img_resized.copy()
        for element in self.elements:
            element.draw_element(board, self.color_map[element.attributes.element_class])
        cv2.imshow('elements', board)
        cv2.waitKey()
        cv2.destroyWindow('elements')

    def show_element_classes(self):
        board_ele_class = self.img_resized.copy()
        board_compo_class = self.img_resized.copy()
        for element in self.elements:
            element.draw_element(board_ele_class, self.color_map[element.attributes.element_class], text=element.attributes.element_class)
            if element.attributes.compo_class is not None:
                element.draw_element(board_compo_class, self.color_map['Compo'], text=element.attributes.compo_class)
        cv2.imshow('element class', board_ele_class)
        cv2.imshow('compo class', board_compo_class)
        cv2.waitKey()
        cv2.destroyAllWindows()
