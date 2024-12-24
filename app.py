import dash
from dash import dcc, html, Input, Output
import requests
import plotly.graph_objects as go
import folium
import io

API_URL = "https://dataservice.accuweather.com/"
LOCATION_URL = 'locations/v1/cities/search'
FORECAST_URL = "forecasts/v1/daily/5day/"
API_KEY = "J9ANH8IbJ72GDDiGsg1H5k4prE7oMxFq"
API_LIST = ["J9ANH8IbJ72GDDiGsg1H5k4prE7oMxFq",
            "Ot3MNhWUAGaOHm7ABAGvmsBndksPARaF",
            "Emw21PScIF1FAIQ0ov3U2dQTZKByKotH",
            "7k3zLVQdD92Fbr1MvdNzK8tajjcS7SHT",
            "xb3dV1OkbAhPdHAZWsGbuxuxmNlm1ZSB"]
for x in API_LIST:
    response = requests.get(
        f"{API_URL}{LOCATION_URL}",
        params={"q": "Москва", "apikey": x},
    )
    status = response.status_code
    if status == 200:
        API_KEY = x
        break


def from_fahrenheit_to_celsius(t):
    return round(5 / 9 * (t - 32), 1)


def get_weather_forecast(city_name):
    try:
        location_response = requests.get(
            f"{API_URL}{LOCATION_URL}",
            params={"q": city_name, "apikey": API_KEY},
        )
        status_code = location_response.status_code
        if status_code == 503:
            return None, "Проблема подключения к API"
        location_response = location_response.json()
        if not location_response:
            return None, f"Город '{city_name}' не найден."
        location_key = location_response[0]["Key"]
        forecast_response = requests.get(
            f"{API_URL}{FORECAST_URL}{location_key}",
            params={"apikey": API_KEY, "details": "true"},
        ).json()
        if not forecast_response:
            return None, f"Данные о погоде для города '{city_name}' не найдены."
        forecast_data = forecast_response["DailyForecasts"]
        return [
            {
                "date": day["Date"],
                "temperature": from_fahrenheit_to_celsius(day["Temperature"]["Maximum"]["Value"]),
                "wind": day["Day"]["Wind"]["Speed"]["Value"],
                "rain": day["Day"]["RainProbability"],
            }
            for day in forecast_data
        ], "Данные успешно загружены"
    except Exception:
        return None, "Ошибка на стороне сервера"


app = dash.Dash(__name__)

# Layout
app.layout = html.Div([
    # Header
    html.Div(
        html.H1(
            "Прогноз погоды по маршруту",
            style={
                "text-align": "center",
                "margin-top": "20px",
                "color": "#007bff",
                "font-family": "Arial, sans-serif",
                "font-size": "32px",
            }
        ),
        style={"padding": "10px", "box-shadow": "0 2px 5px rgba(0,0,0,0.2)", "background-color": "#f8f9fa"}
    ),

    # Form
    html.Div([
        html.Label("Введите города маршрута через запятую:", style={
            "font-weight": "bold",
            "font-family": "Arial, sans-serif",
            "margin-bottom": "10px",
            "display": "block",
        }),
        dcc.Input(
            id="city-input",
            type="text",
            placeholder="Москва, Санкт-Петербург, Казань",
            style={
                "width": "95%",
                "padding": "12px",
                "border": "1px solid #ced4da",
                "border-radius": "4px",
                "margin-bottom": "15px",
                "font-size": "16px",
                "box-shadow": "0 2px 4px rgba(0,0,0,0.1)",
            }
        ),
        html.Label("Выберите временной интервал:", style={
            "font-weight": "bold",
            "margin-bottom": "10px",
            "font-family": "Arial, sans-serif",
            "display": "block",
        }),
        dcc.RadioItems(
            id="forecast-duration",
            options=[
                {"label": "1 День", "value": 1},
                {"label": "3 Дня", "value": 3},
                {"label": "5 Дней", "value": 5},
            ],
            value=3,
            style={
                "gap": "20px",
                "display": "flex",
                "align-items": "center",
                "margin-bottom": "15px",
                "font-family": "Arial, sans-serif",
            },
        ),
        html.Button(
            "Построить маршрут",
            id="build-route",
            n_clicks=0,
            style={
                "background-color": "#007bff",
                "color": "white",
                "padding": "12px 24px",
                "border": "none",
                "border-radius": "4px",
                "cursor": "pointer",
                "font-size": "16px",
                "font-family": "Arial, sans-serif",
                "box-shadow": "0 2px 4px rgba(0,0,0,0.2)",
            }
        ),
    ], style={"width": "60%", "margin": "20px auto", "padding": "20px", "border-radius": "8px",
              "box-shadow": "0 4px 8px rgba(0,0,0,0.1)", "background-color": "#ffffff"}),

    # Отображение карты
    html.Div(id="route-map", style={
        "margin": "30px auto",
        "box-shadow": "0 4px 8px rgba(0,0,0,0.1)",
        "border-radius": "8px",
        "overflow": "hidden"
    }),

    # Отображение графиков
    html.Div(id="forecast-graphs", style={"width": "80%", "margin": "0 auto"})
], style={"background-color": "#f2f2f2", "padding": "20px"})


