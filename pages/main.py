



import streamlit as st
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials
import os

def detect_pothole(image, endpoint, prediction_key, project_id, model_name):
    """
    Detect potholes in an image using Azure Custom Vision object detection model.
    
    :param image: Image file object.
    :param endpoint: Azure Custom Vision prediction endpoint.
    :param prediction_key: Azure Custom Vision prediction key.
    :param project_id: Azure Custom Vision project ID.
    :param model_name: The name of the published model.
    :return: List of detected potholes with confidence scores and bounding boxes.
    """
    credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
    predictor = CustomVisionPredictionClient(endpoint, credentials)
    
    results = predictor.detect_image(project_id, model_name, image.read())  # Updated for object detection
    
    detections = []
    for prediction in results.predictions:
        if prediction.probability > 0.5:
            detections.append({
                "tag": prediction.tag_name,
                "confidence": prediction.probability,
                "bounding_box": prediction.bounding_box
            })
    
    return detections

# Streamlit UI
st.title("Pothole Detection Web App")

import streamlit as st

st.title("Main App")
st.write("Use the sidebar to navigate.")

st.sidebar.page_link("pages/realtime.py", label="Go to Secondary Page")


# Azure credentials
AZURE_ENDPOINT = "https://ankitvision-prediction.cognitiveservices.azure.com/"
AZURE_PREDICTION_KEY = "BoeeJF2gTh4Lup5eqAYNBKgmuLLUrt593hYhoBaP7Of043bJG1CZJQQJ99BCACYeBjFXJ3w3AAAIACOGlxFr"
PROJECT_ID = "810d46f4-1131-4536-994f-c8b754cc0ffa"
MODEL_NAME = "Iteration1"

uploaded_file = st.file_uploader("Upload an image of a road", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
    st.write("Detecting potholes...")
    
    results = detect_pothole(uploaded_file, AZURE_ENDPOINT, AZURE_PREDICTION_KEY, PROJECT_ID, MODEL_NAME)
    
    if results:
        st.write("### Potholes detected:")
        for res in results:
            st.write(f"**{res['tag']}**: {res['confidence']*100:.2f}% confidence")
            st.write(f"Bounding Box: Left: {res['bounding_box'].left:.2f}, Top: {res['bounding_box'].top:.2f}, Width: {res['bounding_box'].width:.2f}, Height: {res['bounding_box'].height:.2f}")
    else:
        st.write("No potholes detected.")

