FROM python:3.12

WORKDIR /app

ADD requirements.txt ./

RUN pip install -r requirements.txt

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]

ADD *.py ./
ADD *.png ./