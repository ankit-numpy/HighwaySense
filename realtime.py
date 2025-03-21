import cv2 as cv
import numpy as np
import os
import streamlit as st
import pandas as pd
import geocoder
from datetime import datetime
from PIL import Image

st.title("Real-Time Pothole Detection App")

start_button = st.button("Start Capture")
stop_button = st.button("Stop Capture")

capture = False
if start_button:
    capture = True
if stop_button:
    capture = False

try:
    class_name = []
    with open(r'utils/obj.names', 'r') as f:
        class_name = [cname.strip() for cname in f.readlines()]

    net = cv.dnn.readNet(r'utils/yolov4_tiny.weights', r'utils/yolov4_tiny.cfg')
    net.setPreferableBackend(cv.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv.dnn.DNN_TARGET_CUDA_FP16)
    model = cv.dnn_DetectionModel(net)
    model.setInputParams(size=(640, 480), scale=1/255, swapRB=True)

    cap = cv.VideoCapture(0)  # Open the default camera
    if not cap.isOpened():
        st.error("Could not open camera")
        st.stop()

    Conf_threshold = 0.5
    NMS_threshold = 0.4
    pothole_data_file = "pothole_data.csv"

    stframe = st.image([])

    while capture:
        ret, frame = cap.read()
        if not ret:
            break

        classes, scores, boxes = model.detect(frame, Conf_threshold, NMS_threshold)
        for (classid, score, box) in zip(classes, scores, boxes):
            label = "pothole"
            x, y, w, h = box
            recarea = w * h
            area = frame.shape[0] * frame.shape[1]

            severity = ""
            severity_threshold_low = 0.007  # Adjust as needed
            severity_threshold_medium = 0.020  # Adjust as needed

            if len(scores) != 0 and scores[0] >= 0.7:
                if (recarea / area) <= severity_threshold_low:
                    severity = "Low"
                elif (recarea / area) <= severity_threshold_medium:
                    severity = "Medium"
                else:
                    severity = "High"

                if severity:
                    cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv.putText(frame, f"{label} ({severity} Severity)",
                               (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    
                    # Get timestamp
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Get latitude and longitude
                    g = geocoder.ip('me')
                    lat, lng = g.latlng if g.latlng else ("N/A", "N/A")
                    
                    # Append data to CSV file
                    pothole_data = pd.DataFrame([[lat, lng, severity, timestamp]],
                                                columns=["Latitude", "Longitude", "Severity", "Timestamp"])
                    if not os.path.exists(pothole_data_file):
                        pothole_data.to_csv(pothole_data_file, index=False)
                    else:
                        pothole_data.to_csv(pothole_data_file, mode='a', header=False, index=False)
        
        frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        stframe.image(frame_rgb, channels="RGB")

except Exception as e:
    st.error(f"Error: {e}")
finally:
    cap.release()
    #cv.destroyAllWindows()
