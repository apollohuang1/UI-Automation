import openai
import json
from os.path import join as pjoin
import os
import re
import cv2
import tiktoken
import math


class Automator:
    def __init__(self, gui=None, task='', output_file_root='data/twitter/testcase1', gui_name='test'):
        self.gui = gui
        self.gui_name = self.gui.gui_name if self.gui else gui_name

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.role = 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'
        self.chain_block = [{'role': 'system', 'content': self.role}]       # store the conversation history for block ai chain
        self.chain_element = [{'role': 'system', 'content': self.role}]     # store the conversation history for element ai chain
        self.task = task                # string, a NL sentence to describe the task, e.g. "Turn on voice"
        self.task_complete = False      # indicate whether the task is complete in this GUI

        self.block_descriptions = {'vh':[], 'desc':[]}    # UI blocks, 'vh' for short blocks that directly use vh, 'desc' for long blocks that are described with NL description
        self.block_identification = ''      # answer for target_block_identification()
        self.block_scrollable_check = ''    # answer for scrollable_block_check()
        self.block_intermediate_check = ''  # answer for intermediate_block_check()

        self.element_complete = ''          # answer for task_completion_check()
        self.element_intermediate = ''      # answer for intermediate_element_check()

        self.target_block_id = None         # target block ids grounded from answers
        self.target_element_id = None       # target element ids grounded from answers

        # output file paths
        self.output_root = pjoin(output_file_root, 'automator')
        os.makedirs(output_file_root, exist_ok=True)
        self.output_block_desc = pjoin(self.output_root, self.gui_name + '_block_desc.json')
        self.output_chain_block = pjoin(self.output_root, self.gui_name + '_chain_block.json')
        self.output_chain_element = pjoin(self.output_root, self.gui_name + '_chain_element.json')

    def ai_chain(self, task=None, load_block_desc=False):
        self.task = task
        # Block description
        if not load_block_desc:
            self.generate_descriptions_for_blocks()
        else:
            self.load_block_descriptions()
        # 0. Identify elements through leaves node vh
        ele_id = self.target_element_identification_by_vh(self.block_descriptions['vh'], task)
        if ele_id is not None:
            return 'click', ele_id
        # 1. Identify related block through descriptions
        self.target_block_identification_by_desc(task)
        # identify the target element if the block is directly related
        if 'Yes' in self.block_identification:
            # *** 1.1 Identify target element in related block
            block_id = self.extract_block_id_from_sentence(self.block_identification)
            ele_id = self.target_element_identification_by_vh(target_block=self.gui.blocks[block_id], task=task)
            if ele_id:
                return 'click', ele_id
            else:
                return None
        # search thoroughly if no directly related block
        else:
            # 2. Related block after scroll
            self.scrollable_block_check()
            if 'Yes' in self.block_scrollable_check:
                block_id = self.extract_block_id_from_sentence(self.block_scrollable_check)
                print('\n*** Scroll [BLock %d] ***\n' % block_id)
                # Scroll the block
                return 'scroll', self.gui.blocks[block_id]['id']
            else:
                # 3. Intermediate block that is indirectly related
                self.intermediate_block_check()
                block_id = self.extract_block_id_from_sentence(self.block_intermediate_check)
                if 'Yes' in self.block_intermediate_check:
                    # *** 3.1 Identify target element in related block
                    ele_id = self.target_element_identification_by_vh(self.gui.blocks[block_id], task=task)
                    if ele_id is not None:
                        return 'click', ele_id
                    else:
                        return None
                else:
                    print('\n*** No related blocks ***\n')
                    return None

    '''
    *************************************
    *** Block Partition & Description ***
    *************************************
    '''
    def generate_descriptions_for_blocks(self, show=False):
        print('------ Generate Block Descriptions ------')
        # short, long_blocks: list of block vh
        leaves, blocks = self.partition_element_to_leaves_and_blocks(self.gui.element_tree)
        # for leaves, use vh directly
        self.block_descriptions['vh'] = leaves
        # for blocks, generate descriptions
        for block in blocks:
            desc = self.generate_block_description(block, show=show)
            if 'scrollable' in self.gui.elements[block['id']] and self.gui.elements[block['id']]['scrollable']:
                self.block_descriptions['desc'].append('[Scrollable] ' + desc)
            else:
                self.block_descriptions['desc'].append('[Not Scrollable] ' + desc)

        json.dump(self.block_descriptions, open(self.output_block_desc, 'w'), indent=4)
        print(self.block_descriptions)

    def partition_element_to_leaves_and_blocks(self, element, max_token_thresh=3500):
        leaves = []     # a list of leave elements
        blocks = []     # a list of block elements
        # if the element is a leaf node, use its vh directly
        if 'children' not in element:
            leaves.append(element)
        else:
            for child in element['children']:
                # for leaves elements, record directly
                if 'children' not in child:
                    leaves.append(child)
                # for block elements, check if it is too long
                else:
                    token_size = self.count_token_size(self.element_to_str(child))
                    # token_size < max_token_thresh, keep as block
                    if token_size < max_token_thresh:
                        blocks.append(child)
                    # token_size > max_token_thresh, partition again
                    else:
                        l, b = self.partition_element_to_leaves_and_blocks(child)
                        if len(l) > 1:
                            blocks.append(l)
                        else:
                            leaves += l
                        blocks += b
            # if the leaves are too long, slice into several pieces (blocks)
            l_token = self.count_token_size(self.element_to_str(leaves))
            if l_token > max_token_thresh:
                slice_no = math.ceil(l_token / max_token_thresh)
                slize_size = len(leaves) // slice_no
                for i in range(slice_no - 1):
                    blocks.append(leaves[i * slize_size: (i + 1) * slize_size])
                blocks.append(leaves[(slice_no - 1) * slize_size:])
                leaves = []
            # if no blocks, use the element as a block as a whole
            if len(blocks) == 0:
                leaves = []
                blocks.append(element)
        return leaves, blocks

    def generate_block_description(self, block, show=False):
        prompt = 'This is a code snippet that descript a part of UI, summarize its functionalities in one paragraph.\n'
        desc = self.ask_openai_prompt(prompt + self.element_to_str(block), self.role, printlog=show)['content']
        if show:
            print(desc)
            self.gui.show_element(self.gui.elements[block['id']])
        return desc

    '''
    ***********************************
    *** Target Block Identification ***
    ***********************************
    '''
    def target_block_identification_by_desc(self, task):
        print('\n------ Target Block Identification ------')
        prompt = 'There are a few descriptions of UI blocks to descript their functionalities. is any of them related to the task "' + task + '"? '\
                 'If yes, which block is the most related to complete the task?\n'
        for i, block_desc in enumerate(self.block_descriptions['desc']):
            prompt += '[Block ' + str(i) + ']:' + block_desc + '\n'
        prompt += '\n Answer [Yes] with the most related block if any or [No] if not.'
        self.chain_block = [{'role': 'system', 'content': self.role}]
        self.chain_block.append({'role': 'user', 'content': prompt})
        self.chain_block.append(self.ask_openai_conversation(self.chain_block))
        self.block_identification = self.chain_block[-1]['content']
        print(self.block_identification)

    def scrollable_block_check(self):
        print('\n------ Scrollable Block Check ------')
        prompt = {'role': 'user',
                  'content': 'For scrollable blocks, is it possible that the UI elements related to the task would show up after scroll? '
                             'Answer [Yes] with the most related block (for example, "Yes, Block 1") if any or [No] if not'}
        self.chain_block.append(prompt)
        self.chain_block.append(self.ask_openai_conversation(self.chain_block))
        self.block_scrollable_check = self.chain_block[-1]['content']
        print(self.block_scrollable_check)

    def intermediate_block_check(self):
        print('\n------ Intermediate Block Check ------')
        prompt = {'role': 'user',
                  'content': 'The task may take multiple steps to complete, is there any block likely to direct to the UI that is related to the task? ' +
                             'Answer [Yes] with the most related block (for example, "Yes, Element 1") if any or [No] if not'}
        self.chain_block.append(prompt)
        self.chain_block.append(self.ask_openai_conversation(self.chain_block))
        self.block_intermediate_check = self.chain_block[-1]['content']
        print(self.block_intermediate_check)

    '''
    *************************************
    *** Target Element Identification ***
    *************************************
    '''
    def target_element_identification_by_vh(self, target_block, task):
        # print('\n------ Identify the target element in Block %d ------' % block_id)
        # check if the task can be completed directly
        self.task_completion_check(target_block, task)
        if 'Yes' in self.element_complete:
            element_id = self.extract_element_id_from_sentence(self.element_complete)
            self.task_complete = True
            print('\n*** [Element %d] can complete the task ***' % element_id)
            return element_id
        # if no, select the most related element
        else:
            self.intermediate_element_check()
            if 'Yes' in self.element_intermediate:
                element_id = self.extract_element_id_from_sentence(self.element_intermediate)
                print('\n*** [Element %d] is the intermediate element to complete the task ***' % element_id)
                return element_id
            else:
                print('\n*** No related elements ***')
                return None

    def task_completion_check(self, target_block, task):
        print('\n------ Element Task Completion Check ------')
        prompt = {'role': 'user',
                  'content': "This given UI block is related to the task '" + task + "'. Can your click on any leaf element that does not have any children in it to complete the task? \n" +
                             "UI block: " + json.dumps(target_block, indent=2) +
                             "\nAnswer [Yes] with the target element id (for example, 'Yes, Element 1') if any or [No] if not"}
        self.chain_element = [{'role': 'system', 'content': self.role}]
        self.chain_element.append(prompt)
        self.chain_element.append(self.ask_openai_conversation(self.chain_element))
        self.element_complete = self.chain_element[-1]['content']
        print(self.element_complete)

    def intermediate_element_check(self):
        print('\n------ Intermediate Element Check ------')
        prompt = {'role': 'user',
                  'content': 'The task may take multiple steps to complete, can your click on any element in the block to direct to the UI that is more related to the task? ' +
                             'Answer [Yes] with the most related element (for example, "Yes, Element 1") if any or [No] if not'}
        self.chain_element.append(prompt)
        self.chain_element.append(self.ask_openai_conversation(self.chain_element))
        self.element_intermediate = self.chain_element[-1]['content']
        print(self.element_intermediate)

    '''
    ***********************************
    *** Grounding Block and Element ***
    ***********************************
    '''
    def extract_block_id_from_sentence(self, sentence):
        b = re.findall('[Bb]lock\s*\d+', sentence)[0]
        return int(re.findall('\d+', b)[0])

    def extract_element_id_from_sentence(self, sentence):
        e = re.findall('[Ee]lement\s*\d+', sentence)[0]
        return int(re.findall('\d+', e)[0])

    # def execute_action(self, action, device, show=False):
    #     '''
    #     @action: (operation type, element id)
    #         => 'click', 'scroll'
    #     @device: ppadb device
    #     '''
    #     op_type, ele_id = action
    #     ele = self.gui.elements[ele_id]
    #     bounds = ele['bounds']
    #     if op_type == 'click':
    #         centroid = ((bounds[2] + bounds[0]) // 2, (bounds[3] + bounds[1]) // 2)
    #         if show:
    #             board = self.gui.img.copy()
    #             cv2.circle(board, (centroid[0], centroid[1]), 20, (255, 0, 255), 8)
    #             cv2.imshow('click', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
    #             cv2.waitKey()
    #             cv2.destroyWindow('click')
    #         device.input_tap(centroid[0], centroid[1])
    #     elif op_type == 'scroll':
    #         bias = 5
    #         if show:
    #             board = self.gui.img.copy()
    #             cv2.circle(board, (bounds[2]-bias, bounds[3]+bias), 20, (255, 0, 255), 8)
    #             cv2.circle(board, (bounds[0]-bias, bounds[1]+bias), 20, (255, 0, 255), 8)
    #             cv2.imshow('scroll', cv2.resize(board, (board.shape[1] // 3, board.shape[0] // 3)))
    #             cv2.waitKey()
    #             cv2.destroyWindow('scroll')
    #         device.input_swipe(bounds[2]-bias, bounds[3]+bias, bounds[0]-bias, bounds[1]+bias, 500)

    '''
    ***************
    *** Testing ***
    ***************
    '''
    def one_prompt_at_once(self, task, ui, role, printlog=False):
        '''
        Ask to complete the task without partitioning blocks
        '''
        conv = [{'role': 'system', 'content': role},
                  {'role': 'user',
                  'content': "Is the given UI related to the task '" + task + "'?\n" +
                             "UI block: " + json.dumps(ui, indent=2) +
                             "\nAnswer [Yes] with the id of the target element that is related to the task (for example, 'Yes, Element 1') if any or [No] if not"}]
        self.ask_openai_conversation(conv, printlog)


    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def ask_openai_prompt(self, prompt, role, printlog=False):
        if role is None:
            conversation = [{'role': 'user', 'content': prompt}]
        else:
            conversation = [{'role': 'system', 'content': role}, {'role': 'user', 'content': prompt}]
        if printlog:
            print('*** Asking ***\n', conversation)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation
            )
        if printlog:
            print('\n*** Answer ***\n', resp['choices'][0].message, '\n')
        return dict(resp['choices'][0].message)

    def ask_openai_conversation(self, conversation, printlog=False):
        if printlog:
            print('*** Asking ***\n', conversation)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation
            )
        if printlog:
            print('\n*** Answer ***\n', resp['choices'][0].message, '\n')
        return dict(resp['choices'][0].message)

    '''
    *****************
    *** Utilities ***
    *****************
    '''
    def count_token_size(self, string):
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(enc.encode(string))

    def element_to_str(self, element, indent=None):
        if not indent:
            return str(element)
        else:
            return json.dumps(element, indent=indent)

    def load_conversation(self):
        if os.path.exists(self.output_chain_block):
            self.chain_block = json.load(open(self.output_chain_block, 'r', encoding='utf-8'))
            print('Load ai chain block from', self.output_chain_block)
        if os.path.exists(self.output_chain_element):
            self.chain_element = json.load(open(self.output_chain_element, 'r', encoding='utf-8'))
            print('Load ai chain element from', self.output_chain_element)

    def load_block_descriptions(self):
        self.block_descriptions = json.load(open(self.output_block_desc, 'r', encoding='utf-8'))
        print('Load block description from', self.output_block_desc)
        print(self.block_descriptions)

    def show_target_element(self, ele_id):
        print(self.gui.elements[ele_id])
        self.gui.show_element(self.gui.elements[ele_id])


if __name__ == '__main__':
    from GUIData import GUIData
    gui = GUIData(gui_img_file='data/twitter/testcase1/device/0.png',
                  gui_json_file='data/twitter/testcase1/device/0.json',
                  output_file_root='data/twitter/testcase1')
    # gui.ui_info_extraction()
    # gui.ui_analysis_elements_description()
    # gui.ui_element_block_tree()
    gui.load_elements()
    gui.show_all_elements(only_leaves=True)

    aut = Automator(gui)
    aut.ai_chain_block('Follow Elon Musk')
