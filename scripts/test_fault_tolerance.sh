#!/bin/bash
set -e

echo "=== Running Fault Tolerance Test ==="

NAMESPACE="reddit-pipeline"

# Test 1: Kill a Kafka broker
echo "Test 1: Killing one Kafka broker..."
kubectl delete pod kafka-1 -n ${NAMESPACE} || true
echo "Waiting for Kafka to recover..."
sleep 30
kubectl get pods -l app=kafka -n ${NAMESPACE}
echo ""

# Test 2: Kill a DataNode
echo "Test 2: Killing one HDFS DataNode..."
kubectl delete pod datanode-1 -n ${NAMESPACE} || true
echo "Waiting for HDFS to recover..."
sleep 30
kubectl get pods -l app=datanode -n ${NAMESPACE}
echo ""

# Test 3: Kill an Elasticsearch node
echo "Test 3: Killing one Elasticsearch node..."
kubectl delete pod elasticsearch-1 -n ${NAMESPACE} || true
echo "Waiting for Elasticsearch to recover..."
sleep 30
kubectl get pods -l app=elasticsearch -n ${NAMESPACE}
echo ""

echo "Fault tolerance test complete!"
echo "All components should self-recover"
