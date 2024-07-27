import zmq

import pygame
import pygame_gui
from collections import deque
import random

import serial
import serial.tools.list_ports
import time
import os
import re

import matplotlib as plt

from serial.serialutil import to_bytes

from pygame_gui import UIManager, PackageResource

from pygame_gui.elements import UIWindow
from pygame_gui.elements import UIButton
from pygame_gui.elements import UIHorizontalSlider
from pygame_gui.elements import UITextEntryLine
from pygame_gui.elements import UIDropDownMenu
from pygame_gui.elements import UIScreenSpaceHealthBar
from pygame_gui.elements import UILabel
from pygame_gui.elements import UIImage
from pygame_gui.elements import UIPanel
from pygame_gui.elements import UISelectionList
from pygame_gui.elements.ui_text_box import UITextBox


from pygame_gui.windows import UIMessageWindow

mcu_serial_object = None
enable_serial_monitor = 1 # 0-disable 1-in app 2-in terminal
serial_log_file = None
serial_msg_text = ""
joysticks = None

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

class Options:
    def __init__(self):
        self.resolution = (1440, 800)
        self.fullscreen = False

class OptionsUIApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Options UI")
        self.options = Options()
        if self.options.fullscreen:
            self.window_surface = pygame.display.set_mode(self.options.resolution,
                                                          pygame.FULLSCREEN)
        else:
            self.window_surface = pygame.display.set_mode(self.options.resolution)

        self.background_surface = None

        self.ui_manager = UIManager(self.options.resolution,
                                    PackageResource(package='data.themes',
                                                    resource='theme_2.json'))
        self.ui_manager.preload_fonts([{'name': 'fira_code', 'point_size': 10, 'style': 'bold'},
                                       {'name': 'fira_code', 'point_size': 10, 'style': 'regular'},
                                       {'name': 'fira_code', 'point_size': 10, 'style': 'italic'},
                                       {'name': 'fira_code', 'point_size': 14, 'style': 'italic'},
                                       {'name': 'fira_code', 'point_size': 14, 'style': 'bold'}
                                       ])

        self.test_slider = None
        self.slider2 = None
        self.slider3 = None
        self.slider4 = None
        self.test_text_entry = None
        self.test_drop_down = None
        self.test_drop_down_2 = None
        self.message_window = None

        self.serial_monitor_mode_header_textbox = None
        self.serial_monitor_mode = None

        self.serial_select_dropdown = None
        self.serial_connect_button = None
        self.serial_refresh_button = None
        self.serial_baudrate_textbox = None

        self.serial_msg_disp = None
        self.serial_msg_entry = None

        self.recreate_ui()

        self.clock = pygame.time.Clock()
        self.time_delta_stack = deque([])

        self.button_response_timer = pygame.time.Clock()
        self.running = True
        self.debug_mode = False

        self.all_enabled = True
        self.all_shown = True

    def recreate_ui(self):
        self.ui_manager.set_window_resolution(self.options.resolution)
        self.ui_manager.clear_and_reset()

        self.background_surface = pygame.Surface(self.options.resolution)
        self.background_surface.fill(self.ui_manager.get_theme().get_colour('dark_bg'))

        self.test_slider = UIHorizontalSlider(pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                          int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 3)),
                                                          (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                              50.0,
                                              (0.0, 100.0),
                                              self.ui_manager,
                                              object_id='#cool_slider')
        
        self.slider2 = UIHorizontalSlider(pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                          int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 4)),
                                                          (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                              50.0,
                                              (0.0, 100.0),
                                              self.ui_manager,
                                              object_id='#slider2')
        
        self.slider3 = UIHorizontalSlider(pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                          int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 5)),
                                                          (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                              50.0,
                                              (0.0, 100.0),
                                              self.ui_manager,
                                              object_id='#slider3')
        
        self.slider4 = UIHorizontalSlider(pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                          int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 6)),
                                                          (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                              50.0,
                                              (0.0, 100.0),
                                              self.ui_manager,
                                              object_id='#slider4')

        self.test_text_entry = UITextEntryLine(pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                            int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 16)),
                                                           (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                               self.ui_manager,
                                               object_id='#main_text_entry')
        self.test_text_entry.set_text('')

        current_resolution_string = (str(self.options.resolution[0]) +
                                     'x' +
                                     str(self.options.resolution[1]))
        self.test_drop_down = UIDropDownMenu(options_list=['1024x768', '1200x800', '1440x800', '1600x900', '800x600', '600x800'],
                                             starting_option=current_resolution_string,
                                             relative_rect = pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                          int(self.options.resolution[1] * 0.01)),
                                                         (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                             manager = self.ui_manager)

        self.test_drop_down_2 = UIDropDownMenu(options_list=['Penguins', 'drop down', 'menu',
                                                'testing', 'overlaps'],
                                               starting_option='Penguins',
                                               relative_rect = pygame.Rect((int(self.options.resolution[0] * 0.01),
                                                          int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32)),
                                                         (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
                                               manager = self.ui_manager,
                                               )
        
        self.serial_select_dropdown = UIDropDownMenu(
            options_list=['not selected'],
            starting_option='not selected',
            relative_rect = pygame.Rect((int(self.options.resolution[0] * 0.99) - int(self.options.resolution[0] / 4),
                            int(self.options.resolution[1] * 0.01)),
                            (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
            manager = self.ui_manager,
            )
        
        self.serial_refresh_button = UIButton(
            pygame.Rect((int(self.options.resolution[0] * 0.99) - int(self.options.resolution[0] / 4),
                            int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32)),
                            (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
            'Refresh COM Ports',
            self.ui_manager)

        self.serial_connect_button = UIButton(
            pygame.Rect((int(self.options.resolution[0] * 0.99) - int(self.options.resolution[0] / 4),
                            int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 16)),
                            (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
            'Press to Connect',
            self.ui_manager)
        
        self.serial_baudrate_textbox = UITextEntryLine(
            relative_rect=pygame.Rect((int(self.options.resolution[0] * 0.99) - int(self.options.resolution[0] / 4),
                            int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 3)),
                            (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
            manager=self.ui_manager,
            initial_text="9600"
        )
        
        self.serial_monitor_mode_header_textbox = UILabel (
            relative_rect= pygame.Rect((int(self.options.resolution[0] * 0.01),
                        int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 7)),
                        (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
            text="Select serial output method"
        )

        self.serial_monitor_mode = UIDropDownMenu(
            options_list=['In app', 'In terminal', 'Disable'],
            starting_option='In app',
            relative_rect= pygame.Rect((int(self.options.resolution[0] * 0.01),
                        int(self.options.resolution[1] * 0.01)+int(self.options.resolution[1] / 32 * 8)),
                        (int(self.options.resolution[0] / 4), int(self.options.resolution[1] / 32))),
            manager=self.ui_manager,
            object_id="#serialmonitor"
        )

        self.serial_msg_disp = UITextBox(
            html_text="",
            relative_rect=pygame.Rect((int(self.options.resolution[0] * 0.01 + self.options.resolution[0] / 4),
                        int(self.options.resolution[1] * 0.01 + self.options.resolution[1] / 32)),
                        (int(self.options.resolution[0] / 2 - self.options.resolution[0] * 0.02), int(self.options.resolution[1] * 28 / 32))),
            manager=self.ui_manager
        )

        self.serial_msg_entry = UITextEntryLine(
            relative_rect=pygame.Rect((int(self.options.resolution[0] * 0.01 + self.options.resolution[0] / 4),
                        int(self.options.resolution[1] * 0.01)),
                        (int(self.options.resolution[0] / 2 - self.options.resolution[0] * 0.02), int(self.options.resolution[1] / 32))), 
            manager=self.ui_manager,
            object_id='#serial_text_entry'
        )

        self.serial_msg_entry.set_text('')

    def create_message_window(self):
        self.button_response_timer.tick()
        self.message_window = UIMessageWindow(
            rect=pygame.Rect((random.randint(0, self.options.resolution[0] - 300),
                              random.randint(0, self.options.resolution[1] - 200)),
                             (300, 250)),
            window_title='Test Message Window',
            html_message='this is a message',
            manager=self.ui_manager)
        time_taken = self.button_response_timer.tick() / 1000.0
        # currently taking about 0.35 seconds down from 0.55 to create
        # an elaborately themed message window.
        # still feels a little slow but it's better than it was.
        print("Time taken to create message window: " + str(time_taken))

    def check_resolution_changed(self):
        resolution_string = self.test_drop_down.selected_option.split('x')
        resolution_width = int(resolution_string[0])
        resolution_height = int(resolution_string[1])
        if (resolution_width != self.options.resolution[0] or
                resolution_height != self.options.resolution[1]):
            self.options.resolution = (resolution_width, resolution_height)
            self.window_surface = pygame.display.set_mode(self.options.resolution)
            self.recreate_ui()

    def process_events(self):
        global mcu_serial_object
        global enable_serial_monitor
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            self.ui_manager.process_events(event)

            if event.type == pygame.JOYBUTTONDOWN:
                print("Joystick button pressed.")
                if event.button == 0:
                    joystick = joysticks[event.instance_id]
                    if joystick.rumble(0, 0.7, 500):
                        print(f"Rumble effect played on joystick {event.instance_id}")

            # if event.type == pygame.KEYDOWN and event.key == pygame.K_d:
            #     self.debug_mode = False if self.debug_mode else True
            #     self.ui_manager.set_visual_debug_mode(self.debug_mode)

            # if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            #     print("self.ui_manager.focused_set:", self.ui_manager.focused_set)

            if (event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED):
                if (event.ui_object_id == '#main_text_entry'):
                    print("main: " + event.text)
                if (event.ui_object_id == '#serial_text_entry'):
                    try:
                        str_to_be_sent = event.text
                        utf8str = str_to_be_sent.encode('utf-8') + b'\n'
                        print("Sent: ", end="")
                        print(utf8str)
                        mcu_serial_object.write(utf8str)
                        self.serial_msg_entry.set_text("")
                    except:
                        print("Send failed!")
                        
            if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if mcu_serial_object is None:
                    print("please connect via serial first")
                else:
                    if event.ui_element == self.test_slider:
                        sliderval = self.test_slider.get_current_value()
                    elif event.ui_element == self.slider2:
                        sliderval = self.slider2.get_current_value()
                    elif event.ui_element == self.slider3:
                        sliderval = self.slider3.get_current_value()
                    elif event.ui_element == self.slider4:
                        sliderval = self.slider4.get_current_value()

                    if sliderval > 51:
                        sendval_a = (sliderval-51)
                        sendval_b = 5
                    elif sliderval < 49:
                        sendval_b = (49 - sliderval)
                        sendval_a = 5
                    else:
                        sendval_a = 5
                        sendval_b = 5

                    if event.ui_element == self.test_slider:
                        # can send serial command here!
                        mcu_serial_object.write(bytes("bb {} 51\n".format(sendval_a), 'utf-8'))
                        time.sleep(0.002)
                        mcu_serial_object.write(bytes("bb {} 53\n".format(sendval_b), 'utf-8'))
                        time.sleep(0.002)
                    elif event.ui_element == self.slider2:
                        mcu_serial_object.write(bytes("bb {} 52\n".format(sendval_a), 'utf-8'))
                        time.sleep(0.002)
                        mcu_serial_object.write(bytes("bb {} 54\n".format(sendval_b), 'utf-8'))
                        time.sleep(0.002)
                    elif event.ui_element == self.slider3:
                        mcu_serial_object.write(bytes("bb {} 55\n".format(sendval_a), 'utf-8'))
                        time.sleep(0.002)
                        mcu_serial_object.write(bytes("bb {} 57\n".format(sendval_b), 'utf-8'))
                        time.sleep(0.002)
                    elif event.ui_element == self.slider4:
                        mcu_serial_object.write(bytes("bb {} 56\n".format(sendval_a), 'utf-8'))
                        time.sleep(0.002)
                        mcu_serial_object.write(bytes("bb {} 58\n".format(sendval_b), 'utf-8'))
                        time.sleep(0.002)
                    

            

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.serial_connect_button:
                    try:
                        print("--Connecting to {}".format(self.serial_select_dropdown.selected_option))
                        conn_baud = int(self.serial_baudrate_textbox.get_text())
                        mcu_serial_object = serial.Serial(port=self.serial_select_dropdown.selected_option, baudrate=conn_baud, timeout=.1)
                    except:
                        print("--Connection failed")
                    else:
                        print("--Connected")

                if event.ui_element == self.serial_refresh_button:
                    try:
                        self.serial_select_dropdown.options_list = ['not selected']
                        ports = serial.tools.list_ports.comports()
                        for port, desc, hwid in sorted(ports):
                                self.serial_select_dropdown.add_options([str(port)])
                    except:
                        print("i don't know why but refresing failed")
                    
            if (event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED):
                if (event.ui_element == self.test_drop_down):
                    self.check_resolution_changed()
                if (event.ui_element == self.serial_monitor_mode):
                    # ['In app', 'In terminal', 'Disable']
                    if self.serial_monitor_mode.selected_option == 'In app':
                        enable_serial_monitor = 1
                    elif self.serial_monitor_mode.selected_option == 'In terminal':
                        enable_serial_monitor = 2
                    elif self.serial_monitor_mode.selected_option == 'Disable':
                        enable_serial_monitor = 0
                    else:
                        enable_serial_monitor = 0

    def run(self):
        global joysticks
        global enable_serial_monitor
        global mcu_serial_object
        global serial_log_file
        global serial_msg_text

        global context
        global socket

        serial_msg_text_size = 200

        while self.running:
            time_delta = self.clock.tick() / 1000.0
            self.time_delta_stack.append(time_delta)
            if len(self.time_delta_stack) > 2000:
                self.time_delta_stack.popleft()
            # check for input
            self.process_events()
            # respond to input
            self.ui_manager.update(time_delta)
            # draw graphics
            self.window_surface.blit(self.background_surface, (0, 0))
            self.ui_manager.draw_ui(self.window_surface)

            # Xbox Controller
            if len(joysticks) >0:
                joystick = joysticks[0]
                axes = joystick.get_numaxes()
                axis_list = [0]*axes
                for i in range(axes):
                    axis_list[i] = joystick.get_axis(i)
                    # print(f"Axis {i} value: {axis:>6.3f}", end="")

                js_display_travel = 10

                L_tr = axis_list[4]
                R_tr = axis_list[5]

                L_tr_base_pos = (self.options.resolution[0]*0.09, -js_display_travel+self.options.resolution[1] * 0.95)
                R_tr_base_pos = (self.options.resolution[0]*0.12, -js_display_travel+self.options.resolution[1] * 0.95)

                L_tr_center_pos = (L_tr_base_pos[0], js_display_travel*L_tr+self.options.resolution[1] * 0.95)
                R_tr_center_pos = (R_tr_base_pos[0], js_display_travel*R_tr+self.options.resolution[1] * 0.95)

                L_tr_rect = pygame.Rect(L_tr_center_pos, (20,5))
                R_tr_rect = pygame.Rect(R_tr_center_pos, (20,5))

                L_tr_base_rect = pygame.Rect(L_tr_base_pos, (20,25))
                R_tr_base_rect = pygame.Rect(R_tr_base_pos, (20,25))

                L_js = (axis_list[0],axis_list[1])
                R_js = (axis_list[2],axis_list[3])

                L_js_base_pos = (self.options.resolution[0]*0.03, self.options.resolution[1] * 0.95)
                R_js_base_pos = (self.options.resolution[0]*0.06, self.options.resolution[1] * 0.95)
                L_js_center_pos = (js_display_travel*L_js[0]+L_js_base_pos[0], js_display_travel*L_js[1]+L_js_base_pos[1])
                R_js_center_pos = (js_display_travel*R_js[0]+R_js_base_pos[0], js_display_travel*R_js[1]+R_js_base_pos[1])


                pygame.draw.rect(self.window_surface, (200, 200, 200), L_tr_base_rect)
                pygame.draw.rect(self.window_surface, (200, 200, 200), R_tr_base_rect)

                pygame.draw.rect(self.window_surface, (255, 255, 255), L_tr_rect)
                pygame.draw.rect(self.window_surface, (255, 255, 255), R_tr_rect)
                
                pygame.draw.circle(self.window_surface, (200, 200, 200), L_js_base_pos, 20)
                pygame.draw.circle(self.window_surface, (200, 200, 200), R_js_base_pos, 20)

                pygame.draw.circle(self.window_surface, (255, 255, 255), L_js_center_pos, 10)
                pygame.draw.circle(self.window_surface, (255, 255, 255), R_js_center_pos, 10)
                
                # print(">")

            pygame.display.update()

            # pyserial
            if (enable_serial_monitor != 0) and (mcu_serial_object is not None):
                numBytesToRead = mcu_serial_object.in_waiting
                if(numBytesToRead > 0):
                    line_readed = mcu_serial_object.readline()
                    serial_log_file.write(str(line_readed)+'\n')
                    if enable_serial_monitor == 1: # in app option
                        serial_msg_text += (str(line_readed)+'\n')
                        self.serial_msg_disp.appended_text += (str(line_readed)+'\n')
                        self.serial_msg_disp.set_text(serial_msg_text)
                        if self.serial_msg_disp.get_text_letter_count() > serial_msg_text_size:
                            diff = self.serial_msg_disp.get_text_letter_count()
                            serial_msg_text = serial_msg_text[diff:]
                        
                        if self.serial_msg_disp.scroll_bar is not None:
                            # set the scroll bar to the bottom
                            percentage_visible = (self.serial_msg_disp.text_wrap_rect[3] /
                                                self.serial_msg_disp.text_box_layout.layout_rect.height)
                            self.serial_msg_disp.scroll_bar.start_percentage = 1.0 - percentage_visible
                            self.serial_msg_disp.scroll_bar.scroll_position = (self.serial_msg_disp.scroll_bar.start_percentage *
                                                            self.serial_msg_disp.scroll_bar.scrollable_height)
                            self.serial_msg_disp.redraw_from_text_block()
                    if enable_serial_monitor == 2: # in terminal option
                        print(line_readed)
                    
                    
def open_serial_log(log_path="./serial_log"):
    global serial_log_file
    
    dir_list = os.listdir(log_path)
    dir_list = [f for f in dir_list if os.path.isfile(log_path+'/'+f)]

    largest_index = 0

    for each_log in dir_list:
        # getting numbers from string 
        temp = re.findall(r'\d+', each_log)
        res = list(map(int, temp))
        largest_index = max([largest_index, res[0]])

    serial_log_file = open(log_path + '/serial_log_' + str(largest_index+1) + '.txt', 'w')


if __name__ == '__main__':
    ports = serial.tools.list_ports.comports()
    open_serial_log()
    for port, desc, hwid in sorted(ports):
            print("{}: [{}]".format(port, hwid))

    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
    print(joysticks)    
    app = OptionsUIApp()
    app.run()
