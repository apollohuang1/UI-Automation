import openai
from GUI import GUI


class Automator:
    def __init__(self, gui, task=''):
        self.gui = gui
        self.textual_elements = []

        openai.api_key = open('openaikey.txt', 'r').readline()
        self.task = task            # string, a NL sentence to describe the task, e.g. "Turn on voice"
        self.prompt = None          # string, prompt including the task and textual_element as options sent to the LLM
        self.openai_responses = []  # the response from openai asked the prompt
        self.openai_answers = []    # the text answer in the openai_resp

    '''
    *********************************
    *** GUI Element Understanding ***
    *********************************
    '''
    def get_textual_gui_elements(self):
        '''
        Get all the gui element in textual, including text elements and textual Compo labels
        '''
        for ele in self.gui.elements_leaves:
            if 'text' in ele and ele['text'] != '':
                text = ele['text']
                if 'content-desc' in ele and ele['content-desc'] != '':
                    text += ' / ' + ele['content-desc']
                    self.textual_elements.append(text)
                else:
                    self.textual_elements.append(ele['text'])
            else:
                if 'content-desc' in ele and ele['content-desc'] != '':
                    self.textual_elements.append(ele['content-desc'])
                # else:
                #     self.textual_elements.append(ele['caption'])
    '''
    ******************
    *** OpenAI LLM ***
    ******************
    '''
    def assemble_prompt(self):
        pre_prompt = 'I will give you several UI components on a UI page, which one of them is more related to the task "' + self.task + '"?'
        post_prompt = 'Components:[' + ';'.join(self.textual_elements) + ';'
        self.prompt = pre_prompt + post_prompt + ']'

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
        print('*** Answer ***\n', resp['choices'][0].message)


if __name__ == '__main__':
    automator = Automator('data/input/2.jpg')
    automator.get_textual_gui_elements()
    automator.select_element_to_perform_task("Contact Lelya")
