#Dockerfile
FROM python:3.10.4

WORKDIR /app

# COPY main_app_v3.py .
# COPY models_v3.py .
# COPY prompts_v3.py .
# COPY sf_connect_v3.py .
# COPY examples_v3.py .
# COPY requirements.txt .
# COPY .env .

COPY . .

RUN pip install -r requirements.txt

CMD ["streamlit","run","app.py"]