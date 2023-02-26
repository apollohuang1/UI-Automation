import time
from os.path import join as pjoin
import cv2
import json
time.clock = time.time

from detection.Detector import Detector
from classification.IconClassifier import IconClassifier


class ElementAttributes:
    def __init__(self):
        self.element_class = None   # ['Compo', 'Text']
        # for non-text
        self.compo_class = None     # ['Text Button', 'Input', 'Switch', 'Image', 'Icon', 'Checkbox']
        self.icon_class = None      # [99 classes]
        self.image_class = None     # [imageNet 1k classes]
        self.clickable = False      # Boolean
        # for text
        self.text_content = None    # Text content
        self.text_ner = None        # NER ['Name', 'Date', 'Time', 'Location']
        self.text_bold = False      # Boolean


class BoundingBox:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.width = right - left
        self.height = bottom - top
        self.area = self.width * self.height


class Element:
    def __init__(self, id, left, top, right, bottom):
        self.id = id
        self.attributes = ElementAttributes()
        self.bounding = BoundingBox(left, top, right, bottom)
        self.clip = None

    def get_clip(self, img):
        self.clip = img[self.bounding.top: self.bounding.bottom, self.bounding.left: self.bounding.right]

    def draw_element(self, img, color, text=None, show=False):
        cv2.rectangle(img, (self.bounding.left, self.bounding.top), (self.bounding.right, self.bounding.bottom), color, 2)
        if text is not None:
            cv2.putText(img, text, (self.bounding.left+5, self.bounding.top+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        if show:
            cv2.imshow('element', img)
            cv2.waitKey()
            cv2.destroyWindow('element')


class GUI:
    def __init__(self, img_file, output_dir='data/output', img_resize_longest_side=800):
        self.img_file = img_file
        self.img = cv2.imread(img_file)
        self.file_name = img_file.replace('\\', '/').split('/')[-1][:-4]
        self.output_dir = output_dir
        self.color_map = {'Compo': (0,255,0), 'Text':(0,0,255),  # element class
                          'Text Button':(0,0,255), 'Input':(166,0,0), 'Switch':(166,166,0), 'Image':(0,166,166), 'Icon':(255,255,0), 'Checkbox':(255,0,166)}  # compo class

        self.Detector = Detector(self.img_file, img_resize_longest_side, self.output_dir)            # GUI Element Detection
        self.Classifier = IconClassifier(model_path='classification/model_results/best-0.93.pt',
                                         class_path='classification/model_results/iconModel_labels.json')
        self.img_reshape = self.Detector.img_reshape  # image reshape for element detection
        self.img_resized = self.Detector.img_resized  # resized image by img_reshape

        self.elements = []  # list of Element objects
        self.color_map = {'Compo': (0,255,0), 'Text':(0,0,255), 'Block':(166,166,0), # element class
                          'Text Button':(0,0,255), 'Input':(166,0,0), 'Switch':(166,166,0), 'Image':(0,166,166), 'Icon':(255,255,0), 'Checkbox':(255,0,166)}  # compo class

        self.detection_result_img = {'text': None, 'non-text': None, 'merge': None}     # visualized detection result
        self.elements = []  # list of Element objects

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
            if compo['class'] == 'Text':
                element.attributes.text_content = compo['text_content']
            element.get_clip(self.img_resized)
            self.elements.append(element)

    '''
    *********************************
    *** GUI Element Understanding ***
    *********************************
    '''
    def classify_compo(self):
        '''
        Classify non-text element's compo_class: ['Text Button', 'Input', 'Switch', 'Image', 'Icon', 'Checkbox']
        :saveto: element.attributes.compo_class
        '''
        self.Classifier = IconClassifier(model_path='classification/model_results/best-0.93.pt',
                                         class_path='classification/model_results/iconModel_labels.json')
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


if __name__ == '__main__':
    gui = GUI('data/input/11.jpg')
    gui.detect_element()
    gui.show_elements()
    gui.classify_compo()
    gui.show_element_classes()