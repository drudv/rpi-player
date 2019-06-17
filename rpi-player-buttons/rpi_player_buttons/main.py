import RPi.GPIO as GPIO
from queue import Queue
from .mopidy import Mopidy, TASK_TOGGLE, TASK_VOLUME_UP, TASK_VOLUME_DOWN, TASK_QUIT
import time
import argparse
import queue
import threading

BUTTON_POLL_INTERVAL = 0.1

q = queue.Queue()

class Button:
    def __init__(self, code, action, long_press_threshold, long_press_iteration):
        self.code = code
        self.action = action
        self.is_pressed = False
        self.long_press_threshold = long_press_threshold
        self.long_press_iteration = long_press_iteration
        self.same_state_ticks = 0
        GPIO.setup(code, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def poll(self):
        self.set_state(GPIO.input(self.code) == False)

    def set_state(self, is_pressed):
        if self.is_pressed != is_pressed:
            self.same_state_ticks = 0
        else:
            self.same_state_ticks += 1
        self.is_pressed = is_pressed
        if is_pressed and self.should_launch_action():
            print('Launch by code', self.code)
            self.action()

    def should_launch_action(self):
        if self.same_state_ticks == 0:
            return True
        if self.same_state_ticks >= self.long_press_threshold:
            ticks_after_threshold = self.same_state_ticks - self.long_press_threshold
            if ticks_after_threshold % self.long_press_iteration == 0:
                return True
        return False


def mopidy_client_worker(queue):
    mopidy = Mopidy(queue=queue)
    mopidy.run()


def main():
    parser = argparse.ArgumentParser(description='Handle music player buttons.')
    parser.add_argument('--gpio-pause', type=int, required=True, help='GPIO number of Pause/Resume button')
    parser.add_argument('--gpio-volume-up', type=int, required=True, help='GPIO number of Volume Up button')
    parser.add_argument('--gpio-volume-down', type=int, required=True, help='GPIO number of Volume Down button')
    args = parser.parse_args()

    q = Queue()
    mopidy_client_thread = threading.Thread(target=mopidy_client_worker, args=(q,))
    mopidy_client_thread.start()

    GPIO.setmode(GPIO.BCM)

    def task_toggle():
        q.put(TASK_TOGGLE)
    def task_volume_up():
        q.put(TASK_VOLUME_UP)
    def task_volume_down():
        q.put(TASK_VOLUME_DOWN)

    pause_button = Button(
        code=args.gpio_pause,
        action=task_toggle,
        long_press_threshold=10,
        long_press_iteration=3)
    volume_up_button = Button(
        code=args.gpio_volume_up,
        action=task_volume_up,
        long_press_threshold=10,
        long_press_iteration=3)
    volume_down_button = Button(
        code=args.gpio_volume_down,
        action=task_volume_down,
        long_press_threshold=10,
        long_press_iteration=3)

    try:
        while True:
            pause_button.poll()
            volume_up_button.poll()
            volume_down_button.poll()
            time.sleep(BUTTON_POLL_INTERVAL)
    except KeyboardInterrupt:
        q.put(TASK_QUIT)
    mopidy_client_thread.join()

if __name__ == "__main__":
    main()
