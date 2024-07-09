# Use a base image with Ubuntu
FROM ubuntu:22.04

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt file to the container
COPY requirements.txt requirements.txt

# Install dependencies from requirements.txt
RUN apt-get update && apt-get install -y python3-pip && pip install -r requirements.txt

# Copy the entire app directory to the container
COPY . .

# Expose the port the Flask app will run on
EXPOSE 5000

ENV PATH="/usr/lib:$PATH"
# Set the environment variable FLASK_APP to point to the app file
ENV FLASK_APP=flask_app.py

# Define the command to run when the container starts
CMD ["python3", "flask_app.py"]




