# ==============================================
# 🌍 Day 1 Dashboard — Points + GeoJSON Boundaries
# ==============================================

import pandas as pd
import folium
from folium.plugins import MarkerCluster, MiniMap, Fullscreen, Search
from dash import Dash, html, dcc, Output, Input
import plotly.express as px
import requests
import io
import json # Import the json library

# -----------------------------
# 1️⃣ Dataset
# -----------------------------
data = {
    "District": ["Jammu", "Kathua", "Udhampur", "Rajouri", "Poonch",
                 "Srinagar", "Baramulla", "Pulwama", "Anantnag", "Kupwara"],
    "Division": ["Jammu", "Jammu", "Jammu", "Jammu", "Jammu",
                 "Kashmir", "Kashmir", "Kashmir", "Kashmir", "Kashmir"],
    "Lat": [32.73, 32.37, 32.92, 33.38, 33.77, 34.08, 34.20, 33.87, 33.73, 34.53],
    "Lon": [74.87, 75.52, 75.13, 74.31, 74.10, 74.80, 74.34, 74.90, 75.15, 74.25]
}
df = pd.DataFrame(data)

# -----------------------------
# 2️⃣ Load GeoJSON Boundaries
# -----------------------------
geojson_url = "https://raw.githubusercontent.com/datameet/india-geojson/master/district/india_district.geojson"

districts_geo = None # Initialize districts_geo

try:
    response = requests.get(geojson_url)
    response.raise_for_status() # Raise an exception for bad status codes
    geojson_text = response.text
    print("First 200 characters of fetched content:", geojson_text[:200]) # Print beginning of content
    districts_geo = json.loads(geojson_text)
except requests.exceptions.RequestException as e:
    print(f"Error fetching GeoJSON: {e}")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    print("Could not parse the fetched content as JSON. Please check the file format.")


# Filter only J&K districts if geojson was loaded successfully
if districts_geo:
    districts_geo["features"] = [
        f for f in districts_geo["features"]
        if f["properties"].get("st_nm", "").lower() in ["jammu and kashmir", "jammu & kashmir"]
    ]
else:
    print("GeoJSON data not loaded, skipping filtering.")


# -----------------------------
# 3️⃣ Create Folium Map Function
# -----------------------------
def create_map(selected_division="All"):
    m = folium.Map(location=[33.6, 75.0], zoom_start=7, tiles="CartoDB Voyager", control_scale=True)
    MiniMap(toggle_display=True).add_to(m)
    Fullscreen().add_to(m)
    marker_cluster = MarkerCluster().add_to(m)
    colors = {"Jammu": "red", "Kashmir": "blue"}

    # Add GeoJSON Layer if districts_geo is not None
    if districts_geo:
        folium.GeoJson(
            data=districts_geo,
            style_function=lambda feature: {
                'fillColor': (
                    'red' if feature["properties"].get("dt_name", "").lower() in
                    [d.lower() for d in df[df["Division"] == "Jammu"]["District"]]
                    else 'blue'
                ),
                'color': 'black',
                'weight': 0.8,
                'fillOpacity': 0.25,
            },
            tooltip=folium.GeoJsonTooltip(fields=["dt_name"], aliases=["District:"])
        ).add_to(m)
    else:
        print("GeoJSON data not available for map layer.")

    # Filter data if needed
    if selected_division != "All":
        filtered_df = df[df["Division"] == selected_division]
    else:
        filtered_df = df

    # Add markers
    for _, row in filtered_df.iterrows():
        popup_html = f"""
        <h4>{row['District']}</h4>
        <b>Division:</b> {row['Division']}<br>
        <b>Lat:</b> {row['Lat']}<br>
        <b>Lon:</b> {row['Lon']}
        """
        folium.CircleMarker(
            location=[row["Lat"], row["Lon"]],
            radius=8,
            popup=popup_html,
            tooltip=row["District"],
            color=colors[row["Division"]],
            fill=True,
            fill_opacity=0.8
        ).add_to(marker_cluster)

    Search(layer=marker_cluster, search_label="District").add_to(m)
    html_data = io.BytesIO()
    m.save(html_data, close_file=False)
    return html_data.getvalue().decode()

# -----------------------------
# 4️⃣ Dash App Layout
# -----------------------------
app = Dash(__name__)
app.title = "J&K District HQs — Points + Boundaries"

app.layout = html.Div([
    html.H1("🗺️ Day 1: Points + Boundaries — District HQs of J&K", style={'textAlign': 'center'}),
    html.P("Interactive Geo Map with District Boundaries and HQ Points", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Filter by Division:"),
        dcc.Dropdown(
            id="division_filter",
            options=[{"label": div, "value": div} for div in sorted(df["Division"].unique())] + [{"label": "All", "value": "All"}],
            value="All",
            clearable=False,
            style={'width': '300px'}
        )
    ], style={'textAlign': 'center', 'marginBottom': '15px'}),

    html.Iframe(id="map", srcDoc=create_map(), width="100%", height="500"),

    html.Div([
        dcc.Graph(id="pie_chart"),
        dcc.Graph(id="scatter_chart")
    ])
])

# -----------------------------
# 5️⃣ Callbacks for charts + map updates
# -----------------------------
@app.callback(
    [Output("pie_chart", "figure"), Output("scatter_chart", "figure"), Output("map", "srcDoc")],
    [Input("division_filter", "value")]
)
def update_dashboard(selected_division):
    if selected_division == "All":
        filtered_df = df
    else:
        filtered_df = df[df["Division"] == selected_division]

    pie_fig = px.pie(
        filtered_df, names="Division", title="Division-wise Distribution",
        color="Division", color_discrete_map={"Jammu": "red", "Kashmir": "blue"}
    )

    scatter_fig = px.scatter(
        filtered_df, x="Lon", y="Lat", text="District", color="Division",
        title="Spatial Spread of District HQs",
        color_discrete_map={"Jammu": "red", "Kashmir": "blue"}
    )
    scatter_fig.update_traces(textposition="top center")

    # Pass districts_geo to create_map
    updated_map = create_map(selected_division)
    return pie_fig, scatter_fig, updated_map

# -----------------------------
# 6️⃣ Run the App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
