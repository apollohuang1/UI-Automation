import time
from os.path import join as pjoin
import cv2
import json

from detection.Detector import Detector
from grouping.Grouper import Grouper
from classification.Classifier import Classifier
from Element import Element


class GUI:
    def __init__(self, img_file, output_dir='data/output', img_resize_longest_side=800):
        self.img_file = img_file
        self.img = cv2.imread(img_file)
        self.file_name = img_file.replace('\\', '/').split('/')[-1][:-4]
        self.output_dir = output_dir

        self.Detector = Detector(self.img_file, img_resize_longest_side, self.output_dir)            # GUI Element Detection
        self.Grouper = Grouper(self.img_file, self.Detector.detection_result_file, self.output_dir)  # GUI Element Grouping (Layout)
        self.Classifier = Classifier()

        self.img_reshape = self.Detector.img_reshape  # image reshape for element detection
        self.img_resized = self.Detector.img_resized  # resized image by img_reshape

        self.elements = []  # list of Element objects
        self.color_map = {'Compo': (0,255,0), 'Text':(0,0,255),  # element class
                          'Text Button':(0,0,255), 'Input':(166,0,0), 'Switch':(166,166,0), 'Image':(0,166,166), 'Icon':(255,255,0), 'Checkbox':(255,0,166)}  # compo class

        self.detection_result_img = {'text': None, 'non-text': None, 'merge': None}     # visualized detection result
        self.grouping_result_img = {'group': None, 'pair': None, 'list': None}          # visualized detection result

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
    def classify_element(self, compo_class=True, icon_class=True, image_class=True):
        self.Classifier.load_classifiers(compo=compo_class, icon=icon_class, img=image_class)
        if compo_class:
            self.classify_compo_class()
        if icon_class:
            self.classify_icon_class()
        if image_class:
            self.classify_img_class()

    def classify_compo_class(self):
        '''
        Classify non-text element's compo_class: ['Text Button', 'Input', 'Switch', 'Image', 'Icon', 'Checkbox']
        :saveto: element.attributes.compo_class
        '''
        compos = []
        for ele in self.elements:
            if ele.attributes.element_class == 'Compo':
                compos.append(ele)
        compos_clips = [compo.clip for compo in compos]
        labels = self.Classifier.predict_images(compos_clips, opt='compo')
        for i, compo in enumerate(compos):
            compo.attributes.compo_class = labels[i]

    def classify_icon_class(self):
        '''
        Classify icon element's icon_class: [99 classes]
        :saveto: element.attributes.icon_class
        '''
        icons = []
        for ele in self.elements:
            if ele.attributes.compo_class == 'Icon':
                icons.append(ele)
        icons_clips = [icon.clip for icon in icons]
        labels = self.Classifier.predict_images(icons_clips, opt='icon')
        for i, icon in enumerate(icons):
            icon.attributes.icon_class = labels[i]

    def classify_img_class(self):
        '''
        Classify image element's icon_class: [imageNet 1k classes]
        :saveto: element.attributes.image_class
        '''
        imgs = []
        for ele in self.elements:
            if ele.attributes.compo_class == 'Image':
                imgs.append(ele)
        imgs_clips = [img.clip for img in imgs]
        labels = self.Classifier.predict_images(imgs_clips, opt='image')
        for i, img in enumerate(imgs):
            img.attributes.image_class = labels[i]

    '''
    **************************
    *** Layout Recognition ***
    **************************
    '''
    # entry method
    def recognize_layout(self, show=True):
        # self.Grouper.load_detection_result_from_file()
        self.Grouper.load_compos(self.Detector.compos_json)
        self.Grouper.recognize_layout()
        if show:
            self.show_layout_recognition()

    '''
    *********************
    *** Visualization ***
    *********************
    '''
    def show_element_detection(self):
        self.Detector.visualize_element_detection()

    def show_layout_recognition(self):
        self.Grouper.visualize_layout_recognition()

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
        board_icon_class = self.img_resized.copy()
        board_img_class = self.img_resized.copy()

        for element in self.elements:
            element.draw_element(board_ele_class, self.color_map[element.attributes.element_class], text=element.attributes.element_class)
            if element.attributes.compo_class is not None:
                element.draw_element(board_compo_class, self.color_map[element.attributes.compo_class], text=element.attributes.compo_class)
            if element.attributes.icon_class is not None:
                element.draw_element(board_icon_class, self.color_map['Icon'], text=element.attributes.icon_class)
            if element.attributes.image_class is not None:
                element.draw_element(board_img_class, self.color_map['Image'], text=element.attributes.image_class)

        cv2.imshow('element class', board_ele_class)
        cv2.imshow('compo class', board_compo_class)
        cv2.imshow('icon class', board_icon_class)
        cv2.imshow('image class', board_img_class)
        cv2.waitKey()
        cv2.destroyAllWindows()
