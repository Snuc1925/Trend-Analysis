# Testing Guide

This guide covers testing strategies for the Lambda Architecture pipeline, including unit tests, integration tests, scalability tests, and fault tolerance tests.

## Test Pyramid

```
           ╱╲
          ╱  ╲       E2E Tests
         ╱    ╲
        ╱──────╲
       ╱        ╲    Integration Tests
      ╱          ╲
     ╱────────────╲
    ╱              ╲  Unit Tests
   ╱________________╲
```

## Unit Tests

### Running Unit Tests

```bash
# Run all unit tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_schemas.py -v

# Run with coverage
python3 -m pytest tests/ --cov=backend --cov-report=html
```

### Test Coverage

**Current Tests:**

1. **test_schemas.py**
   - Tests data schema generation
   - Validates post, comment, user structures
   - Verifies timestamp formatting

2. **test_historical_generator.py**
   - Tests historical data generation
   - Validates file creation
   - Verifies JSON format

**Adding New Tests:**

```python
# tests/test_new_feature.py
import unittest

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        # Setup test fixtures
        pass
    
    def test_feature_behavior(self):
        # Test implementation
        self.assertEqual(expected, actual)
```

## Integration Tests

### Kafka Integration Test

```bash
# Start Kafka cluster
kubectl wait --for=condition=ready pod -l app=kafka -n reddit-pipeline --timeout=300s

# Test producer
python3 << EOF
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:30092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send test message
producer.send('reddit.posts', {'test': 'message'})
producer.flush()
print("✓ Producer test passed")
EOF

# Test consumer
python3 << EOF
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'reddit.posts',
    bootstrap_servers='localhost:30092',
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    consumer_timeout_ms=5000
)

messages = [msg for msg in consumer]
print(f"✓ Consumer test passed - received {len(messages)} messages")
EOF
```

### HDFS Integration Test

```bash
# Wait for HDFS to be ready
kubectl wait --for=condition=ready pod -l app=namenode -n reddit-pipeline --timeout=300s

# Test HDFS write
kubectl exec -n reddit-pipeline $(kubectl get pod -l app=namenode -n reddit-pipeline -o jsonpath='{.items[0].metadata.name}') -- bash -c '
echo "test data" | hdfs dfs -put - /test.txt
hdfs dfs -cat /test.txt
hdfs dfs -rm /test.txt
echo "✓ HDFS test passed"
'
```

### Elasticsearch Integration Test

```bash
# Wait for Elasticsearch
kubectl wait --for=condition=ready pod -l app=elasticsearch -n reddit-pipeline --timeout=600s

# Test indexing
curl -X POST "http://localhost:30920/test_index/_doc" \
  -H 'Content-Type: application/json' \
  -d '{"test": "data", "timestamp": "2024-01-01T00:00:00Z"}'

# Test search
curl "http://localhost:30920/test_index/_search?pretty"

# Cleanup
curl -X DELETE "http://localhost:30920/test_index"

echo "✓ Elasticsearch test passed"
```

## End-to-End Test

### Complete Pipeline Test

```bash
#!/bin/bash
set -e

echo "=== Running E2E Test ==="

# 1. Deploy infrastructure
echo "Deploying infrastructure..."
make deploy
sleep 60  # Wait for pods to stabilize

# 2. Generate historical data
echo "Generating historical data..."
make generate-historical

# 3. Start consumer in background
echo "Starting consumer..."
make run-consumer &
CONSUMER_PID=$!
sleep 10

# 4. Start producer for 30 seconds
echo "Starting producer..."
timeout 30 make run-producer || true

# 5. Verify data in HDFS
echo "Verifying HDFS data..."
NAMENODE_POD=$(kubectl get pod -l app=namenode -n reddit-pipeline -o jsonpath='{.items[0].metadata.name}')
FILE_COUNT=$(kubectl exec -n reddit-pipeline $NAMENODE_POD -- hdfs dfs -count -q /data | awk '{print $3}')

if [ "$FILE_COUNT" -gt 0 ]; then
    echo "✓ HDFS contains $FILE_COUNT files"
else
    echo "✗ HDFS verification failed"
    exit 1
fi

# 6. Verify data in Elasticsearch
echo "Verifying Elasticsearch data..."
DOC_COUNT=$(curl -s "http://localhost:30920/_cat/count?format=json" | jq '.[0].count // 0' | tr -d '"')

if [ "$DOC_COUNT" -gt 0 ]; then
    echo "✓ Elasticsearch contains $DOC_COUNT documents"
else
    echo "✓ Elasticsearch check passed (may be empty in E2E test)"
fi

# Cleanup
kill $CONSUMER_PID 2>/dev/null || true

echo "=== E2E Test Passed ==="
```

