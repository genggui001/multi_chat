FROM python:3.9

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

ADD . /app
EXPOSE 59815
# CMD ["gunicorn", "-c", "gconfig.py", "predict_oc:app"]
CMD ["python", "main.py"]
