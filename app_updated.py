import streamlit as st
import cv2 as cv
import numpy as np
import pandas as pd
import os
import geocoder
from datetime import datetime
import requests
import json

def get_location():
    """
    Get the current location using multiple methods for better accuracy.
    Falls back to IP-based location if more precise methods fail.
    """
    try:
        # Try to get location from browser (only works in Streamlit)
        if st.session_state.get('location') is None:
            # This will prompt the user for location permission in the browser
            st.session_state['location_requested'] = True
            
            # Add JavaScript to get location
            st.markdown(
                """
                <script>
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            const lat = position.coords.latitude;
                            const lon = position.coords.longitude;
                            // Store in sessionStorage
                            sessionStorage.setItem('user_lat', lat);
                            sessionStorage.setItem('user_lon', lon);
                            // Force refresh to pick up the new values
                            window.location.reload();
                        },
                        function(error) {
                            console.error("Error getting location:", error);
                        }
                    );
                }
                </script>
                """,
                unsafe_allow_html=True
            )
            
            # Try to read from query parameters using the updated method
            try:
                lat = st.query_params.get('lat', None)
                lon = st.query_params.get('lon', None)
                
                if lat and lon:
                    return float(lat), float(lon)
            except Exception as e:
                st.warning(f"Could not get location from query params: {e}")
    except Exception as e:
        st.warning(f"Could not get precise location: {e}")
    
    # Fallback to IP-based location
    try:
        # Try using ipinfo.io for more accurate IP-based location
        response = requests.get('https://ipinfo.io/json')
        if response.status_code == 200:
            data = response.json()
            if 'loc' in data:
                lat, lon = data['loc'].split(',')
                return float(lat), float(lon)
    except Exception as e:
        st.warning(f"Could not get location from ipinfo.io: {e}")
    
    # Final fallback to geocoder
    g = geocoder.ip('me')
    if g.latlng:
        return g.latlng[0], g.latlng[1]
    
    # If all methods fail, return a default location
    return 28.6139, 77.2090  # Default to New Delhi coordinates

