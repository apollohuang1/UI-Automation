import openai


class Automator:
    def __init__(self, gui=None, task=''):
        self.gui = gui
        self.element_desc = []

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.role = 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'
        self.conversation = [{'role': 'system', 'content': self.role}]    # store the conversation history [{'role':, 'content':}]
        self.task = task                # string, a NL sentence to describe the task, e.g. "Turn on voice"

        self.block_description = []     # list of strings describing block
        self.block_identification = ''  # answer for block_identification

    def show_target_element(self, ele_id):
        print(self.gui.elements_leaves[ele_id])
        self.gui.show_element(self.gui.elements_leaves[ele_id])

    '''
    ***************
    *** AI Chain***
    ***************
    '''
    def generate_descriptions_for_blocks(self):
        prompt = 'This is a code snippet that descript a part of UI, summarize its functionalities in one paragraph.\n'
        for block in self.gui.blocks:
            self.block_description.append(self.ask_openai(prompt + str(block)))

    def target_block_identification(self):
        prompt = 'I will give you a list of blocks in the UI, is any of them related to the task "' + self.task + '"? ' \
                 'If yes, which block is the most related to complete the task?\n'
        for i, block_desc in enumerate(self.block_description):
            prompt += '[Block ' + str(i) + ':' + block_desc + '\n'
        prompt += '\n Just ask [Yes, Block id] if any block is related or [No] if not.'
        self.block_identification = self.ask_openai(prompt)

    # def scrollable_block_check(self):

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
        print('\n*** Answer ***\n', resp['choices'][0].message)
        return resp['choices'][0].message

    def ask_openai_conversation(self, conversation):
        if not conversation: conversation = self.conversation
        print('*** Asking ***\n', conversation)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    conversation
                ]
            )
        print('\n*** Answer ***\n', resp['choices'][0].message)
        return resp['choices'][0].message


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
