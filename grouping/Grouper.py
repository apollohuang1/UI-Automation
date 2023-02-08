import pandas as pd
import cv2
import os
import json
import time
from os.path import join as pjoin

import detection.detect_text.text_detection as text
import detection.detect_compo.ip_region_proposal as ip
import detection.detect_merge.merge as merge
from grouping.obj.Compos_DF import ComposDF
from grouping.obj.Compo import *
from grouping.obj.Block import *
from grouping.obj.List import *
import grouping.lib.draw as draw


class Grouper:
    def __init__(self, img_file, detection_result_file, output_dir='data/output'):
        self.img_file = img_file
        self.img = cv2.imread(img_file)
        self.img_reshape = self.img.shape
        self.img_resized = cv2.resize(self.img, (self.img_reshape[1], self.img_reshape[0]))
        self.file_name = img_file.replace('\\', '/').split('/')[-1][:-4]

        self.detection_result_file = detection_result_file  # json file of detection result
        self.output_dir = pjoin(output_dir, 'layout') if output_dir is not None else None

        self.compos_json = None  # {'img_shape':(), 'compos':[]}
        self.compos_df = None    # dataframe for efficient processing
        self.compos = []         # list of Compo objects

        self.layout_result_img_group = None     # visualize group of compos with repetitive layout
        self.layout_result_img_pair = None      # visualize paired groups
        self.layout_result_img_list = None      # visualize list (paired group) boundary

        self.lists = []     # list of List objects representing lists
        self.blocks = []    # list of Block objects representing blocks

    def save_layout_result_imgs(self):
        os.makedirs(self.output_dir, exist_ok=True)
        cv2.imwrite(pjoin(self.output_dir, self.file_name + '-group.jpg'), self.layout_result_img_group)
        cv2.imwrite(pjoin(self.output_dir, self.file_name + '-pair.jpg'), self.layout_result_img_pair)
        cv2.imwrite(pjoin(self.output_dir, self.file_name + '-list.jpg'), self.layout_result_img_list)
        # print('Layout recognition result images save to ', output_dir)

    def save_layout_result_json(self):
        os.makedirs(self.output_dir, exist_ok=True)
        js = []
        for block in self.blocks:
            js.append(block.wrap_info())
        json.dump(js, open(pjoin(self.output_dir, self.file_name + '.json'), 'w'), indent=4)

    def save_layout_result(self):
        self.save_layout_result_imgs()
        self.save_layout_result_json()

    '''
    *****************************
    *** GUI Element Detection ***
    *****************************
    '''
    def load_detection_result_from_file(self):
        '''
        Load json detection result from json file
        '''
        self.compos_json = json.load(open(self.detection_result_file))
        self.img_reshape = self.compos_json['img_shape']
        self.img_resized = cv2.resize(self.img, (self.img_reshape[1], self.img_reshape[0]))

    def load_compos(self, compos):
        '''
        Load compos from objects: {'img_shape':(), 'compos':[]}
        '''
        self.compos_json = compos.copy()
        self.img_reshape = self.compos_json['img_shape']
        self.img_resized = cv2.resize(self.img, (self.img_reshape[1], self.img_reshape[0]))

    '''
    **************************
    *** Layout Recognition ***
    **************************
    '''
    # *** step1 ***
    def cvt_compos_json_to_dataframe(self):
        '''
        Represent the components using a Pandas DataFrame for the sake of processing
        '''
        self.compos_df = ComposDF(json_data=self.compos_json, gui_img=self.img_resized.copy())

    # *** step2 ***
    def recognize_groups(self):
        '''
        Recognize perceptual groups according to clustering and pairing algorithms
        '''
        # cluster elements into groups according to position and area
        self.compos_df.recognize_element_groups_by_clustering()   # group, alignment_in_group, group_nontext, group_text
        # group similar Blocks (Containers) by checking their children's similarity
        self.compos_df.recognize_similar_blocks()       # group_pair
        # pair clusters (groups) into a larger group
        self.compos_df.pair_groups()                    # group_pair, pair_to
        # identify list item (paired elements) in each compound large group
        self.compos_df.list_item_partition()            # list_item
        # filter out invalid unpaired groups
        self.compos_df.remove_invalid_groups()
        # add missed compos by checking group items
        self.compos_df.add_missed_compos_by_checking_group_item()

    # *** step3 ***
    def cvt_groups_to_list_compos(self):
        '''
        Represent the recognized perceptual groups as List objects
        '''
        df = self.compos_df.compos_dataframe
        self.lists = []
        self.compos = []

        # multiple list (multiple compos in each list item)
        groups = df.groupby('group_pair').groups
        list_id = 0
        for i in groups:
            if i == -1 or len(groups[i]) == 1:
                continue
            self.lists.append(List(compo_id='l-' + str(list_id), list_class='multi', compo_df=df.loc[groups[i]], list_alignment=df.loc[groups[i][0]]['alignment_in_group']))
            list_id += 1
            # remove selected compos
            df = df.drop(list(groups[i]))

        # single list (single compo in each list item)
        groups = df.groupby('group').groups
        for i in groups:
            if i == -1 or len(groups[i]) == 1:
                continue
            self.lists.append(List(compo_id='l-' + str(list_id), list_class='single', compo_df=df.loc[groups[i]], list_alignment=df.loc[groups[i][0]]['alignment_in_group']))
            list_id += 1
            # remove selected compos
            df = df.drop(list(groups[i]))

        # convert left compos that are not in lists
        for i in range(len(df)):
            compo_df = df.iloc[i]
            self.compos.append(Compo(compo_id='c-' + str(compo_df['id']), compo_class=compo_df['class'], compo_df=compo_df))
        # regard the list as a type of component in the GUI
        self.compos += self.lists

    # *** step4 ***
    def slice_hierarchical_block(self):
        '''
        Slice the GUI into hierarchical blocks based on the recognized Compos
        '''
        blocks, non_blocked_compos = slice_blocks(self.compos, 'v')
        self.blocks = blocks

    # entry method
    def recognize_layout(self, is_save=True):
        start = time.clock()
        self.cvt_compos_json_to_dataframe()
        self.recognize_groups()
        self.cvt_groups_to_list_compos()
        self.slice_hierarchical_block()
        self.get_layout_result_imgs()
        if is_save:
            self.save_layout_result()
        print("[Layout Recognition Completed in %.3f s] Input: %s Output: %s" % (time.clock() - start, self.img_file, pjoin(self.output_dir, self.file_name + '.json')))
        # print(time.ctime(), '\n\n')

    '''
    *********************
    *** Visualization ***
    *********************
    '''
    def get_layout_result_imgs(self):
        self.layout_result_img_group = self.visualize_compos_df('group', show=False)
        self.layout_result_img_pair = self.visualize_compos_df('group_pair', show=False)
        self.layout_result_img_list = self.visualize_lists(show=False)

    def visualize_layout_recognition(self):
        # self.visualize_all_compos()
        cv2.imshow('group', cv2.resize(self.layout_result_img_group, (500, 800)))
        cv2.imshow('group_pair', cv2.resize(self.layout_result_img_pair, (500, 800)))
        cv2.imshow('list', cv2.resize(self.layout_result_img_list, (500, 800)))
        cv2.waitKey()
        cv2.destroyAllWindows()

    def visualize_compos_df(self, visualize_attr, show=True):
        board = self.img_resized.copy()
        return self.compos_df.visualize_fill(board, gather_attr=visualize_attr, name=visualize_attr, show=show)

    def visualize_all_compos(self, show=True):
        board = self.img_resized.copy()
        for compo in self.compos:
            board = compo.visualize(board)
        if show:
            cv2.imshow('compos', board)
            cv2.waitKey()
            cv2.destroyWindow('compos')

    def visualize_lists(self, show=True):
        board = self.img_resized.copy()
        for lst in self.lists:
            board = lst.visualize_list(board, flag='block')
        if show:
            cv2.imshow('lists', board)
            cv2.waitKey()
            cv2.destroyWindow('lists')
        return board

    def visualize_block(self, block_id, show=True):
        board = self.img_resized.copy()
        self.blocks[block_id].visualize_sub_blocks_and_compos(board, show=show)

    def visualize_blocks(self, show=True):
        board = self.img_resized.copy()
        for block in self.blocks:
            board = block.visualize_block(board)
        if show:
            cv2.imshow('compos', board)
            cv2.waitKey()
            cv2.destroyWindow('compos')

    def visualize_container(self, show=True):
        board = self.img_resized.copy()
        df = self.compos_df.compos_dataframe
        containers = df[df['class'] == 'Block']
        for i in range(len(containers)):
            container = containers.iloc[i]
            children = df.loc[list(container['children'])]
            for j in range(len(children)):
                child = children.iloc[j]
                color = (0,255,0) if child['class'] == 'Compo' else (0,0,255)
                cv2.rectangle(board, (child['column_min'], child['row_min']), (child['column_max'], child['row_max']), color, 2)
            draw.draw_label(board, (container['column_min'], container['row_min'], container['column_max'], container['row_max']), (166, 166, 0), text='container')
        if show:
            cv2.imshow('container', board)
            cv2.waitKey()
            cv2.destroyWindow('container')