def process_image(image):
    class_name = []
    with open(r'utils/obj.names', 'r') as f:
        class_name = [cname.strip() for cname in f.readlines()]
    
    net = cv.dnn.readNet(r'utils/yolov4_tiny.weights', r'utils/yolov4_tiny.cfg')
    model = cv.dnn_DetectionModel(net)
    model.setInputParams(size=(640, 480), scale=1/255, swapRB=True)
    
    height, width, _ = image.shape
    image_area = height * width
    total_pothole_area = 0
    
    classes, scores, boxes = model.detect(image, 0.5, 0.4)
    
    # Get current location
    lat, lon = get_location()
    pothole_list = []
    
    # Get current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for (classid, score, box) in zip(classes, scores, boxes):
        label = "pothole"
        x, y, w, h = box
        pothole_area = w * h
        total_pothole_area += pothole_area
        
        severity = "High" if (pothole_area / image_area) > 0.02 else "Medium" if (pothole_area / image_area) > 0.007 else "Low"
        
        cv.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv.putText(image, f"{label} ({severity})", (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Add timestamp to the pothole data
        pothole_list.append([lat, lon, pothole_area, severity, timestamp])
    
    pothole_data = pd.DataFrame(pothole_list, columns=["Latitude", "Longitude", "Pothole Area (pixels)", "Severity", "Timestamp"])
    return image, pothole_data

def process_video(video_path):
    class_name = []
    with open(r'utils/obj.names', 'r') as f:
        class_name = [cname.strip() for cname in f.readlines()]
    
    net = cv.dnn.readNet(r'utils/yolov4_tiny.weights', r'utils/yolov4_tiny.cfg')
    model = cv.dnn_DetectionModel(net)
    model.setInputParams(size=(640, 480), scale=1/255, swapRB=True)
    
    cap = cv.VideoCapture(video_path)
    ret, frame = cap.read()
    if not ret:
        st.error("Failed to load video.")
        return None
    
    width = int(cap.get(3))
    height = int(cap.get(4))
    result = cv.VideoWriter('result.avi', cv.VideoWriter_fourcc(*'MJPG'), 10, (width, height))
    
    # Get current location
    lat, lon = get_location()
    pothole_list = []
    
    # Get current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        classes, scores, boxes = model.detect(frame, 0.5, 0.4)
        for (classid, score, box) in zip(classes, scores, boxes):
            label = "pothole"
            x, y, w, h = box
            pothole_area = w * h
            
            severity = "High" if (pothole_area / (width * height)) > 0.02 else "Medium" if (pothole_area / (width * height)) > 0.007 else "Low"
            
            cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv.putText(frame, f"{label} ({severity})", (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # Add pothole to list - only add unique potholes (simple approach: check if box coordinates are different)
            # This is a simple approach to avoid duplicates from the same video frame
            if not any(abs(x-prev_x) < 10 and abs(y-prev_y) < 10 for prev_x, prev_y, _, _ in [box_data[2:6] for box_data in pothole_list]):
                pothole_list.append([lat, lon, pothole_area, severity, timestamp])
        
        result.write(frame)
    
    cap.release()
    result.release()
    cv.destroyAllWindows()
    
    # Create DataFrame from pothole list
    if pothole_list:
        pothole_data = pd.DataFrame(pothole_list, columns=["Latitude", "Longitude", "Pothole Area (pixels)", "Severity", "Timestamp"])
        return pothole_data
    return None

def process_camera():
    class_name = []
    with open(r'utils/obj.names', 'r') as f:
        class_name = [cname.strip() for cname in f.readlines()]
    
    net = cv.dnn.readNet(r'utils/yolov4_tiny.weights', r'utils/yolov4_tiny.cfg')
    model = cv.dnn_DetectionModel(net)
    model.setInputParams(size=(640, 480), scale=1/255, swapRB=True)
    
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        st.error("Failed to open camera.")
        return None
    
    width = int(cap.get(3))
    height = int(cap.get(4))
    
    # Get current location
    lat, lon = get_location()
    pothole_list = []
    
    # Get current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    stframe = st.empty()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        classes, scores, boxes = model.detect(frame, 0.5, 0.4)
        for (classid, score, box) in zip(classes, scores, boxes):
            label = "pothole"
            x, y, w, h = box
            pothole_area = w * h
            
            severity = "High" if (pothole_area / (width * height)) > 0.02 else "Medium" if (pothole_area / (width * height)) > 0.007 else "Low"
            
            cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv.putText(frame, f"{label} ({severity})", (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # Add pothole to list - only add unique potholes (simple approach: check if box coordinates are different)
            if not any(abs(x-prev_x) < 10 and abs(y-prev_y) < 10 for prev_x, prev_y, _, _ in [box_data[2:6] for box_data in pothole_list]):
                pothole_list.append([lat, lon, pothole_area, severity, timestamp])
        
        stframe.image(frame, channels="BGR")
        
        if st.button("Stop Detection", key="stop_detection"):
            break
    
    cap.release()
    cv.destroyAllWindows()
    
    # Create DataFrame from pothole list
    if pothole_list:
        pothole_data = pd.DataFrame(pothole_list, columns=["Latitude", "Longitude", "Pothole Area (pixels)", "Severity", "Timestamp"])
        return pothole_data
    return None

def main():
    # Initialize session state for location
    if 'location' not in st.session_state:
        st.session_state['location'] = None
    if 'location_requested' not in st.session_state:
        st.session_state['location_requested'] = False
    
    st.title("Pothole Detection System")
    st.write("Upload an image or video to detect potholes using YOLOv4 Tiny.")
    
    # Display current location information
    lat, lon = get_location()
    st.sidebar.write(f"Current Location: {lat:.6f}, {lon:.6f}")
    st.sidebar.write("Note: For more accurate location, please allow location access in your browser.")
    st.sidebar.page_link("realtime.py", label="Go to Report a POTHOLE")
    st.sidebar.page_link("visualize_potholes.py", label="Go to Map")
    option = st.radio("Select Input Type", ("Image", "Video", "Real-time Camera"))
    
    if option == "Image":
        uploaded_image = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
        if uploaded_image is not None:
            image = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            image = cv.imdecode(image, cv.IMREAD_COLOR)
            processed_image, pothole_data = process_image(image)
            # AREA CALCULATION
            st.table(pothole_data)
            height, width, _ = image.shape
            image_area = height * width
            total_pothole_area = pothole_data["Pothole Area (pixels)"].sum()
            st.write("Area % to maintain:",(total_pothole_area/image_area)*100 )
            st.image(processed_image, channels="BGR", caption="Processed Image")
            
            _, img_encoded = cv.imencode(".jpg", processed_image)
            st.download_button(
                label="Download Processed Image",
                data=img_encoded.tobytes(),
                file_name="processed_image.jpg",
                mime="image/jpeg"
            )
            
            # Save CSV - MODIFIED TO APPEND DATA
            csv_path = "pothole_data.csv"
            
            # Check if file exists and append data
            if os.path.exists(csv_path):
                existing_data = pd.read_csv(csv_path)
                # Append new data
                updated_data = pd.concat([existing_data, pothole_data], ignore_index=True)
                updated_data.to_csv(csv_path, index=False)
                st.success(f"Added {len(pothole_data)} new pothole records to the database")
            else:
                # Create new file if it doesn't exist
                pothole_data.to_csv(csv_path, index=False)
                st.success(f"Created new database with {len(pothole_data)} pothole records")
            
            # Provide download option for the updated CSV
            with open(csv_path, "rb") as f:
                st.download_button(
                    label="Download Pothole Data CSV",
                    data=f,
                    file_name="pothole_data.csv",
                    mime="text/csv"
                )
    
    elif option == "Video":
        uploaded_file = st.file_uploader("Upload Video", type=["mp4", "avi", "mov"])
        if uploaded_file is not None:
            temp_video_path = "uploaded_video.mp4"
            with open(temp_video_path, "wb") as f:
                f.write(uploaded_file.read())
            
            if st.button("Run Detection", key="run_detection_video"):
                pothole_data = process_video(temp_video_path)
                
                # Save CSV - MODIFIED TO APPEND DATA FROM VIDEO
                if pothole_data is not None and not pothole_data.empty:
                    csv_path = "pothole_data.csv"
                    
                    # Check if file exists and append data
                    if os.path.exists(csv_path):
                        existing_data = pd.read_csv(csv_path)
                        # Append new data
                        updated_data = pd.concat([existing_data, pothole_data], ignore_index=True)
                        updated_data.to_csv(csv_path, index=False)
                        st.success(f"Added {len(pothole_data)} new pothole records to the database")
                    else:
                        # Create new file if it doesn't exist
                        pothole_data.to_csv(csv_path, index=False)
                        st.success(f"Created new database with {len(pothole_data)} pothole records")
                
                st.video("result.avi")
                
                with open("result.avi", "rb") as file:
                    st.download_button(
                        label="Download Processed Video",
                        data=file,
                        file_name="processed_video.avi",
                        mime="video/avi"
                    )
    
    elif option == "Real-time Camera":
        if st.button("Start Detection", key="start_detection_camera"):
            pothole_data = process_camera()
            
            # Save CSV - MODIFIED TO APPEND DATA FROM CAMERA
            if pothole_data is not None and not pothole_data.empty:
                csv_path = "pothole_data.csv"
                
                # Check if file exists and append data
                if os.path.exists(csv_path):
                    existing_data = pd.read_csv(csv_path)
                    # Append new data
                    updated_data = pd.concat([existing_data, pothole_data], ignore_index=True)
                    updated_data.to_csv(csv_path, index=False)
                    st.success(f"Added {len(pothole_data)} new pothole records to the database")
                else:
                    # Create new file if it doesn't exist
                    pothole_data.to_csv(csv_path, index=False)
                    st.success(f"Created new database with {len(pothole_data)} pothole records")
                
                # Provide download option for the updated CSV
                with open(csv_path, "rb") as f:
                    st.download_button(
                        label="Download Pothole Data CSV",
                        data=f,
                        file_name="pothole_data.csv",
                        mime="text/csv"
                    )

if __name__ == "__main__":
    main()


