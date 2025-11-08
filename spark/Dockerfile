FROM apache/spark:3.4.1-python3

USER root

# Copy application code
COPY spark/batch/ /app/batch/
COPY spark/streaming/ /app/streaming/

WORKDIR /app

USER spark

# Default command
CMD ["spark-submit", "--master", "local[4]", "batch/batch_processor.py"]
