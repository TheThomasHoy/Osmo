"""
Copyright (C) <2023> <Thomas Hoy>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import cv2
import os
import time
import threading
from threading import Lock
import RPi.GPIO as GPIO
import Adafruit_ADS1x15
from flask import Flask, Response, render_template, jsonify
from concurrent.futures import ThreadPoolExecutor

gpio_lock = Lock()

stream_running = False

executor = ThreadPoolExecutor(max_workers=1)

lock = threading.Lock()

cap = cv2.VideoCapture(-1)
adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)

GAIN = 1
PIN = 7

values = [0]*100

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static')

def take_screenshot_periodically():
    global cap
    while True:
        time.sleep(1800)
        lock.acquire()
        success, frame = cap.read()
        lock.release()
        if success:
            filename = 'screenshot_{}.jpg'.format(int(time.time()))
            cv2.imwrite(os.path.join(app.static_folder, 'screenshots', filename), frame)
            app.logger.info('Screenshot saved as {}'.format(filename))
        else:
            cap = cv2.VideoCapture(-1)

screenshot_thread = threading.Thread(target=take_screenshot_periodically)
screenshot_thread.start()

def setup():
    with gpio_lock:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(PIN, GPIO.OUT)
        GPIO.output(PIN, GPIO.HIGH)
        time.sleep(0.1)

def gen_frames():
    global cap
    while stream_running:
        lock.acquire()
        success, frame = cap.read()
        lock.release()
        if not success:
            cap = cv2.VideoCapture(-1)
            success, frame = cap.read()
            if not success:
                break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/camera')
def camera_object():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    return render_template('index.html', stream_running=stream_running)

@app.route('/start_stream', methods=['POST'])
def start_stream():
    global stream_running
    stream_running = True
    return render_template('index.html', stream_running=stream_running)

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global stream_running
    stream_running = False
    return render_template('index.html', stream_running=stream_running)

@app.route('/take_screenshot', methods=['POST'])
def take_screenshot():
    global cap
    lock.acquire()
    success, frame = cap.read()
    lock.release()
    if success:
        filename = 'screenshot_{}.jpg'.format(int(time.time()))
        cv2.imwrite(os.path.join(app.static_folder, 'screenshots', filename), frame)
        app.logger.info('Screenshot saved as {}'.format(filename))
        message = 'Screenshot saved as {}'.format(filename)
        button = '<button onclick="location.href=\'/dashboard\'">Back to Osmo Dashboard</button>'
        return message + '<br>' + button
    else:
        cap = cv2.VideoCapture(-1)
        return 'Error taking screenshot'

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/get_screenshots')
def get_screenshots():
    screenshots_dir = os.path.join(app.static_folder, 'screenshots')
    screenshots = os.listdir(screenshots_dir)
    return jsonify(screenshots=screenshots)


@app.route('/data')
def data():
    moisture = max(values)
    pump_status = 'on' if GPIO.input(PIN) == 0 else 'off'
    return jsonify(moisture=moisture, pump_status=pump_status)

# ... imports and other code ...

@app.route('/turn_pump_on', methods=['POST'])
def turn_pump_on():
    global loop_enabled
    with gpio_lock:
        loop_enabled = False
        GPIO.output(PIN, GPIO.LOW)
        print("Pump is on")
    return "Pump turned on"

@app.route('/turn_pump_off', methods=['POST'])
def turn_pump_off():
    global loop_enabled
    with gpio_lock:
        loop_enabled = False
        GPIO.output(PIN, GPIO.HIGH)
        print("Pump is off")
    return "Pump turned off"

# ... other routes ...

loop_enabled = True

def loop():
    global loop_enabled
    while True:
        if loop_enabled:
            with gpio_lock:
                for i in range(100):
                    values[i] = adc.read_adc(0, gain=GAIN)
                if not loop_enabled:
                    continue
                if max(values) > 21400:
                    GPIO.output(PIN, GPIO.LOW)
                    time.sleep(0.1)
                else:
                    GPIO.output(PIN, GPIO.HIGH)
                    time.sleep(0.1)
        else:
            time.sleep(0.1)

# ... other functions and main block ...


def destroy():
    GPIO.output(PIN, GPIO.HIGH)
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        future = executor.submit(loop)
        app.run(host='0.0.0.0', port=5000)
        stream_running = False
        future.result()  # Wait for the loop() function to complete before exiting
    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    finally:
        destroy()
