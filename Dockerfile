FROM python:3.13-slim

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

RUN pip install --no-cache-dir \
    numpy \
    pandas \
    scipy

WORKDIR /home/forecasting-agent

CMD ["python"]