# 🌾 AI-Integrated Smart Agriculture Advisor

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![Machine Learning](https://img.shields.io/badge/AI-Random%20Forest%20%26%20CNN-orange)
![Status](https://img.shields.io/badge/Status-Completed-success)

## 📖 Overview
The **AI-Integrated Smart Agriculture Advisor** is a comprehensive web-based platform designed to assist farmers in making data-driven decisions. By leveraging **Machine Learning (Random Forest, Gradient Boosting)** and **Deep Learning (CNN)**, the system offers precise recommendations to maximize crop yield, reduce waste, and improve profitability.

This project bridges the gap between technology and traditional farming by providing real-time insights on crops, diseases, fertilizers, and market trends.

---

## 🚀 Key Features

### 1. 🌱 Crop Recommendation
* **Algorithm:** Random Forest Classifier
* **Function:** Analyzes soil parameters (N, P, K, pH) and weather conditions (Temperature, Humidity, Rainfall) to suggest the most suitable crop for cultivation.

### 2. 🍂 Disease Detection
* **Algorithm:** Convolutional Neural Network (CNN)
* **Function:** Allows users to upload images of crop leaves. The AI detects diseases (e.g., Early Blight, Leaf Rust) and provides immediate chemical or organic remedies.
* **Preprocessing:** Image resizing (224x224) and RGB conversion using OpenCV.

### 3. 🧪 Fertilizer Optimization
* **Function:** Calculates nutrient deficits in the soil and recommends the precise dosage of fertilizers (Urea, DAP, MOP) required.

### 4. 📈 Yield Prediction
* **Algorithm:** Gradient Boosting Regressor
* **Function:** Estimates the expected harvest quantity (in tons) based on farm area and crop type, helping in logistics planning.

### 5. 💰 Market Price Forecasting
* **Algorithm:** ARIMA (Time Series Analysis)
* **Function:** Predicts future market trends and commodity prices to help farmers decide the best time to sell.

### 6. 💧 Smart Irrigation
* **Function:** Integrates with Weather APIs to advise on irrigation schedules (e.g., "Irrigate Immediately" or "Rain Expected - Do Not Water").

---

## 🛠️ Tech Stack

* **Frontend:** HTML5, CSS3, JavaScript
* **Backend:** Python (Flask)
* **Machine Learning:** Scikit-learn, TensorFlow, NumPy, Pandas
* **Image Processing:** OpenCV, PIL
* **Database:**  MySQL
* **APIs:** OpenWeatherMap, Data.gov.in (Market Prices)


## 💻 Installation & Setup

Follow these steps to run the project locally on your machine.

### Prerequisites
* Python 3.7 or higher installed.

### Steps
1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/thummutukuri-pavankumar/AI-Smart-Agri-Advisor.git](https://github.com/thummutukuri-pavankumar/AI-Smart-Agri-Advisor.git)
    cd AI-Smart-Agri-Advisor
    ```

2.  **Create a Virtual Environment (Optional but Recommended)**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    ```bash
    python app.py
    ```

5.  **Access the Web App**
    * Open your browser and go to: `http://127.0.0.1:5000/`

---

## 📂 Project Structure

```bash
├── static/              # CSS, Images, JS files
├── templates/           # HTML Templates
├── models/              # Trained ML models (.pkl, .h5)
├── app.py               # Main Flask Application
├── requirements.txt     # Python Dependencies
└── README.md            # Project Documentation
=======
# ai-smart-agriculture-advisor
AI-Integrated Smart Agriculture Advisor is an AI-powered web application that provides farmers with crop recommendations, disease detection, irrigation planning, and market price prediction using Machine Learning, Computer Vision, and NLP. It helps improve productivity, reduce costs, and enable data-driven farming decisions.
