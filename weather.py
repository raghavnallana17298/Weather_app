import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import pyrebase
import datetime

# -------------------------------
# 🔥 Your Firebase Config
# -------------------------------
firebaseConfig = {
    "apiKey": "AIzaSyCt4CHQJOP8Tv4oc8J4nzIEnRdEbfQUs-o",
    "authDomain": "weather-app-61018.firebaseapp.com",
    "databaseURL": "https://weather-app-61018-default-rtdb.firebaseio.com",
    "projectId": "weather-app-61018",
    "storageBucket": "weather-app-61018.appspot.com",
    "messagingSenderId": "428005445103",
    "appId": "1:428005445103:web:459d08c6499c303ae7fa1a"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

# -------------------------------
# PDF + Weather helpers
# -------------------------------
def create_pdf(forecast_df, city):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Weather Forecast for {city.capitalize()}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(40, 10, "Max Temp (°C)", 1)
    pdf.cell(40, 10, "Min Temp (°C)", 1)
    pdf.cell(70, 10, "Condition", 1)
    pdf.ln()
    for _, row in forecast_df.iterrows():
        pdf.cell(40, 10, row["Date"], 1)
        pdf.cell(40, 10, str(row["Max Temp (°C)"]), 1)
        pdf.cell(40, 10, str(row["Min Temp (°C)"]), 1)
        pdf.cell(70, 10, row["Condition"], 1)
        pdf.ln()
    return bytes(pdf.output(dest='S'))

def get_weather(city):
    url = f"https://wttr.in/{city}?format=j1"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_weather_icon(description):
    desc = description.lower()
    if "sunny" in desc or "clear" in desc:
        return "☀️"
    elif "cloud" in desc:
        return "☁️"
    elif "rain" in desc:
        return "🌧️"
    elif "thunder" in desc:
        return "⛈️"
    elif "snow" in desc:
        return "❄️"
    else:
        return "🌡️"

# -------------------------------
# 🔐 Streamlit UI for Auth
# -------------------------------
st.title("🌤️ Weather App ")

menu = ["Login", "Sign Up"]
choice = st.sidebar.selectbox("Menu", menu)
email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type='password')

if choice == "Sign Up":
    if st.sidebar.button("Create Account"):
        # Validate email format
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, email):
            st.sidebar.warning("⚠ Please enter a valid email address.")
        elif len(password) < 6:
            st.sidebar.warning("⚠ Password must be at least 6 characters.")
        else:
            try:
                user = auth.create_user_with_email_and_password(email, password)
                st.sidebar.success("✅ Account created! Please login.")
                db.child("users").push({"email": email, "created_at": str(datetime.datetime.now())})
            except Exception as e:
                error_msg = str(e)
                if "EMAIL_EXISTS" in error_msg:
                    st.sidebar.warning("⚠ Email already exists. Try logging in instead.")
                elif "INVALID_EMAIL" in error_msg:
                    st.sidebar.warning("⚠ Invalid email format.")
                else:
                    st.sidebar.error(f"🔥 Firebase Error: {e}")


if choice == "Login":
    if st.sidebar.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state['user'] = user
            st.sidebar.success(f"Welcome {str(email)[:len(str(email))-10]}!")
        except Exception as e:
            st.sidebar.error(f"Login failed: {e}")

# -------------------------------
# 🎯 Weather UI after login
# -------------------------------
if 'user' in st.session_state:
    st.success(f"Hello {str(email)[:len(str(email))-10]}! You are logged in.")
    st.write("✅ You can now use the weather dashboard.")

    city = st.text_input("Enter City Name:", value="Lucknow")
    if st.button("Get Weather"):
        with st.spinner("Fetching weather data..."):
            data = get_weather(city)
        if data:
            current = data["current_condition"][0]
            temp_c = current["temp_C"]
            desc = current["weatherDesc"][0]["value"]
            icon = get_weather_icon(desc)
            humidity = current["humidity"]
            wind = current["windspeedKmph"]

            st.header(f"Current Weather in {city.capitalize()}")
            st.metric("🌡 Temperature (°C)", temp_c)
            st.write(f"{icon} **Condition:** {desc}")
            st.write(f"💧 **Humidity:** {humidity}%")
            st.write(f"🌬 **Wind Speed:** {wind} km/h")

            st.subheader("📅 3-Day Forecast")
            days, max_temps, min_temps, conditions = [], [], [], []
            for day in data["weather"]:
                days.append(day["date"])
                max_temps.append(int(day["maxtempC"]))
                min_temps.append(int(day["mintempC"]))
                conditions.append(day["hourly"][4]["weatherDesc"][0]["value"])
            forecast_df = pd.DataFrame({
                "Date": days,
                "Max Temp (°C)": max_temps,
                "Min Temp (°C)": min_temps,
                "Condition": conditions
            })
            st.table(forecast_df)

            csv = forecast_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Forecast as CSV", data=csv,
                               file_name=f"{city}_forecast.csv", mime='text/csv')

            pdf_data = create_pdf(forecast_df, city)
            st.download_button("📄 Download Forecast as PDF", data=pdf_data,
                               file_name=f"{city}_forecast.pdf", mime='application/pdf')

            fig = px.line(forecast_df, x="Date", y=["Max Temp (°C)", "Min Temp (°C)"],
                          markers=True, title=f"Temperature Trend for {city.capitalize()}")
            st.plotly_chart(fig)
        else:
            st.error("Could not fetch weather data. Please check city name or try again later.")

    if st.button("Logout"):
        del st.session_state['user']
        st.experimental_rerun()
else:
    st.warning("Please login to use the weather dashboard.")
