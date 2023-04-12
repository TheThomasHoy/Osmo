import cv2
import os # Allows Python application to interact with the running operating system
import time
from flask import Flask, Response, render_template
from flask_apscheduler import APScheduler
import threading

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static')

# OpenCV video camera object
cap = cv2.VideoCapture(0)
stream_running = False

# Initialize scheduler object
scheduler = APScheduler()

# Create instance of the Lock class from the threading library
lock = threading.Lock()

# Define generator function for video frames
def gen_frames():
    while stream_running:
        success, frame = cap.read()
        if not success:
            break
        # Encode the frame as JPEG
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
    return render_template('stream.html', stream_running=stream_running)

# Flask route for starting camera stream
@app.route('/start_stream', methods=['POST'])
def start_stream():
    global stream_running
    stream_running = True
    return render_template('stream.html', stream_running=stream_running)

# Flask route for stopping camera stream
@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global stream_running
    stream_running = False
    return render_template('stream.html', stream_running=stream_running)

# Flask route for taking a screenshot
@app.route('/take_screenshot', methods=['POST'])
def take_screenshot():
    # Take a screenshot by reading a single frame from the video capture object (camera stream)
    success, frame = cap.read()
    if success:
        # Generate a filename with a timestamp (integer timestamp of seconds after Unix epoch)
        filename = 'screenshot_{}.jpg'.format(int(time.time()))
        # Save the screenshot to a file
        # os.path.join - Joins Flask application's 'static_folder' directory, screenshots subdirectory,
        # and filename generated with a timestamp
        cv2.imwrite(os.path.join(app.static_folder, 'screenshots', filename), frame)
        # Log the event that the screenshot was saved with its filename
        app.logger.info('Screenshot saved as {}'.format(filename))
        # Render a message to indicate that the screenshot has been saved with its filename
        message = 'Screenshot saved as {}'.format(filename)
        # Render a button to take the user back to the main page
        button = '<button onclick="location.href=\'/\'">Back to Osmo Dashboard</button>'
        return message + '<br>' + button
    else:
        return 'Error taking screenshot'

scheduler.add_job(id='automate_screenshot', func=lambda: threading.Thread(target=take_screenshot).start(), trigger="interval", minutes=30)
scheduler.start()

if __name__ == '__main__':
    # Create separate threads for the camera stream and the scheduler
    camera_thread = threading.Thread(target=app.run, args=('localhost', 5000))
    scheduler_thread = threading.Thread(target=scheduler.start)

    # Start the camera and scheduler threads
    camera_thread.start()
    scheduler_thread.start()

    # Wait for the camera and scheduler threads to complete
    camera_thread.join()
    scheduler_thread.join()