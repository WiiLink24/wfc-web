FROM python:alpine

RUN adduser -D server
WORKDIR /home/server

# Copy requirements first as to not disturb cache for other changes.
COPY requirements.txt .

RUN pip3 install -r requirements.txt && \
  pip3 install gunicorn

# Finally, copy the entire source.
COPY app.py .
COPY static static
COPY templates templates
COPY routes routes
COPY utils utils

USER server
RUN chown -R server:server /home/server

ENV FLASK_APP app.py
EXPOSE 8080
ENTRYPOINT ["gunicorn", "-b", ":8080", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
