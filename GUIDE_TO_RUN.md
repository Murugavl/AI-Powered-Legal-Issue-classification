`# 🚀 Satta Vizhi - Application Run Guide

This guide explains how to start all components of the Satta Vizhi Legal Assistant application locally.

## 📋 Prerequisites
- **Node.js** (v16+)
- **Java JDK** (v17+) AND **Maven**
- **Python** (v3.8+)
- **PostgreSQL** (Optional, we are currently using H2 file-based DB for development)

## 🛠️ Step-by-Step Startup

You need to run **3 separate terminals**, one for each service.

### 1. 🧠 Start the AI Engine (Python)
This service handles Natural Language Processing (legal text analysis).

```bash
cd nlp-python
# Create venv if not exists (optional but recommended)
# python -m venv venv
# .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```
*Port: 8000*

---

### 2. 🔙 Start the Backend (Java Spring Boot)
This service handles the database, authentication, and core logic.

```bash
cd backend-java
# Clean and Run
mvn spring-boot:run
```
*Port: 8080*

---

### 3. 🖥️ Start the Frontend (React)
This is the user interface you interact with in the browser.

```bash
cd frontend
# Install dependencies (only needed once)
npm install

# Run the dev server
npm run dev
```
*Port: 5173* (usually)

---

## 🌐 Accessing the App

Once all three are running, open your browser and go to:
👉 **[http://localhost:5173](http://localhost:5173)**

## ⚠️ Troubleshooting

- **Login Failed?** 
  - Ensure the **Backend** is running without errors.
  - If you deleted the `data/` folder or reset the DB, you must **Register** again.
- **Voice Not Working?**
  - Ensure **Python NLP** service is running.
  - Check browser permissions for microphone.
