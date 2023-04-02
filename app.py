from flask import Flask, render_template, Response
import RPi.GPIO as GPIO
import time 
import Adafruit_ADS1x15 
import math
import cv2

app = Flask(__name__)

adc = Adafruit_ADS1x15.ADS1115(address=0x48, busnum=1)
GAIN = 1
PIN = 7

def setup():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(PIN, GPIO.OUT)
    GPIO.output(PIN, GPIO.HIGH)
    time.sleep(0.1)

def read_moisture():
    values = [0]*100
    for i in range(100):
        values[i] = adc.read_adc(0, gain=GAIN)
    return max(values)

def gen_frames():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Encoding the image in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    moisture_level = read_moisture()
    if moisture_level > 21400:
        GPIO.output(PIN, GPIO.LOW)
        pump_status = 'on'
    else:
        GPIO.output(PIN, GPIO.HIGH)
        pump_status = 'off'
    return render_template('index.html', moisture_level=moisture_level, pump_status=pump_status)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=5000, debug=True)
