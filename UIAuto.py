import json
from os.path import join as pjoin
import os
import re
import cv2
import tiktoken
import math
from OpenAI import OpenAI


class UIAuto:
    def __init__(self, gui, task='', model='gpt-4'):
        self.gui = gui
        self.gui_name = self.gui.gui_name

        self.role = 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'
        self.openai = OpenAI(role=self.role, model=model)

        self.conversation = [{'role': 'system', 'content': self.role}]       # store the conversation history for block ai chain
        self.task = task  # string, a NL sentence to describe the task, e.g. "Turn on voice"

        self.ans_block_sum = None
        self.ans_target_block = None
        self.ans_target_element = None

    '''
    *******************************************
    *** AI Chain Checking Elements Directly ***
    *******************************************
    '''
    # def identify_task_target_element(self, task):
    #     self.conversation += [{'role': 'user', 'content': 'This is a view hierarchy of a UI, can you segment it into functional blocks? Summarize all of its elements and functionalities, and print the "id" of each block.'},
    #                           {'role': 'user', 'content': str(self.gui.element_tree)},
    #                           {'role': 'user', 'content': 'To complete the task "' + task + '", which block is the most related one to interact with?'}]

    '''
    ******************************
    *** AI Chain with UI Block ***
    ******************************
    '''
    def ai_chain_block(self, task, printlog=False):
        self.summarize_block(printlog)
        self.identify_task_target_block(task, printlog)
        self.identify_task_target_element_from_block(self.get_target_block_node(), printlog)

    def summarize_block(self, printlog=False):
        print('------ Summarize GUI Blocks ------')
        self.conversation += [{'role': 'user', 'content': 'This is a view hierarchy of a UI, can you segment it into functional blocks? Summarize all of its elements and functionalities, and print the "id" of each block.'},
                              {'role': 'user', 'content': str(self.gui.element_tree)}]
        self.ans_block_sum = self.openai.ask_openai_conversation(self.conversation, printlog=printlog)  # {'role':'system', 'content': 'Block sums'}
        self.conversation.append(self.ans_block_sum)

    def identify_task_target_block(self, task, printlog=False):
        print('------ Identify Target Blocks ------')
        self.task = task
        block_sum = self.conversation[-1]    # {'role':'system', 'content': 'Block sums'}
        conv = [{'role': 'system', 'content': self.role},
                block_sum,
                {'role': 'user', 'content': 'To complete the task "' + task + '", which block is the most related one to interact with? Just output the block id as the answer in format of - Block id: 2.'}]
        self.conversation.append(conv[-1])
        self.ans_target_block = self.openai.ask_openai_conversation(conv, printlog=printlog)  # {'role':'system', 'content': 'Target block'}
        self.conversation.append(self.ans_target_block)

    def get_target_block_node(self):
        b = re.findall('[Bb]lock\s*[Ii][Dd]:\s\d+', self.ans_target_block['content'])[0]
        block_id = int(re.findall('\d+', b)[0])
        return self.gui.get_ui_element_node_by_id(block_id)

    def identify_task_target_element_from_block(self, block_node, printlog=False):
        print('------ Identify Target Element ------')
        self.conversation += [{'role': 'user', 'content': 'All the elements view hierarchy in the blocks is:'},
                              {'role': 'user', 'content': str(block_node)},
                              {'role': 'user', 'content': 'Which element exactly in this Block is the most related one to interact with to the task "' + self.task + '"? Give the detail information from the view hierarchy.'}]
        conv_no_element_tree = self.conversation[:2] + self.conversation[3:]  # remove the entire element tree for the sake of token size
        self.ans_target_element = self.openai.ask_openai_conversation(conv_no_element_tree, printlog=printlog)
        self.conversation.append(self.ans_target_element)

    def save_conv(self, output_file='data/conv.json'):
        json.dump(self.conversation, open(output_file, 'w'), indent=2)

    def load_conv(self, input_file='data/conv.json'):
        self.conversation = json.load(open(input_file, 'r'))
