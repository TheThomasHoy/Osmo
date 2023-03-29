from flask import Flask, render_template, Response
import RPi.GPIO as GPIO
import time 
import Adafruit_ADS1x15 
import math
import cv2
from flask import Flask, Response, render_template

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

# Define generator function for video frames
def gen_frames():
    # OpenCV video camera object
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Encoding the image in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Yield the frame in bytes
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Return the response with the video stream embedded in the HTML template
@app.route('/camera')
def camera_object():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Flask route for camera stream
@app.route('/')
def index():
    return render_template('stream.html')

if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=5000, debug=True)
