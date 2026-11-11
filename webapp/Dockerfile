FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
	&& addgroup --system app \
	&& adduser --system --ingroup app app
COPY . .
RUN mkdir -p /uploads \
	&& chown -R app:app /app /uploads

USER app

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:create_app()"]
