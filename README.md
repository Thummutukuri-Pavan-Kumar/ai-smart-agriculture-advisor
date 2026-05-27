# 🌾 AI-Integrated Smart Agriculture Advisor

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![Machine Learning](https://img.shields.io/badge/AI-Random%20Forest%20%26%20CNN-orange)
![Status](https://img.shields.io/badge/Status-Completed-success)

---

## 📖 Overview

The **AI-Integrated Smart Agriculture Advisor** is a comprehensive web-based platform designed to assist farmers in making data-driven decisions. By leveraging **Machine Learning (Random Forest, Gradient Boosting)** and **Deep Learning (CNN)**, the system offers precise recommendations to maximize crop yield, reduce waste, and improve profitability.

This project bridges the gap between technology and traditional farming by providing real-time insights on crops, diseases, fertilizers, and market trends.

---

## 🚀 Key Features

### 🌱 Crop Recommendation
- **Algorithm:** Random Forest Classifier
- **Function:** Analyzes soil parameters (N, P, K, pH) and weather conditions (Temperature, Humidity, Rainfall) to suggest the most suitable crop.

### 🍂 Disease Detection
- **Algorithm:** Convolutional Neural Network (CNN)
- **Function:** Detects crop diseases from uploaded leaf images and suggests remedies.
- **Preprocessing:** Image resizing (224x224) and RGB conversion using OpenCV.

### 🧪 Fertilizer Optimization
- Calculates nutrient deficits and recommends fertilizer dosage.

### 📈 Yield Prediction
- **Algorithm:** Gradient Boosting Regressor
- Predicts expected harvest quantity based on farm area and crop type.

### 💰 Market Price Forecasting
- **Algorithm:** ARIMA (Time Series Analysis)
- Predicts future crop market prices.

### 💧 Smart Irrigation
- Integrates weather APIs for irrigation scheduling.

---

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3, JavaScript
- **Backend:** Python, Flask
- **Machine Learning:** Scikit-learn, TensorFlow, NumPy, Pandas
- **Image Processing:** OpenCV, PIL
- **Database:**  MySQL
- **APIs:** OpenWeatherMap, Data.gov.in

---

## 💻 Installation & Setup

### Clone Repository

```bash
git clone https://github.com/Thummutukuri-Pavan-Kumar/ai-smart-agriculture-advisor.git
cd ai-smart-agriculture-advisor
Create Virtual Environment
python -m venv venv
Windows
venv\Scripts\activate
Linux / Mac
source venv/bin/activate
Install Dependencies
pip install -r requirements.txt
Run Application
python app.py
Access Web App
http://127.0.0.1:5000/
📂 Project Structure
├── static/
├── templates/
├── models/
├── app.py
├── requirements.txt
└── README.md
🌟 Future Enhancements
Mobile Application
IoT Sensor Integration
Drone-Based Monitoring
Multilingual Voice Assistant
👨‍💻 Author

Pavan Kumar

GitHub: https://github.com/Thummutukuri-Pavan-Kumar
LinkedIn: https://www.linkedin.com/in/pavan-kumar-bb0b56291