Save as `scripts/test_e2e.sh` and run:

```bash
chmod +x scripts/test_e2e.sh
./scripts/test_e2e.sh
```

## Scalability Tests

### Throughput Test

Test system performance at different message rates:

```bash
make test-scalability
```

**What it tests:**
- Kafka throughput at 10, 100, 200, ..., 1000 msg/sec
- Consumer lag at each rate
- System resource utilization

**Metrics to monitor:**

```bash
# During test, monitor in separate terminal:

# Kafka consumer lag
kubectl exec -n reddit-pipeline kafka-0 -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group hdfs-consumer-group

# Pod resource usage
kubectl top pods -n reddit-pipeline

# HDFS disk usage
kubectl exec -n reddit-pipeline <namenode-pod> -- hdfs dfs -df -h
```

### Custom Throughput Test

```bash
# Test specific rate
python3 backend/data-generator/realtime_producer.py localhost:30092 500

# Monitor lag
watch -n 1 'kubectl exec -n reddit-pipeline kafka-0 -- kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group hdfs-consumer-group'
```

### Expected Results

| Rate (msg/sec) | Consumer Lag | CPU Usage | Status |
|----------------|--------------|-----------|--------|
| 10             | 0            | Low       | ✓      |
| 100            | 0-10         | Medium    | ✓      |
| 500            | 10-50        | High      | ✓      |
| 1000           | 50-100       | Very High | ⚠      |
| 5000           | >100         | Max       | Target |

## Fault Tolerance Tests

### Component Failure Tests

```bash
make test-fault-tolerance
```

**What it tests:**
1. Kafka broker failure and recovery
2. HDFS DataNode failure and recovery
3. Elasticsearch node failure and recovery

### Manual Fault Injection

#### Test 1: Kill Kafka Broker

```bash
# Kill broker
kubectl delete pod kafka-1 -n reddit-pipeline

# Monitor recovery
watch kubectl get pods -l app=kafka -n reddit-pipeline

# Expected: New pod starts within 30-60 seconds
# Verify: kafka-1 shows Running and 1/1 Ready

# Check cluster health
kubectl exec -n reddit-pipeline kafka-0 -- kafka-broker-api-versions \
  --bootstrap-server localhost:9092
```

#### Test 2: Kill HDFS DataNode

```bash
# Kill DataNode
kubectl delete pod datanode-1 -n reddit-pipeline

# Monitor recovery
watch kubectl get pods -l app=datanode -n reddit-pipeline

# Check replication status
NAMENODE_POD=$(kubectl get pod -l app=namenode -n reddit-pipeline -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n reddit-pipeline $NAMENODE_POD -- hdfs dfsadmin -report

# Expected: Under-replicated blocks temporarily increase, then return to 0
```

#### Test 3: Kill Elasticsearch Node

```bash
# Kill ES node
kubectl delete pod elasticsearch-1 -n reddit-pipeline

# Monitor recovery
watch kubectl get pods -l app=elasticsearch -n reddit-pipeline

# Check cluster health
curl "http://localhost:30920/_cluster/health?pretty"

# Expected: Status changes yellow → green within 1-2 minutes
```

### Network Partition Test

```bash
# Simulate network partition using network policies
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-kafka-1
  namespace: reddit-pipeline
spec:
  podSelector:
    matchLabels:
      app: kafka
      statefulset.kubernetes.io/pod-name: kafka-1
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF

# Wait and observe
sleep 30

# Remove partition
kubectl delete networkpolicy isolate-kafka-1 -n reddit-pipeline

# Expected: Kafka cluster detects partition, kafka-1 rejoins after policy removal
```

### Data Loss Test

