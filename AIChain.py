import json
import re
import cv2
from utils.openai.OpenAI import OpenAI


class AIChain:
    def __init__(self, gui, task='', model='gpt-4', device=None):
        self.device = device

        self.gui = gui
        self.gui_name = self.gui.gui_name

        self.role = 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'
        self.openai = OpenAI(role=self.role, model=model)

        self.conversation = None  # store the conversation history for block ai chain
        self.task = task  # string, a NL sentence to describe the task, e.g. "Turn on voice"

    def init_conversation(self):
        self.conversation = [
            {'role': 'system', 'content': self.role},
            {'role': 'user', 'content': 'This is a view hierarchy of a UI containing various UI blocks and elements.'},
            {'role': 'user', 'content': str(self.gui.element_tree)},
            {'role': 'user', 'content': 'I will ask you questions and tasks based on this'}
        ]
        self.conversation.append(self.openai.ask_openai_conversation(self.conversation))

    '''
    *******************************************
    *** AI Chain - Checking UI Relationship ***
    *******************************************
    '''
    def ai_chain_automate_check_ui_relation(self, task, printlog=False):
        self.check_ui_relation_with_task(task, printlog=printlog)
        relation = self.conversation[-1]['content']
        # return the relationship between the current gui and the task
        if 'Unrelated' in relation:
            return 0, None
        elif 'Completed' in relation:
            return 1, None
        elif 'related' in relation:
            element = self.get_target_element_node(relation)
            return 2, element
        else:
            raise Exception("Incorrect relationship")

    def check_ui_relation_with_task(self, task, printlog=False):
        print('--- Check the relationship between the task and current gui ---')
        self.init_conversation()
        self.conversation += [
            {'role': 'user', 'content': 'I will give you a task, and please select the relationship between the UI and the task from the three options:'},
            {'role': 'user', 'content': '1. Directly related, which means there is an element in the UI to complete the task directly; 2. Indirectly related, which means although there is no element in the UI to complete the task directly, there is a certain element that can direct to the related UI to complete the task; 3. Unrelated, which means this UI is not related to the task at all; 4. Completed, which means the UI is already in the completed status of the task.'},
            {'role': 'user', 'content': 'Please answer in this format: [Relationship: Directly Related/ Indirectly related, Element id: 12], or [Relationship: Unrelated/Completed, Element id: N/A]. No need to detail any explanation.'}
        ]
        self.conversation.append(self.openai.ask_openai_conversation(self.conversation, printlog))
        self.conversation += [
            {'role': 'user', 'content': 'The task is "' + task + '".'}
        ]
        self.conversation.append(self.openai.ask_openai_conversation(self.conversation, printlog))
        print('Relationship -', self.conversation[-1]['content'])

    '''
    *********************************************
    *** AI Chain - Checking Elements Directly ***
    *********************************************
    '''
    def ai_chain_automate_check_elements_directly(self, task, printlog=False, show_action=False):
        self.check_direct_ui_relevance(task, printlog)
        if 'Yes' in self.conversation[-1]['content']:
            element = self.get_target_element_node(self.conversation[-1]['content'])
            action = ['click', element['id']]
            self.execute_action(action, self.device, show_action)
        else:
            self.check_indirect_ui_relevance(task, printlog)
            if 'Yes' in self.conversation[-1]['content']:
                element = self.get_target_element_node(self.conversation[-1]['content'])
                action = ['click', element['id']]
                self.execute_action(action, self.device, show_action)
            else:
                print('==== This UI is not related to the task ====')

    def check_direct_ui_relevance(self, task, printlog=False):
        print('--- Check if the UI directly related ---')
        self.init_conversation()
        self.conversation += [
            {'role': 'user', 'content': 'Is this UI directly related to the task "' + task + '"?'},
            {'role': 'user', 'content': 'If yes, answer "Yes" and the related Element id, for example, "Yes, Element id: 2". Otherwise, answer "No"'}
        ]
        self.conversation.append(self.openai.ask_openai_conversation(self.conversation, printlog=printlog))

    def check_indirect_ui_relevance(self, task, printlog=False):
        print('--- Check if the UI indirectly related ---')
        self.conversation += [
            {'role': 'user', 'content': 'The task "' + task + '" may take multiple steps to complete. Is there any UI elements that can direct to the related UI to complete the task?'},
            {'role': 'user', 'content': 'If yes, answer "Yes" and the related Element id, for example, "Yes, Element id: 2". Otherwise, answer "No"'}
        ]
        self.conversation.append(self.openai.ask_openai_conversation(self.conversation, printlog=printlog))

    def incorrect_element(self, ele_id, printlog=False):
        self.conversation += [
            {'role': 'user', 'content': 'Element ' + str(ele_id) + ' can not direct to the related UI. Answer the last question again.'}
        ]
        self.conversation.append(self.openai.ask_openai_conversation(self.conversation, printlog=printlog))

    '''
    ***************************
    *** AI Chain - UI Block ***
    ***************************
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

    '''
    ******************************
    *** Conversation Operation ***
    ******************************
    '''
    def save_conv(self, output_file='data/conv.json'):
        json.dump(self.conversation, open(output_file, 'w'), indent=2)

    def load_conv(self, input_file='data/conv.json'):
        self.conversation = json.load(open(input_file, 'r'))

    def print_conversation(self):
        print(json.dumps(self.conversation, indent=2))

    '''
    ************************
    *** Grounding Action ***
    ************************
    '''
    def get_target_element_node(self, sentence):
        print('--- Get the related element ---')
        e = re.findall('[Ee]lement\s*[Ii][Dd]:\s*\d+', sentence)
        ele_id = int(re.findall('\d+', e[0])[0])
        return self.gui.get_ui_element_node_by_id(ele_id)
