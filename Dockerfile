FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir streamlit supabase streamlit-cookies-manager
CMD ["streamlit", "run", "app.py", "--server.port=${PORT}", "--server.address=0.0.0.0"]