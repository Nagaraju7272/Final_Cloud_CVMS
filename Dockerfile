# Use an official Python runtime as the base image
 
FROM python:3.12-slim
 
# Set the working directory inside the container
 
WORKDIR /app
 
# Copy the requirements file to the working directory
 
COPY requirements.txt .
 
# Install dependencies
 
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy the contents of the build context (student_management/) directly into /app/
 
COPY . .
 
# Debug: List the contents of /app/ to verify structure
 
RUN ls -la /app/
 
# Collect static files
 
RUN python manage.py collectstatic --noinput
 
# Fix permissions for static files
 
RUN chmod -R 755 /app/staticfiles
 
# Install and configure whitenoise to serve static files
 
RUN pip install whitenoise
 
# Expose port 8000 for the application
 
EXPOSE 8000
 
# Run migrations and start Gunicorn
 
CMD ["sh", "-c", "python manage.py migrate && gunicorn --workers=4 --timeout=180 --bind=0.0.0.0:8000 cvms.wsgi:application"]
 
