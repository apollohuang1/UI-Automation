import openai


class Automator:
    def __init__(self, gui=None, task=''):
        self.gui = gui
        self.element_desc = []

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.task = task            # string, a NL sentence to describe the task, e.g. "Turn on voice"
        self.prompt = None          # string, prompt including the task and textual_element as options sent to the LLM
        self.openai_responses = []  # the response from openai asked the prompt
        self.openai_answers = []    # the text answer in the openai_resp

    def gather_element_descriptions(self):
        for ele in self.gui.elements_leaves:
            if ele['description']:
                self.element_desc.append((ele['leaf-id'], ele['description']))

    def show_target_element(self, ele_id):
        print(self.gui.elements_leaves[ele_id])
        self.gui.show_element(self.gui.elements_leaves[ele_id])

    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def assemble_prompt(self):
        pre_prompt = 'You have a list of UI components on the current UI page, which one of them is more related to the task "' + self.task + '"?\n'
        post_prompt = 'Components:['
        for desc in self.element_desc:
            post_prompt += str(desc) + ';'
        self.prompt = pre_prompt + post_prompt + ']\n'
        self.prompt += 'Note that it may take multiple steps to reach the target UI with the target component to complete the task. ' \
                       'If no component in the current UI that directly related to the task, which of them is more possible to lead to the target UI?'

    def select_element_to_perform_task(self, task):
        self.task = task
        self.assemble_prompt()
        self.ask_openai(self.prompt)

    def ask_openai(self, prompt):
        print('*** Asking ***\n', prompt)
        resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {'role': 'system', 'content': 'You are a mobile virtual assistant that understands and interacts with the user interface to complete given task.'},
                    {'role': 'user', 'content': prompt}
                ]
            )
        self.openai_responses.append(resp)
        self.openai_answers.append(resp['choices'][0].message)
        print('\n*** Answer ***\n', resp['choices'][0].message)


if __name__ == '__main__':
    from GUIData import GUIData
    gui = GUIData('data/emulator-5554.png', 'data/emulator-5554.json')
    gui.extract_elements_from_vh()
    gui.show_all_elements()
    gui.show_all_elements(only_leaves=True)
    gui.extract_elements_description()

    aut = Automator(gui)
    aut.gather_element_descriptions()
    aut.select_element_to_perform_task(task='Change display language')
