import cv2
import os
import time
import threading
import RPi.GPIO as GPIO
import Adafruit_ADS1x15 
from flask import Flask, Response, render_template, jsonify

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static')

cap = cv2.VideoCapture(0)
stream_running = False
adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)

GAIN = 1
PIN = 7

def setup():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIN, GPIO.OUT)
    GPIO.output(PIN, GPIO.HIGH)
    time.sleep(0.1)

values = [0]*100

def gen_frames():
    while stream_running:
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
def index():
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
    success, frame = cap.read()
    if success:
        filename = 'screenshot_{}.jpg'.format(int(time.time()))
        cv2.imwrite(os.path.join(app.static_folder, 'screenshots', filename), frame)
        app.logger.info('Screenshot saved as {}'.format(filename))
        message = 'Screenshot saved as {}'.format(filename)
        button = '<button onclick="location.href=\'/\'">Back to Osmo Dashboard</button>'
        return message + '<br>' + button
    else:
        return 'Error taking screenshot'

@app.route('/data')
def data():
    moisture = max(values)
    pump_status = 'on' if GPIO.input(PIN) == 0 else 'off'
    return jsonify(moisture=moisture, pump_status=pump_status)

def loop():
    while True:
        for i in range(100):
            values[i]=adc.read_adc(0,gain=GAIN)
        print(max(values))

        if max(values) > 21400: 
            GPIO.output(PIN, GPIO.LOW)
           # print("Pump is on") 
           # print(PIN)
            time.sleep(0.1)
        else:
            GPIO.output(PIN, GPIO.HIGH)
           # print("Pump is off")
           # print(PIN)
            time.sleep(0.1)

def destroy():
    GPIO.output(PIN, GPIO.HIGH)
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        loop_thread = threading.Thread(target=loop)
        loop_thread.start()
        app.run(host='0.0.0.0', port=5000, debug=True)
        stream_running = False
        loop_thread.join()
    except KeyboardInterrupt:
        print("Keyboard interrupt detected.")
    finally:
        destroy()
