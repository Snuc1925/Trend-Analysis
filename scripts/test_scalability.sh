#!/bin/bash
set -e

echo "=== Running Scalability Test ==="

# Parameters
INITIAL_RATE=10
MAX_RATE=1000
STEP=100
DURATION=60  # seconds per test

KAFKA_SERVER=${1:-"localhost:30092"}

echo "Testing scalability from ${INITIAL_RATE} to ${MAX_RATE} msg/sec"
echo "Kafka server: ${KAFKA_SERVER}"
echo ""

for RATE in $(seq ${INITIAL_RATE} ${STEP} ${MAX_RATE}); do
    echo "Testing at ${RATE} msg/sec for ${DURATION} seconds..."
    
    # Run producer
    python3 backend/data-generator/realtime_producer.py ${KAFKA_SERVER} ${RATE} &
    PRODUCER_PID=$!
    
    # Wait for duration
    sleep ${DURATION}
    
    # Stop producer
    kill ${PRODUCER_PID} || true
    
    # Collect metrics
    echo "Rate: ${RATE} msg/sec - Collecting metrics..."
    
    # Check Kafka lag
    kubectl exec -n reddit-pipeline kafka-0 -- kafka-consumer-groups \
        --bootstrap-server localhost:9092 \
        --describe --group hdfs-consumer-group || true
    
    echo "---"
    sleep 5
done

echo ""
echo "Scalability test complete!"
