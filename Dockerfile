FROM python:3.12
RUN apt update
#RUN apt isntall
WORKDIR /app

COPY requirements.txt .

#RUN python3 -m venv venv 
#RUN source venv/bin/activate

RUN pip install -r requirements.txt
COPY . . 
CMD ["python3","bot.py"]
