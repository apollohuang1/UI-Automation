import os
import cv2
import json
import pandas as pd
from os.path import join as pjoin
import copy

from classification.IconClassifier import IconClassifier
from classification.IconCaption import IconCaption

import sys
import warnings
sys.path.append('classification')
warnings.filterwarnings("ignore", category=Warning)


class GUIData:
    def __init__(self, gui_img_file, gui_json_file, output_file_root='data/twitter/testcase1'):
        self.img_file = gui_img_file
        self.json_file = gui_json_file
        self.gui_name = gui_img_file.replace('/', '\\').split('\\')[-1].split('.')[0]

        self.img = cv2.resize(cv2.imread(gui_img_file), (1080, 2280))      # resize the image to be consistent with the vh
        self.json = json.load(open(gui_json_file, 'r', encoding='utf-8'))  # json data, the view hierarchy of the GUI

        self.element_id = 0
        self.elements = []          # list of element in dictionary {'id':, 'class':...}
        self.elements_leaves = []   # leaf nodes that does not have children
        self.element_tree = None    # structural element tree, dict type
        self.blocks = []            # list of blocks from element tree
        self.removed_node_no = 0    # for the record of the number of removed nodes

        self.model_icon_caption = None   # IconCaption
        self.model_icon_classification = None  # IconClassification

        # output file paths
        self.output_dir = pjoin(output_file_root, 'guidata')
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file_path_elements = pjoin(self.output_dir, self.gui_name + '_elements.json')
        self.output_file_path_element_tree = pjoin(self.output_dir, self.gui_name + '_tree.json')

    def load_elements(self, file_path_elements=None, file_path_element_tree=None):
        if not file_path_elements: file_path_elements = self.output_file_path_elements
        if not file_path_element_tree: file_path_element_tree = self.output_file_path_element_tree

        print('Load elements from', file_path_elements)
        self.elements = json.load(open(file_path_elements, 'r', encoding='utf-8'))           # => self.elements
        self.gather_leaf_elements()                     # => self.elements_leaves
        self.element_id = self.elements[-1]['id'] + 1         # => self.element_id
        print('Load element tree from', file_path_element_tree)
        self.element_tree = json.load(open(file_path_element_tree, 'r', encoding='utf-8'))   # => self.element_tree
        self.partition_blocks()     # => self.blocks

    '''
    **************************
    *** UI Info Extraction ***
    **************************
    '''
    def ui_info_extraction(self):
        '''
        Extract elements from raw view hierarchy Json file and store them as dictionaries
        => self.elements; self.elements_leaves
        '''
        json_cp = copy.deepcopy(self.json)
        element_root = json_cp['activity']['root']
        element_root['class'] = 'root'
        # clean up the json tree to remove redundant layout node
        self.prone_invalid_children(element_root)
        self.remove_redundant_nesting(element_root)
        self.merge_element_with_single_leaf_child(element_root)
        self.extract_children_elements(element_root, 0)
        self.gather_leaf_elements()
        json.dump(self.elements, open(self.output_file_path_elements, 'w', encoding='utf-8'), indent=4)
        print('Save elements to', self.output_file_path_elements)

    def prone_invalid_children(self, element):
        '''
        Prone invalid children elements
        Leave valid children and prone their children recursively
        Take invalid children's children as its own directly
        '''
        def check_if_element_valid(ele, min_length=5):
            '''
            Check if the element is valid and should be kept
            '''
            if (ele['bounds'][0] >= ele['bounds'][2] - min_length or ele['bounds'][1] >= ele['bounds'][
                3] - min_length) or \
                    ('layout' in ele['class'].lower() and not ele['clickable']):
                return False
            return True

        valid_children = []
        if 'children' in element:
            for child in element['children']:
                if check_if_element_valid(child):
                    valid_children.append(child)
                    self.prone_invalid_children(child)
                else:
                    valid_children += self.prone_invalid_children(child)
                    self.removed_node_no += 1
            element['children'] = valid_children
        return valid_children

    def remove_redundant_nesting(self, element):
        '''
        Remove redundant parent node whose bounds are same
        '''
        if 'children' in element and len(element['children']) > 0:
            redundant = False
            new_children = []
            for child in element['children']:
                # inherit clickability
                if element['clickable']:
                    child['clickable'] = True
                # recursively inspect child node
                new_children += self.remove_redundant_nesting(child)
                if child['bounds'] == element['bounds']:
                    redundant = True
            # only return the children if the node is redundany
            if redundant:
                self.removed_node_no += 1
                return new_children
            else:
                element['children'] = new_children
        return [element]

    def merge_element_with_single_leaf_child(self, element):
        '''
        Keep the resource-id and class and clickable of the child element
        '''
        if 'children' in element:
            if len(element['children']) == 1 and 'children' not in element['children'][0]:
                child = element['children'][0]
                element['resource-id'] = child['resource-id']
                element['class'] = child['class']
                element['clickable'] = child['clickable']
                self.removed_node_no += 1
                del element['children']
            else:
                new_children = []
                for child in element['children']:
                    new_children.append(self.merge_element_with_single_leaf_child(child))
                element['children'] = new_children
        return element

    def extract_children_elements(self, element, layer):
        '''
        Recursively extract children from an element
        '''
        element['id'] = self.element_id
        element['layer'] = layer
        self.elements.append(element)
        children_depth = layer  # record the depth of the children
        if 'children' in element and len(element['children']) > 0:
            element['children-id'] = []
            for child in element['children']:
                self.element_id += 1
                element['children-id'].append(self.element_id)
                children_depth = max(children_depth, self.extract_children_elements(child, layer+1))
            element['children-depth'] = children_depth
            # replace wordy 'children' with 'children-id'
            del element['children']
        if 'ancestors' in element:
            del element['ancestors']
        return children_depth

    def gather_leaf_elements(self):
        i = 0
        for ele in self.elements:
            if 'children-id' not in ele:
                ele['leaf-id'] = i
                self.elements_leaves.append(ele)
                i += 1

    '''
    *******************
    *** UI Analysis ***
    *******************
    '''
    def ui_analysis_elements_description(self):
        '''
        Extract description for UI elements through 'text', 'content-desc', 'classification' and 'caption'
        => element['description']
        '''
        # generate caption for non-text elements
        self.caption_elements()
        # classify non-text elements
        self.classify_elements()
        # extract element description from 'text', 'content-desc', 'icon-cls' and 'caption'
        for ele in self.elements_leaves:
            description = ''
            # check text
            if len(ele['text']) > 0:
                description += ele['text']
            # check content description
            if 'content-desc' in ele and len(ele['content-desc']) > 0 and ele['content-desc'] != ele['text']:
                description = ele['content-desc'] if len(description) == 0 else description + ' / ' + ele['content-desc']
            # if no text and content description, check caption
            if len(description) == 0:
                if ele['icon-cls']:
                    description = ele['icon-cls']
                else:
                    description = ele['caption'] if '<unk>' not in ele['caption'] else None
            ele['description'] = description
        # save the elements with 'description' attribute
        json.dump(self.elements, open(self.output_file_path_elements, 'w', encoding='utf-8'), indent=4)
        print('Save elements to', self.output_file_path_elements)

    def caption_elements(self, elements=None):
        if self.model_icon_caption is None:
            self.model_icon_caption = IconCaption(vocab_path='classification/model_results/vocab_idx2word.json',
                                                  model_path='classification/model_results/labeldroid.pt')
        elements = self.elements_leaves if elements is None else elements
        clips = []
        for ele in elements:
            bound = ele['bounds']
            clips.append(self.img[bound[1]: bound[3], bound[0]:bound[2]])
        captions = self.model_icon_caption.predict_images(clips)
        for i, ele in enumerate(elements):
            ele['caption'] = captions[i]

    def classify_elements(self, elements=None):
        if self.model_icon_classification is None:
            self.model_icon_classification = IconClassifier(model_path='classification/model_results/best-0.93.pt',
                                                            class_path='classification/model_results/iconModel_labels.json')
        elements = self.elements_leaves if elements is None else elements
        clips = []
        for ele in elements:
            bound = ele['bounds']
            clips.append(self.img[bound[1]: bound[3], bound[0]:bound[2]])
        classes = self.model_icon_classification.predict_images(clips)
        for i, ele in enumerate(elements):
            if classes[i][1] > 0.95:
                ele['icon-cls'] = classes[i][0]
            else:
                ele['icon-cls'] = None

    '''
    ***********************
    *** Structural Tree ***
    ***********************
    '''
    def ui_element_block_tree(self):
        '''
        Form a hierarchical element tree with a few key attributes to represent the vh
        => self.element_tree
        => self.blocks
        '''
        self.element_tree = self.combine_children(self.elements[0])
        self.partition_blocks()
        json.dump(self.element_tree, open(self.output_file_path_element_tree, 'w'), indent=4)
        print('Save element tree to', self.output_file_path_element_tree)

    def combine_children(self, element):
        element_cp = copy.deepcopy(element)
        if 'children-id' in element_cp:
            element_cp['children'] = []
            for c_id in element_cp['children-id']:
                element_cp['children'].append(self.combine_children(self.elements[c_id]))
        # self.select_ele_attr(element_cp, ['id', 'text', 'resource-id', 'class', 'content-desc', 'clickable', 'scrollable', 'children', 'description'])
        self.select_ele_attr(element_cp, ['id', 'resource-id', 'class', 'clickable', 'children', 'description', 'layer'])
        self.revise_ele_attr(element_cp)
        return element_cp

    def select_ele_attr(self, element, selected_attrs):
        element_cp = copy.deepcopy(element)
        for key in element_cp.keys():
            if key not in selected_attrs or element[key] is None or element[key] == '':
                del(element[key])

    def revise_ele_attr(self, element):
        if 'resource-id' in element:
            element['resource-id'] = element['resource-id'].replace('com', '')
            element['resource-id'] = element['resource-id'].replace('android', '')
            element['resource-id'] = element['resource-id'].replace('..', '.')
            element['resource-id'] = element['resource-id'].replace('.:', ':')
        if 'class' in element:
            element['class'] = element['class'].replace('android', '')
            element['class'] = element['class'].replace('..', '.')
            element['class'] = element['class'].replace('.:', ':')

    def partition_blocks(self):
        '''
        Partition the UI into several blocks
        => self.blocks
        '''
        l1_children = self.element_tree['children']
        deeper = False
        for child in l1_children:
            desc = ''
            if 'class' in child:
                desc += child['class'].lower()
            if 'resource-id' in child:
                desc += child['resource-id'].lower()
            if 'description' in child:
                desc += child['description'].lower()
            # if there is a background in the first level of root children, go deeper
            if 'background' in desc and 'children' not in child:
                deeper = True
            else:
                self.blocks.append(child)
        if deeper:
            l2_blocks = []
            for block in self.blocks:
                if 'children' in block:
                    l2_blocks += block['children']
                else:
                    if block['bounds'][2] - block['bounds'][0] > 20 and block['bounds'][3] - block['bounds'][1] > 20:
                        l2_blocks.append(block)
            self.blocks = l2_blocks

    def flatten_block_to_elements(self, block):
        block_cp = copy.deepcopy(block)
        elements = []
        nodes = [block_cp]
        while len(nodes) > 0:
            cur_node = nodes.pop()
            elements.append(cur_node)
            if 'children' not in cur_node:
                continue
            nodes += cur_node['children']
            del(cur_node['children'])
        return elements

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
            print(ele['class'])
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

    def show_element(self, element, show_children=True):
        board = self.img.copy()
        color = (0,255,0) if not element['clickable'] else (0,0,255)
        bounds = element['bounds']
        cv2.rectangle(board, (bounds[0], bounds[1]), (bounds[2], bounds[3]), color, 3)
        if show_children and 'children-id' in element:
            for c_id in element['children-id']:
                bounds = self.elements[c_id]['bounds']
                cv2.rectangle(board, (bounds[0], bounds[1]), (bounds[2], bounds[3]), (255,0,255), 3)
        cv2.imshow('element', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
        cv2.waitKey()
        cv2.destroyWindow('element')

    def show_element_by_id(self, ele_id, show_children=True):
        element = self.elements[ele_id]
        self.show_element(element, show_children)

    def show_screen(self):
        cv2.imshow('screen', self.img)
        cv2.waitKey()
        cv2.destroyWindow('screen')

    def show_blocks(self):
        for block in self.blocks:
            print(block)
            self.show_element_by_id(block['id'])


if __name__ == '__main__':
    load = False
    gui = GUIData(gui_img_file='data/twitter/testcase1/device/0.png',
                  gui_json_file='data/twitter/testcase1/device/0.json',
                  output_file_root='data/twitter/testcase1')
    # load previous result
    if load:
        gui.load_elements()
    # process from scratch
    else:
        gui.ui_info_extraction()
        gui.ui_analysis_elements_description()
        gui.ui_element_block_tree()
    gui.show_all_elements(only_leaves=True)
