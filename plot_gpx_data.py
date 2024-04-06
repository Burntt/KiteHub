import gpxpy
import folium
import numpy as np
import folium.plugins as plugins
import math
from math import radians, cos, sin, asin, sqrt

gpx_file_name = 'GPX_data/Vilanova-Torredembarra.gpx'
speed_threshold = 25 / 3.6  # Converting 30 km/h to m/s for comparison

def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between two points on the earth."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    return c * r

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate the compass bearing from one point to another."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing


# Function to calculate a new point given a start point, bearing, and distance
def calculate_new_point(lat, lon, bearing, distance):
    R = 6378.1  # Radius of the Earth in kilometers
    bearing = math.radians(bearing)  # Convert bearing to radians

    lat1 = math.radians(lat)  # Current lat point converted to radians
    lon1 = math.radians(lon)  # Current long point converted to radians

    lat2 = math.asin(math.sin(lat1) * math.cos(distance / R) +
                     math.cos(lat1) * math.sin(distance / R) * math.cos(bearing))

    lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(distance / R) * math.cos(lat1),
                             math.cos(distance / R) - math.sin(lat1) * math.sin(lat2))

    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)

    return [lat2, lon2]

with open(gpx_file_name, 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

coordinates = []
times = []
speeds = []
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            coordinates.append((point.latitude, point.longitude))
            times.append(point.time)
            if point.extensions:
                speed = None
                for extension in point.extensions:
                    if extension.tag.endswith('speed'):
                        try:
                            speed = float(extension.text)
                            break
                        except ValueError:
                            continue
                speeds.append(speed if speed is not None else 0)

# Extract start and end locations from the file name
_, file_name = gpx_file_name.rsplit('/', 1)
start_location_name, end_location_name = file_name.replace('.gpx', '').split('-')

# Extract date from the first timestamp
start_date = times[0].strftime('%Y-%m-%d') if times else "Unknown Date"

# Prepare map
m = folium.Map(location=coordinates[0], zoom_start=12)

# Correctly segment the route based on speed
for i in range(1, len(coordinates)):
    # Check if there's a speed value for the segment and assign color
    segment_color = 'red' if speeds[i-1] < speed_threshold else 'blue'
    folium.PolyLine(coordinates[i-1:i+1], color=segment_color, weight=2.5).add_to(m)

# Calculate statistics after ensuring there are speeds recorded
if speeds:
    total_distance = sum(haversine(coordinates[i-1][1], coordinates[i-1][0], coordinates[i][1], coordinates[i][0]) for i in range(1, len(coordinates)))
    avg_speed = np.mean(speeds) * 3.6  # Convert to km/h
    max_speed = np.max(speeds) * 3.6   # Convert to km/h
    duration = (times[-1] - times[0]).total_seconds() / 3600
else:
    total_distance, avg_speed, max_speed, duration = 0, 0, 0, 0

# Add title and statistics marker at the midpoint
title_html = f'''
<div style="background-color: #f9f9f9; border-radius: 6px; padding: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.5); width: 300px; transform: translateY(40px);">
    <h4 style="color: #0078A8; margin:0;">Route from {start_location_name} to {end_location_name} on {start_date}</h4>
    <p style="margin: 5px 0; font-size: 14px; color: #555;">
        <strong>Distance:</strong> {total_distance:.2f} km<br>
        <strong>Duration:</strong> {duration:.2f} hours<br>
        <strong>Avg Speed:</strong> {avg_speed:.2f} km/h<br>
        <strong>Max Speed:</strong> {max_speed:.2f} km/h<br>
        <strong>Jump Height:</strong> {10.1} meter<br>
    </p>
</div>
'''
midpoint_location = coordinates[len(coordinates) // 2]
folium.Marker(midpoint_location, icon=folium.DivIcon(html=title_html)).add_to(m)

# Estimate wind direction
start_point = coordinates[0]
end_point = coordinates[-1]
bearing = calculate_bearing(start_point[0], start_point[1], end_point[0], end_point[1])

# Calculate the offset position for the wind direction icon
offset_lat, offset_lon = calculate_new_point(midpoint_location[0], midpoint_location[1], bearing + 90, -7)  # 2 km to the side

# Select the closest pre-rotated wind icon based on the calculated bearing
icon_url = 'https://cdn-icons-png.flaticon.com/512/2045/2045893.png'
icon_width, icon_height = 100, 100  # You can change these values as needed
icon_anchor_center = (icon_width // 2, icon_height // 2)
icon = folium.CustomIcon(icon_url, icon_size=(icon_width, icon_height), icon_anchor=icon_anchor_center)
folium.Marker([offset_lat, offset_lon], icon=icon, tooltip=f'Wind Direction: {bearing:.0f}°').add_to(m)

# Calculate the end point of the subtle dashed line extending from the wind icon
point_line_end = calculate_new_point(offset_lat, offset_lon, bearing, 10)  # This should return a [lat, lon] pair

# Draw the subtle dashed line for wind direction
line_points = [[offset_lat, offset_lon], point_line_end]  # A list of coordinate pairs
line = folium.PolyLine(line_points, color='gray', weight=5, opacity=0.75, dash_array='5').add_to(m)

# Add an arrow to the line to indicate direction
plugins.PolyLineTextPath(
    line,
    ' ►',  # The arrow symbol (you can also use '>', but '►' gives a more defined arrow)
    repeat=True,
    offset=8,  # You might need to adjust this offset depending on the weight of the line
    attributes={'fill': 'gray', 'font-weight': 'bold', 'font-size': '24'}
).add_to(m)


print("Start Point:", start_point)  # Debug print
print("End Point:", end_point)  # Debug print

# Ensure these variables are tuples of (latitude, longitude)
start_marker = folium.Marker(
    location=start_point,  # Should be [latitude, longitude]
    popup='Start',
    icon=folium.Icon(color='green', icon='info-sign')
)
start_marker.add_to(m)

end_marker = folium.Marker(
    location=end_point,  # Should be [latitude, longitude]
    popup='End',
    icon=folium.Icon(color='red')
)
end_marker.add_to(m)

# Save and show the map
map_filename = 'surfr_route_map.html'
m.save(map_filename)
print(f"Map saved to {map_filename}")