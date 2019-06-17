import websocket
import json
import time
import threading
from queue import Queue, Empty

REQUEST_TIMEOUT = 20 # sec
PING_INTERVAL = 30 # sec
RECONNECT_INTERVAL = 1 # sec

TASK_QUIT = 'QUIT'
TASK_TOGGLE = 'TOGGLE'
TASK_VOLUME_UP = 'VOLUME_UP'
TASK_VOLUME_DOWN = 'VOLUME_DOWN'

class MopidyRequest:
    def __init__(self, data, on_success):
        self.data = data
        self.on_success = on_success
        self.start_time = time.time()
        self.expiration_time = self.start_time + REQUEST_TIMEOUT

    def is_expired(self):
        return time.time() > self.expiration_time

    def handle_success(self, result):
        if self.on_success:
            self.on_success(result)

class Mopidy:
    ws = None
    ws_thread = None
    volume = 50
    next_request_id = 1
    is_connected = False
    is_playing = False
    last_connect_time = None
    last_request_time = None
    requests = {}

    def __init__(self, queue):
        self.queue = queue

    def send_request(self, method, params = {}, on_success = None):
        self.last_request_time = time.time()
        if self.ws is None and self.is_connected:
            print('Mopidy is not connected. Request ignored.')
            return
        request_id = self.get_next_request_id()
        data = {
            'id': request_id,
            'jsonrpc': '2.0',
            'method': method,
            'params': params
        }
        self.ws.send(json.dumps(data))
        self.requests[request_id] = MopidyRequest(data=data, on_success=on_success)

    def get_next_request_id(self):
        request_id = self.next_request_id
        self.next_request_id += 1
        return request_id

    def handle_event(self, data):
        event = data['event']
        if event == 'volume_changed':
            self.save_volume(data['volume'])
        elif event == 'playback_state_changed':
            self.save_playing_status(data['new_state'] == 'playing')

    def handle_message(self, ws, message):
        try:
            data = json.loads(message)
        except Exception as ex:
            print("Can't parse payload", ex)
            return
        if 'event' in data:
            self.handle_event(data)
            return
        request = self.requests.get(data['id'])
        if request is None:
            print('Response to unknown request:', message)
            return
        request.handle_success(data['result'])
        self.remove_request(data['id'])

    def check_expired_requests(self):
        expired_requests = [k for k, v in self.requests.items() if v.is_expired()]
        for k in expired_requests:
            print('Expired request: {} with data={}'.format(k, str(self.requests[k].data)))
            self.remove_request(k)

    def handle_task(self, task):
        if task == TASK_VOLUME_UP:
            self.change_volume(10)
        elif task == TASK_VOLUME_DOWN:
            self.change_volume(-10)
        elif task == TASK_TOGGLE:
            if self.is_playing:
                self.pause()
            else:
                self.resume()
        elif task == TASK_QUIT:
            if self.ws:
                self.ws.close()
                self.cleanup_connection()

    def handle_connection_success(self, ws):
        print('Connection success')
        self.is_connected = True
        self.get_volume()
        self.get_playing_status()

    def handle_connection_error(self, ws, error):
        print('Connection error', error)

    def handle_connection_close(self, ws):
        if self.ws:
            self.cleanup_connection()

    def handle_response_error(self, request_id):
        self.remove_request(request_id)

    def remove_request(self, request_id):
        del self.requests[request_id]

    def cleanup_connection(self):
        self.is_connected = False
        self.ws = None
        self.ws_thread.join()
        self.ws_thread = None

    def connect(self):
        def on_message(ws, message):
            self.handle_message(ws, message)
        def on_open(ws):
            self.handle_connection_success(ws)
        def on_close(ws):
            self.handle_connection_close(ws)
        def on_error(ws, error):
            self.handle_connection_error(ws, error)
        self.last_connect_time = time.time()
        self.ws = websocket.WebSocketApp("ws://localhost:6680/mopidy/ws",
            on_message=on_message,
            on_open=on_open,
            on_error=on_error,
            on_close=on_close)
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def get_volume(self):
        def on_success(volume):
            self.save_volume(volume)
        self.send_request(method='core.mixer.get_volume', on_success=on_success)

    def get_playing_status(self):
        def on_success(state):
            self.save_playing_status(state == 'playing')
        self.send_request(method='core.playback.get_state', on_success=on_success)

    def change_volume(self, diff):
        next_volume = self.volume + diff
        if next_volume > 100:
            next_volume = 100
        elif next_volume < 0:
            next_volume = 0
        self.volume = next_volume # optimistic update
        def on_success(result):
            pass
        self.send_request(method='core.mixer.set_volume', on_success=on_success, params=[next_volume,])

    def pause(self):
        def on_success(result):
            pass
        self.send_request(method='core.playback.pause', on_success=on_success)

    def resume(self):
        def on_success(result):
            pass
        self.send_request(method='core.playback.resume', on_success=on_success)

    def save_volume(self, volume):
        self.volume = volume

    def save_playing_status(self, is_playing):
        self.is_playing = is_playing

    def ping_if_necessary(self):
        if self.ws is not None and time.time() > self.last_request_time + PING_INTERVAL:
            self.get_playing_status()

    def reconnect_if_necessary(self):
        if self.ws is None and time.time() > self.last_connect_time + RECONNECT_INTERVAL:
            self.connect()

    def run(self):
        self.connect()
        while True:
            try:
                task = None
                try:
                    task = self.queue.get(block=True, timeout=0.1)
                except Empty:
                    pass
                if task is not None:
                    self.handle_task(task)
                    if task == TASK_QUIT:
                        break
                if self.ws is not None and self.is_connected:
                    self.check_expired_requests()
                    self.ping_if_necessary()
                else:
                    self.reconnect_if_necessary()
            except Exception as ex:
                print(ex)
