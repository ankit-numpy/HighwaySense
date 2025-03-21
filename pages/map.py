import streamlit as st
import pandas as pd
import pydeck as pdk
import geocoder

# Load the CSV file
def load_data():
    file_path = "pothole_data.csv"
    df = pd.read_csv(file_path)
    return df

# Get current location
def get_current_location():
    g = geocoder.ip("me")
    if g.latlng:
        return pd.DataFrame([{"Latitude": g.latlng[0], "Longitude": g.latlng[1], "type": "current_location"}])
    return None

# Streamlit app
def main():
    st.title("Pothole Locations Map")
    
    df = load_data()
    df["type"] = "pothole"  # Mark all pothole locations
    
    # Assuming CSV has 'Latitude' and 'Longitude' columns
    if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        st.error("CSV file must contain 'Latitude' and 'Longitude' columns")
        return
    
    # Add menu option to select map type
    map_type = st.selectbox("Select Map Type", ["Default Map", "Satellite View"])
    map_styles = {
        "Default Map": "mapbox://styles/mapbox/streets-v11",
        "Satellite View": "mapbox://styles/mapbox/satellite-streets-v11"
    }
    
    # Get real-time current location
    location_df = get_current_location()
    if location_df is not None:
        st.write("Your Current Location:", location_df)
        df = pd.concat([df, location_df], ignore_index=True)
    
    # Define color based on type
    df["color"] = df["type"].map({"pothole": [255, 0, 0, 200], "current_location": [0, 255, 0, 200]})
    st.write(df)
    # Create the map
    st.write("Detailed Map View")
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position=["Longitude", "Latitude"],
        get_color="color",
        get_radius=100,
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
    )
    
    view_state = pdk.ViewState(
        Latitude=df['Latitude'].mean(), 
        Longitude=df['Longitude'].mean(),
        zoom=25,
        pitch=45,
        bearing=0,
    )
    
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style=map_styles[map_type],
        tooltip={"text": "Latitude: {Latitude}\nLongitude: {Longitude}"}
    )
    
    st.pydeck_chart(deck)

if __name__ == "__main__":
    main()
