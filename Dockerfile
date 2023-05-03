# Use a Raspberry Pi-based Python runtime as a parent image
FROM balenalib/raspberrypi3-python:3.8

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN install_packages gcc python3-dev libraspberrypi-bin && \
    python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=app.py

# Run the command to start the app
CMD ["flask", "run", "--host=0.0.0.0"]
