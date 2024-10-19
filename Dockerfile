# Step 1: Use an official Python runtime as the base image
FROM python:3.12-slim

# Step 2: Set the working directory in the container
WORKDIR /app

# Install necessary system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0

# Step 3: Copy the current directory contents into the container at /app
COPY . /app

# Step 4: Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Make port 5000 available to the world outside this container
EXPOSE 2325

# Step 6: Set environment variables for Flask
ENV FLASK_APP=app
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=2325

# Step 7: Run the Flask app when the container launches
CMD ["flask", "run"]