@app.callback(
    [Output("route-map", "children"),
     Output("forecast-graphs", "children")],
    [Input("build-route", "n_clicks")],
    [dash.dependencies.State("city-input", "value"), dash.dependencies.State("forecast-duration", "value")]
)
def update_route_and_forecast(n_clicks, city_input, duration):
    if n_clicks == 0:
        return None, None
    if not city_input:
        return None, html.Div("Введите хотя бы один город", style={
            "color": "white",
            "background-color": "red",
            "padding": "10px",
            "margin": "10px 0",
            "border-radius": "5px",
            "text-align": "center",
            "font-weight": "bold"
        })

    cities = [city.strip() for city in city_input.split(",")]
    weather_data = []
    locations = []
    graphs = []
    correct_cities = False

    for city in cities:
        forecast_data, info = get_weather_forecast(city)
        if not forecast_data:
            graphs.append(html.Div(f"{info}", style={
                "color": "white",
                "background-color": "red",
                "padding": "10px",
                "margin": "10px 0",
                "border-radius": "5px",
                "text-align": "center",
                "font-weight": "bold"
            }))
            if info == "Проблема подключения к API":
                return None, graphs
            continue
        correct_cities = True
        location_response = requests.get(
            f"{API_URL}{LOCATION_URL}",
            params={"q": city, "apikey": API_KEY},
        )
        location_response.raise_for_status()
        location_data = location_response.json()[0]
        lat, lon = location_data["GeoPosition"]["Latitude"], location_data["GeoPosition"]["Longitude"]
        weather_data.append((city, forecast_data))
        locations.append((lat, lon))
    if not correct_cities:
        return None, html.Div("Введите корректные названия городов", style={
            "color": "white",
            "background-color": "red",
            "padding": "10px",
            "margin": "10px 0",
            "border-radius": "5px",
            "text-align": "center",
            "font-weight": "bold"
        })
    m = folium.Map(location=locations[0], zoom_start=6)
    for (lat, lon), (city, forecast) in zip(locations, weather_data):
        folium.Marker(
            [lat, lon],
            popup=f"Город: {city}<br>Температура: {forecast[0]['temperature']}°C",
            tooltip=city
        ).add_to(m)

    folium.PolyLine(locations, color="blue", weight=2.5, opacity=1).add_to(m)
    map_html = io.BytesIO()
    m.save(map_html, close_file=False)
    map_html.seek(0)
    map_src = map_html.getvalue().decode()
    for city, forecast in weather_data:
        forecast = forecast[:duration]
        dates = [day["date"][:10] for day in forecast]
        temperatures = [day["temperature"] for day in forecast]
        wind_speeds = [day["wind"] for day in forecast]
        rain_probs = [day["rain"] for day in forecast]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=temperatures, mode="lines+markers", name="Температура (°C)"))
        fig.add_trace(go.Scatter(x=dates, y=wind_speeds, mode="lines+markers", name="Скорость ветра (km/h)"))
        fig.add_trace(go.Scatter(x=dates, y=rain_probs, mode="lines+markers", name="Вероятность дождя (%)"))
        fig.update_layout(title=f"Прогноз погоды для города {city}", xaxis_title="Дата", yaxis_title="Значение",
                          paper_bgcolor="#ffffff", plot_bgcolor="#f8f9fa")

        graphs.append(html.Div([
            html.H2(f"{city}", style={"text-align": "center"}),
            dcc.Graph(figure=fig)
        ], style={"padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 8px rgba(0,0,0,0.1)",
                  "margin-bottom": "20px", "background-color": "#ffffff"}))

    return html.Iframe(srcDoc=map_src,
                       style={"width": "100%", "height": "500px", "border": "none"}), graphs


if __name__ == "__main__":
    app.run_server(debug=True)
