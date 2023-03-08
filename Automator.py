import openai
import json
from os.path import join as pjoin
import os


class Automator:
    def __init__(self, gui=None, task='', output_file_root='data/twitter/testcase1/automator', gui_name='test'):
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

        # output file paths
        self.output_root = output_file_root
        os.makedirs(output_file_root, exist_ok=True)
        self.output_block_desc = pjoin(self.output_root, self.gui_name + '_block_desc.json')
        self.output_chain_block = pjoin(self.output_root, self.gui_name + '_chain_block.json')
        self.output_chain_element = pjoin(self.output_root, self.gui_name + '_chain_element.json')


    '''
    **********************
    *** AI Chain Block ***
    **********************
    '''
    def ai_chain_block(self, task=None):
        self.generate_descriptions_for_blocks()
        self.target_block_identification(task)
        self.scrollable_block_check()
        self.intermediate_block_check()
        json.dump(self.chain_block, open(self.output_chain_block, 'w', encoding='utf-8'), indent=4)

    def generate_descriptions_for_blocks(self):
        print('------ Generate Block Descriptions ------')
        prompt = 'This is a code snippet that descript a part of UI, summarize its functionalities in one paragraph.\n'
        for block in self.gui.blocks:
            desc = self.ask_openai_prompt(prompt + str(block))['content']
            if self.gui.elements[block['id']]['scrollable']:
                self.block_descriptions.append('[Scrollable] ' + desc)
            else:
                self.block_descriptions.append('[Not Scrollable] ' + desc)
        json.dump(self.block_descriptions, open(self.output_block_desc, 'w'), indent=4)

    def target_block_identification(self, task=None):
        print('------ Target Block Identification ------')
        if not task: task = self.task
        prompt = 'I will give you a list of blocks in the UI, is any of them related to the task "' + task + '"? ' \
                 'If yes, which block is the most related to complete the task?\n'
        for i, block_desc in enumerate(self.block_descriptions):
            prompt += '[Block ' + str(i) + ']:' + block_desc + '\n'
        prompt += '\n Answer [Yes] with the most related block if any or [No] if not.'
        self.chain_block = [{'role': 'system', 'content': self.role}]
        self.chain_block.append({'role': 'user', 'content': prompt})
        self.chain_block.append(self.ask_openai_conversation(self.chain_block))
        self.block_identification = self.chain_block[-1]['content']

    def scrollable_block_check(self):
        print('------ Scrollable Block Check ------')
        prompt = {'role': 'user',
                  'content': 'For scrollable blocks, is it possible that the UI elements related to the task would show up after scroll? '
                             'Answer [Yes] with the most related block if any or [No] if not'}
        self.chain_block.append(prompt)
        self.chain_block.append(self.ask_openai_conversation(self.chain_block))
        self.block_scrollable_check = self.chain_block[-1]['content']

    def intermediate_block_check(self):
        print('------ Intermediate Block Check ------')
        prompt = {'role': 'user',
                  'content': 'The task may take multiple steps to complete, is there any block likely to jump to the UI that is related to the task? ' +
                             'Answer [Yes] with the most related block if any or [No] if not'}
        self.chain_block.append(prompt)
        self.chain_block.append(self.ask_openai_conversation(self.chain_block))
        self.block_intermediate_check = self.chain_block[-1]['content']

    '''
    ************************
    *** AI Chain Element ***
    ************************
    '''
    def ai_chain_element(self, target_block):
        self.task_completion_check(target_block)
        self.intermediate_element_check()
        json.dump(self.chain_block, open(self.output_chain_element, 'w', encoding='utf-8'), indent=4)

    def task_completion_check(self, target_block):
        prompt = {'role': 'user',
                  'content': 'Can any elements in the given UI block complete the task directly? \n' +
                             'UI block: ' + str(target_block) +
                             '\nAnswer [Yes] with the target element if any or [No] if not'}
        self.chain_element = [{'role': 'system', 'content': self.role}]
        self.chain_element.append(prompt)
        self.chain_element.append(self.ask_openai_conversation(self.chain_element))
        self.element_complete = self.chain_element[-1]['content']

    def intermediate_element_check(self):
        prompt = {'role': 'user',
                  'content': 'The task may take multiple steps to complete, is there any UI element in the block likely to jump to the UI that is related to the task? ' +
                             'Answer [Yes] with the most related block if any or [No] if not'}
        self.chain_element.append(prompt)
        self.chain_element.append(self.ask_openai_conversation(self.chain_element))
        self.element_intermediate = self.chain_element[-1]['content']

    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def ask_openai_prompt(self, prompt, role=None):
        if not role: role = self.role
        conversation = [{'role': 'system', 'content': self.role}, {'role': 'user', 'content': prompt}]
        print('*** Asking ***\n', conversation)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation
            )
        print('\n*** Answer ***\n', resp['choices'][0].message, '\n')
        return dict(resp['choices'][0].message)

    def ask_openai_conversation(self, conversation):
        print('*** Asking ***\n', conversation)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation
            )
        print('\n*** Answer ***\n', resp['choices'][0].message, '\n')
        return dict(resp['choices'][0].message)

    '''
    *****************
    *** Utilities ***
    *****************
    '''
    def load_conversation(self):
        self.chain_block = json.load(open(self.output_chain_block, 'r', encoding='utf-8'))
        self.chain_element = json.load(open(self.output_chain_element, 'r', encoding='utf-8'))
        print('Load ai chain conversation from', self.output_chain_block, self.output_chain_element)

    def load_block_descriptions(self):
        self.block_descriptions = json.load(open(self.output_block_desc, 'r', encoding='utf-8'))
        print('Load ai chain conversation from', self.output_chain_block, self.output_chain_element)

    def show_target_element(self, ele_id):
        print(self.gui.elements_leaves[ele_id])
        self.gui.show_element(self.gui.elements_leaves[ele_id])


if __name__ == '__main__':
    from GUIData import GUIData
    gui = GUIData(gui_img_file='data/twitter/testcase1/device/0.png',
                  gui_json_file='data/twitter/testcase1/device/0.json',
                  output_file_root='data/twitter/testcase1/guidata')
    # gui.ui_info_extraction()
    # gui.ui_analysis_elements_description()
    # gui.ui_element_block_tree()
    gui.load_elements()
    gui.show_all_elements(only_leaves=True)

    aut = Automator(gui)
    aut.ai_chain_block('Change display language')
