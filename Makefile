.PHONY: help install deploy clean test-scalability test-fault-tolerance generate-historical run-producer run-consumer run-batch run-streaming status logs

help:
	@echo "Lambda Architecture Big Data Pipeline"
	@echo ""
	@echo "Available targets:"
	@echo "  install                - Install Python dependencies"
	@echo "  deploy                 - Deploy all components to Kubernetes"
	@echo "  clean                  - Remove all deployed components"
	@echo "  generate-historical    - Generate historical data"
	@echo "  run-producer          - Run real-time data producer"
	@echo "  run-consumer          - Run data consumer (bootstrap + streaming)"
	@echo "  run-batch             - Run batch processing job"
	@echo "  run-streaming         - Run streaming processing job"
	@echo "  test-scalability      - Run scalability tests"
	@echo "  test-fault-tolerance  - Run fault tolerance tests"
	@echo "  status                - Show deployment status"
	@echo "  logs                  - Show logs from all components"

install:
	pip install -r requirements.txt

deploy:
	./scripts/deploy.sh

clean:
	./scripts/cleanup.sh

generate-historical:
	python3 backend/data-generator/historical_generator.py

run-producer:
	python3 backend/data-generator/realtime_producer.py localhost:30092 100

run-consumer:
	python3 backend/data-generator/consumer.py localhost:30092 http://localhost:30870 /tmp/historical_data

run-batch:
	spark-submit --master local[4] \
		spark/batch/batch_processor.py \
		hdfs://localhost:30900/data \
		hdfs://localhost:30900/output/batch

run-streaming:
	spark-submit --master local[4] \
		--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,org.elasticsearch:elasticsearch-spark-30_2.12:8.9.0 \
		spark/streaming/speed_processor.py \
		localhost:30092 \
		localhost

test-scalability:
	./scripts/test_scalability.sh localhost:30092

test-fault-tolerance:
	./scripts/test_fault_tolerance.sh

status:
	@echo "=== Deployment Status ==="
	kubectl get pods -n reddit-pipeline
	@echo ""
	@echo "=== Services ==="
	kubectl get svc -n reddit-pipeline

logs:
	@echo "=== Recent logs from all components ==="
	kubectl logs -n reddit-pipeline -l app=kafka --tail=50 || true
	kubectl logs -n reddit-pipeline -l app=namenode --tail=50 || true
	kubectl logs -n reddit-pipeline -l app=elasticsearch --tail=50 || true
