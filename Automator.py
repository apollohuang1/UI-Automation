import openai
import json


class Automator:
    def __init__(self, gui=None, task=''):
        self.output_root = 'data/openai'
        self.gui = gui
        self.element_desc = []

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.role = 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'
        self.conversation = [{'role': 'system', 'content': self.role}]    # store the conversation history [{'role':, 'content':}]
        self.task = task                # string, a NL sentence to describe the task, e.g. "Turn on voice"

        self.block_descriptions = []        # list of strings describing block
        self.block_identification = ''      # answer for target_block_identification()
        self.block_scrollable_check = ''    # answer for scrollable_block_check()
        self.block_intermediate_check = ''  # answer for intermediate_block_check()

    def generate_descriptions_for_blocks(self, save=True):
        prompt = 'This is a code snippet that descript a part of UI, summarize its functionalities in one paragraph.\n'
        for block in self.gui.blocks:
            desc = self.ask_openai_prompt(prompt + str(block))['content']
            if self.gui.elements[block['id']]['scrollable']:
                self.block_descriptions.append('[Scrollable] ' + desc)
            else:
                self.block_descriptions.append('[Not Scrollable] ' + desc)
        if save:
            self.save_block_descriptions()

    '''
    **********************
    *** AI Chain Block ***
    **********************
    '''
    def target_block_identification(self, task=None, new_conversation=True):
        if not task: task = self.task
        prompt = 'I will give you a list of blocks in the UI, is any of them related to the task "' + task + '"? ' \
                 'If yes, which block is the most related to complete the task?\n'
        for i, block_desc in enumerate(self.block_descriptions):
            prompt += '[Block ' + str(i) + ']:' + block_desc + '\n'
        prompt += '\n Answer [Yes] with the most related block if any or [No] if not.'
        if new_conversation:
            self.conversation = [{'role': 'system', 'content': self.role}]
        self.conversation.append({'role': 'user', 'content': prompt})
        self.conversation.append(self.ask_openai_conversation())
        self.block_identification = self.conversation[-1]['content']

    def scrollable_block_check(self):
        prompt = {'role': 'user',
                  'content': 'For scrollable blocks, is it possible that the UI elements related to the task would show up after scroll? '
                             'Answer [Yes] with the most related block if any or [No] if not'}
        self.conversation.append(prompt)
        self.conversation.append(self.ask_openai_conversation())
        self.block_scrollable_check = self.conversation[-1]['content']

    def intermediate_block_check(self):
        prompt = {'role': 'user',
                  'content': 'The task may take multiple steps to complete, is there any block likely to jump to the UI that is related to the task? ' +
                             'Answer [Yes] with the most related block if any or [No] if not'}
        self.conversation.append(prompt)
        self.conversation.append(self.ask_openai_conversation())
        self.block_intermediate_check = self.conversation[-1]['content']

    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def ask_openai_prompt(self, prompt, role=None):
        if not role: role = self.role
        print('*** Asking ***\n', role, '\n', prompt)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {'role': 'system', 'content': self.role},
                    {'role': 'user', 'content': prompt}
                ]
            )
        print('\n*** Answer ***\n', resp['choices'][0].message, '\n')
        return dict(resp['choices'][0].message)

    def ask_openai_conversation(self, conversation=None):
        if not conversation: conversation = self.conversation
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
    def save_conversation(self, file='data/openai/conversation.json'):
        json.dump(self.conversation, open(file, 'w', encoding='utf-8'), indent=4)

    def load_conversation(self, file='data/openai/conversation.json'):
        self.conversation = json.load(open(file, 'r', encoding='utf-8'))

    def save_block_descriptions(self, file='data/openai/blocks.json'):
        json.dump(self.block_descriptions, open(file, 'w', encoding='utf-8'), indent=4)

    def load_block_descriptions(self, file='data/openai/blocks.json'):
        self.block_descriptions = json.load(open(file, 'r', encoding='utf-8'))

    def show_target_element(self, ele_id):
        print(self.gui.elements_leaves[ele_id])
        self.gui.show_element(self.gui.elements_leaves[ele_id])


if __name__ == '__main__':
    from GUIData import GUIData
    gui = GUIData('data/emulator-5554.png', 'data/emulator-5554.json')
    gui.ui_info_extraction()
    gui.ui_analysis_elements_description()
    gui.ui_element_block_tree()
    gui.show_all_elements(only_leaves=True)

    aut = Automator(gui)
    aut.gather_element_descriptions()
    aut.select_element_to_perform_task(task='Change display language')