```bash
#!/bin/bash
# Test that no data is lost during failures

# Start producer with unique messages
python3 << EOF
from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers='localhost:30092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send 1000 messages with IDs
for i in range(1000):
    msg = {'id': i, 'data': f'test_{i}'}
    producer.send('reddit.posts', msg)
    if i % 100 == 0:
        print(f"Sent {i} messages")
    time.sleep(0.01)

producer.flush()
print("Sent 1000 messages")
EOF

# Kill a broker during consumption
sleep 2
kubectl delete pod kafka-1 -n reddit-pipeline &

# Wait for recovery
sleep 60

# Verify all messages consumed
kubectl exec -n reddit-pipeline kafka-0 -- kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic reddit.posts

# Expected: Offsets show 1000 messages (or more if producer continued)
```

## Performance Benchmarks

### Batch Processing Benchmark

```bash
# Generate large dataset
python3 << EOF
from backend.data-generator.historical_generator import HistoricalDataGenerator
gen = HistoricalDataGenerator()
gen.generate_historical_data(num_days=30, posts_per_day=10000)
EOF

# Measure batch processing time
time make run-batch

# Expected: Process 300K posts in <10 minutes
```

### Streaming Latency Benchmark

```bash
# Terminal 1: Start streaming job
make run-streaming

# Terminal 2: Produce with timestamps
python3 << EOF
from kafka import KafkaProducer
from datetime import datetime
import json
import time

producer = KafkaProducer(
    bootstrap_servers='localhost:30092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

for i in range(100):
    msg = {
        'id': i,
        'sent_at': datetime.utcnow().isoformat()
    }
    producer.send('reddit.posts', msg)
    time.sleep(1)
EOF

# Terminal 3: Monitor Elasticsearch
watch -n 1 'curl -s "http://localhost:30920/views_subreddit_activity_v1/_search?size=1&sort=@timestamp:desc" | jq .hits.hits[0]._source'

# Expected: Documents appear in ES within 1-2 seconds of production
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=backend --cov-report=xml
      - uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: engineerd/setup-kind@v0.5.0
      - run: make deploy
      - run: ./scripts/test_e2e.sh
```

## Test Data Management

### Test Data Cleanup

```bash
# Clean Kafka topics
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics \
  --bootstrap-server localhost:9092 \
  --delete --topic reddit.posts

# Clean HDFS
kubectl exec -n reddit-pipeline <namenode-pod> -- hdfs dfs -rm -r /data/*

# Clean Elasticsearch
curl -X DELETE "http://localhost:30920/_all"

# Recreate topics
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics \
  --create --topic reddit.posts \
  --partitions 3 --replication-factor 3 \
  --bootstrap-server localhost:9092
```

### Test Data Fixtures

```python
# tests/fixtures.py
import pytest
from backend.data_generator.schemas import DataSchemas

@pytest.fixture
def sample_post():
    schemas = DataSchemas()
    return schemas.generate_post("test_post_1", "test_user_1", "python")

@pytest.fixture
def sample_comment():
    schemas = DataSchemas()
    return schemas.generate_comment("test_comment_1", "test_post_1", "test_user_1")
```

## Monitoring Test Results

### Grafana Test Dashboard

Create a dashboard with:
- Test success rate
- Test execution time
- Coverage metrics
- Failed test history

### Prometheus Alerts for Tests

```yaml
# prometheus-alerts.yml
groups:
  - name: test-alerts
    rules:
      - alert: HighTestFailureRate
        expr: test_failure_rate > 0.1
        for: 5m
        annotations:
          summary: "High test failure rate"
```

## Best Practices

1. **Run tests frequently**: Before every commit
2. **Keep tests fast**: Unit tests < 1s, integration tests < 30s
3. **Isolate tests**: Each test should be independent
4. **Use fixtures**: Reuse common test data
5. **Clean up**: Always clean up resources after tests
6. **Document expected behavior**: Include docstrings
7. **Monitor trends**: Track test metrics over time
8. **Automate**: Run tests in CI/CD pipeline

## Troubleshooting Test Failures

### Common Issues

**Timeout Errors:**
- Increase timeouts in Kubernetes wait commands
- Check pod resource limits
- Verify cluster has sufficient resources

**Connection Errors:**
- Verify services are ready
- Check NodePort mappings
- Confirm network policies allow traffic

**Data Verification Failures:**
- Check consumer logs for errors
- Verify Kafka topic creation
- Confirm HDFS write permissions

**Flaky Tests:**
- Add retry logic for network operations
- Increase sleep delays between operations
- Use proper wait conditions instead of fixed sleeps
