import openai
import json
from os.path import join as pjoin
import os
import re


class Automator:
    def __init__(self, gui=None, task='', output_file_root='data/twitter/testcase1', gui_name='test'):
        self.gui = gui
        self.gui_name = self.gui.gui_name if self.gui else gui_name

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.role = 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'
        self.chain_block = [{'role': 'system', 'content': self.role}]       # store the conversation history for block ai chain
        self.chain_element = [{'role': 'system', 'content': self.role}]     # store the conversation history for element ai chain
        self.task = task                # string, a NL sentence to describe the task, e.g. "Turn on voice"

        self.block_descriptions = []        # list of strings describing block
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

    def ai_chain(self, task=None, show_block=False, load_block_desc=False):
        self.task = task
        # Block description
        if not load_block_desc:
            self.generate_descriptions_for_blocks(show_block)
        # 1. Related target block
        self.target_block_identification(task)
        # identify the target element if the block is directly related
        if 'Yes' in self.block_identification:
            # *** 1.1 Identify target element in related block
            ele_id = self.ai_chain_element(block_id=self.extract_block_id_from_sentence(self.block_identification), task=task)
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
                return 'scroll', block_id
            else:
                # 3. Intermediate block that is indirectly related
                self.intermediate_block_check()
                if 'Yes' in self.block_intermediate_check:
                    # *** 3.1 Identify target element in related block
                    ele_id = self.ai_chain_element(block_id=self.extract_block_id_from_sentence(self.block_intermediate_check), task=task)
                    if ele_id is not None:
                        return 'click', ele_id
                    else:
                        return None
                else:
                    print('\n*** No related blocks ***\n')
                    return None

    '''
    **********************
    *** AI Chain Block ***
    **********************
    '''
    def ai_chain_block(self, task=None, show_block=False):
        self.generate_descriptions_for_blocks(show_block)
        self.target_block_identification(task)
        self.scrollable_block_check()
        self.intermediate_block_check()
        json.dump(self.chain_block, open(self.output_chain_block, 'w', encoding='utf-8'), indent=4)

    def generate_descriptions_for_blocks(self, show=False):
        print('------ Generate Block Descriptions ------')
        prompt = 'This is a code snippet that descript a part of UI, summarize its functionalities in one paragraph.\n'
        for block in self.gui.blocks:
            desc = self.ask_openai_prompt(prompt + str(block), self.role)['content']
            if self.gui.elements[block['id']]['scrollable']:
                self.block_descriptions.append('[Scrollable] ' + desc)
            else:
                self.block_descriptions.append('[Not Scrollable] ' + desc)
            print(self.block_descriptions[-1])
            if show:
                self.gui.show_element(self.gui.elements[block['id']])
        json.dump(self.block_descriptions, open(self.output_block_desc, 'w'), indent=4)

    def target_block_identification(self, task=None):
        print('\n------ Target Block Identification ------')
        prompt = 'I will give you a list of blocks in the UI, is any of them related to the task "' + task + '"? ' \
                 'If yes, which block is the most related to complete the task?\n'
        for i, block_desc in enumerate(self.block_descriptions):
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
    ************************
    *** AI Chain Element ***
    ************************
    '''
    def ai_chain_element(self, block_id, task):
        print('\n====== Identify the target element in Block %d ======' % block_id)
        target_block = self.gui.blocks[block_id]
        # check if the task can be completed directly
        self.task_completion_check(target_block, task)
        if 'Yes' in self.element_complete:
            element_id = self.extract_element_id_from_sentence(self.element_complete)
            print('*** [Element %d] can complete the task ***' % element_id)
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
        print('\n------ Task Completion Check ------')
        prompt = {'role': 'user',
                  'content': "This given UI block is related to the task '" + task + "'. Can your click on any element in it to complete the task? \n" +
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

    def show_target_element(self, ele_id):
        print(self.gui.elements_leaves[ele_id])
        self.gui.show_element(self.gui.elements_leaves[ele_id])


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
