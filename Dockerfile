FROM python:alpine

WORKDIR /home/ubuntu

# Copy requirements first as to not disturb cache for other changes.
COPY requirements.txt .

RUN pip3 install -r requirements.txt && \
  pip3 install gunicorn

USER ubuntu

# Finally, copy the entire source.
COPY app.py .
COPY static static
COPY templates templates
COPY routes routes
COPY utils utils

ENV FLASK_APP app.py
EXPOSE 8080
ENTRYPOINT ["gunicorn", "-b", ":8080", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
