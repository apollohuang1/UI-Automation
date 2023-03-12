import warnings
warnings.filterwarnings("ignore", category=Warning)

from ppadb.client import Client as AdbClient
from Device import Device
from GUIData import GUIData
from Automator import Automator
client = AdbClient(host="127.0.0.1", port=5037)

task = 'Follow Elon Musk'
device = Device(client.devices()[0], app_name='twitter', test_case_no=1)

while True:
    # 1. Save vh xml, json and screenshot image to "data/app_name/test_case_no/device"
    print('\n=== 1. Collect UI metadata from the device ===')
    device.cap_screenshot()
    device.cap_vh()
    device.reformat_vh_json()

    # 2. Extract elements and element_tree and save to "data/app_name/test_case_no/guidata"
    print('\n=== 2. Extract and analyze UI info ===')
    gui = GUIData(gui_img_file=device.output_file_path_screenshot,
                  gui_json_file=device.output_file_path_json,
                  output_file_root=device.testcase_save_dir)
    gui.ui_info_extraction()
    gui.ui_analysis_elements_description()
    gui.ui_element_block_tree()
    gui.show_all_elements(only_leaves=False)

    # 3. Generate description for blocks and ask a chain of questions to identify target block and target element related to the task, save to "data/app_name/test_case_no/automator"
    print('\n=== 3. Check if the task can complete on the UI through AI chain ===')
    aut = Automator(gui)
    result = aut.ai_chain(task)  # None for infeasible task; (action_type, element_id) for feasible task

    if result is not None:
        # 4. Execute the action
        print('\n=== 4. Execute action to click or scroll element ===')
        aut.execute_action(result, device.adb_device, show=True)
        device.ui_no += 1   # next UI
    else:
        # stop the process if the task is infeasible
        print('\n=== 4. The task is infeasible on the current UI ===')
        break

    # stop the process if the task completes
    if aut.task_complete:
        print('\n=== 5. Complete the task and exit ===')
        break
