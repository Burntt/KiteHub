import gpxpy
import folium
import numpy as np
from math import radians, cos, sin, asin, sqrt

gpx_file_name = 'GPX_data/Vilanova-Torredembarra.gpx'

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    return c * r


# Load and parse the GPX file
with open(gpx_file_name, 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

# Extract track information
coordinates = []
times = []
speeds = []
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            coordinates.append((point.latitude, point.longitude))
            times.append(point.time)
            speed_value = None
            if point.extensions:
                for extension in point.extensions:
                    if extension.tag.endswith('speed'):
                        try:
                            speed_value = float(extension.text)
                            break
                        except ValueError:
                            print(f"Error converting speed to float: {extension.text}")
                            speed_value = None
            speeds.append(speed_value if speed_value is not None else 0)

# Extract date
if times:
    # Extracting the date from the first timestamp
    start_date = times[0].strftime('%Y-%m-%d')
else:
    start_date = "Unknown Date"

# Compute midpoint
total_distance = 0
cumulative_distances = [0]

# Calculate total distance and cumulative distances
for i in range(1, len(coordinates)):
    distance = haversine(coordinates[i-1][1], coordinates[i-1][0],
                         coordinates[i][1], coordinates[i][0])
    total_distance += distance
    cumulative_distances.append(total_distance)

half_distance = total_distance / 2

# Find the point nearest to half the total distance
midpoint_index = 0
for i, cumulative_distance in enumerate(cumulative_distances):
    if cumulative_distance >= half_distance:
        midpoint_index = i
        break

midpoint_location = coordinates[midpoint_index]



# Create a folium map centered on the first coordinate
m = folium.Map(location=coordinates[0], zoom_start=12)

# Add track to the map
folium.PolyLine(coordinates, color='blue', weight=2.5, opacity=1).add_to(m)

# Calculate statistics
avg_speed = np.mean(speeds) * 3.6  # Convert to km/h
max_speed = np.max(speeds) * 3.6   # Convert to km/h
total_distance = sum([segment.length_3d() for track in gpx.tracks for segment in track.segments]) / 1000  # km
duration = (times[-1] - times[0]).total_seconds() / 3600  # hours

# Statistics summary using HTML
statistics_html = f"""
<div style="font-size: 12pt; font-family: Arial, Helvetica, sans-serif;">
<h4>Track Statistics</h4>
<ul>
    <li>Average Speed: {avg_speed:.2f} km/h</li>
    <li>Max Speed: {max_speed:.2f} km/h</li>
    <li>Total Distance: {total_distance:.2f} km</li>
    <li>Duration: {duration:.2f} hours</li>
    <li>Jump height: {10.1} meter</li>
</ul>
</div>
"""

# Add markers with HTML popup for the start marker
folium.Marker(
    location=coordinates[0],
    popup='Start'),
    icon=folium.Icon(color='green', icon='info-sign')
).add_to(m)

# Add end marker
folium.Marker(
    location=coordinates[-1],
    popup='End',
    icon=folium.Icon(color='red')
).add_to(m)

# Extracting the base name of the file (without the path)
base_name = gpx_file_name.split('/')[-1]
start_location_name, end_location_name = base_name.replace('.gpx', '').split('-')
print(f"Start Location: {start_location_name}, End Location: {end_location_name}")

title_html = f'''
<div style="background-color: #f9f9f9; border-radius: 6px; padding: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.5); width: 300px; transform: translateY(40px);">
    <h4 style="color: #0078A8; margin:0;">Route Information</h4>
    <hr style="margin: 5px 0;">
    <p style="margin: 5px 0; font-size: 14px; color: #555;">
        <strong>From:</strong> {start_location_name}<br>
        <strong>To:</strong> {end_location_name}<br>
        <strong>Date:</strong> {start_date}<br>
        <strong>Distance:</strong> {total_distance:.2f} km<br>
        <strong>Duration:</strong> {duration:.2f} hours<br>
        <strong>Avg Speed:</strong> {avg_speed:.2f} km/h<br>
        <strong>Max Speed:</strong> {max_speed:.2f} km/h<br>
        <strong>Jump Height:</strong> 10.1 meters
    </p>
</div>
'''

# Adding the title marker at the midpoint with the updated HTML for styling
folium.Marker(midpoint_location, 
              icon=folium.DivIcon(html=title_html)
             ).add_to(m)

# Save and show the map
map_filename = 'surfr_route_map.html'
m.save(map_filename)
print(f"Map saved to {map_filename}")