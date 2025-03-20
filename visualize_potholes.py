import pandas as pd
import folium
from folium.plugins import MarkerCluster, LocateControl
import webbrowser
import os
import geocoder

def visualize_potholes_on_map():
    # Read the CSV file containing pothole data
    try:
        df = pd.read_csv("pothole_data.csv")
        print(f"Loaded {len(df)} pothole records from CSV file")
    except FileNotFoundError:
        print("Error: pothole_data.csv file not found")
        return
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return
    
    # Check if the dataframe has the required columns
    required_columns = ["Latitude", "Longitude", "Severity"]
    if not all(col in df.columns for col in required_columns):
        print(f"Error: CSV file must contain columns: {required_columns}")
        return
    
    # Get user's current location
    try:
        g = geocoder.ip('me')
        if g.latlng:
            user_lat, user_lng = g.latlng
            print(f"Detected user location: {user_lat}, {user_lng}")
        else:
            print("Could not detect user location, using pothole data center")
            user_lat, user_lng = None, None
    except Exception as e:
        print(f"Error getting user location: {e}")
        user_lat, user_lng = None, None
    
    # Create a map centered at user's location or pothole data center
    if user_lat and user_lng:
        pothole_map = folium.Map(location=[user_lat, user_lng], zoom_start=13)
    else:
        center_lat = df["Latitude"].mean()
        center_lng = df["Longitude"].mean()
        pothole_map = folium.Map(location=[center_lat, center_lng], zoom_start=13)
    
    # Add locate control to allow users to find their location on the map
    LocateControl(auto_start=True, position='topright').add_to(pothole_map)
    
    # Add a marker cluster to the map for potholes
    marker_cluster = MarkerCluster().add_to(pothole_map)
    
    # Define colors for different severity levels
    severity_colors = {
        "Low": "green",
        "Medium": "orange",
        "High": "red"
    }
    
    # Add markers for each pothole
    for idx, row in df.iterrows():
        # Get the color based on severity
        color = severity_colors.get(row["Severity"], "blue")
        
        # Create popup text with pothole information
        popup_text = f"""
        <b>Pothole #{idx+1}</b><br>
        Latitude: {row["Latitude"]}<br>
        Longitude: {row["Longitude"]}<br>
        Severity: {row["Severity"]}
        """
        if "Pothole Area (pixels)" in df.columns:
            popup_text += f"<br>Area: {row['Pothole Area (pixels)']} pixels"
        if "Timestamp" in df.columns:
            popup_text += f"<br>Detected on: {row['Timestamp']}"
        
        # Add marker to the cluster
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=color, icon="warning-sign", prefix="glyphicon")
        ).add_to(marker_cluster)
    
    # Add a marker for the user's current location if available
    if user_lat and user_lng:
        folium.Marker(
            location=[user_lat, user_lng],
            popup="Your Current Location",
            icon=folium.Icon(color="blue", icon="user", prefix="fa")
        ).add_to(pothole_map)
        
        # Add a circle around user's location (100m radius)
        folium.Circle(
            location=[user_lat, user_lng],
            radius=100,  # 100 meters
            color="blue",
            fill=True,
            fill_opacity=0.2,
            popup="Your Location (100m radius)"
        ).add_to(pothole_map)
    
    # Save the map as an HTML file
    map_file = "pothole_map.html"
    pothole_map.save(map_file)
    
    # Open the map in the default web browser
    map_path = os.path.abspath(map_file)
    print(f"Map saved to: {map_path}")
    webbrowser.open("file://" + map_path)

if __name__ == "__main__":
    visualize_potholes_on_map()
