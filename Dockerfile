FROM python:3.10

RUN apt-get update --fix-missing && \
    apt-get -y install ffmpeg && \
    apt-get clean

WORKDIR /opt/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade setuptools \
    && pip install --no-cache-dir -r requirements.txt

COPY ./src/ .

ENTRYPOINT ["python", "main.py"]
