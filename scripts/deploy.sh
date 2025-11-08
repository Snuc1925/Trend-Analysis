#!/bin/bash
set -e

echo "=== Deploying Lambda Architecture Pipeline ==="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

# Create namespace
echo "Creating namespace..."
kubectl create namespace reddit-pipeline || true

# Deploy Zookeeper
echo "Deploying Zookeeper..."
kubectl apply -f kafka/manifests/zookeeper.yaml -n reddit-pipeline

# Wait for Zookeeper to be ready
echo "Waiting for Zookeeper to be ready..."
kubectl wait --for=condition=ready pod -l app=zookeeper -n reddit-pipeline --timeout=300s || true

# Deploy Kafka
echo "Deploying Kafka..."
kubectl apply -f kafka/manifests/kafka.yaml -n reddit-pipeline

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
kubectl wait --for=condition=ready pod -l app=kafka -n reddit-pipeline --timeout=300s || true

# Create Kafka topics
echo "Creating Kafka topics..."
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics --create --topic reddit.posts --partitions 3 --replication-factor 3 --if-not-exists --bootstrap-server localhost:9092 || true
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics --create --topic reddit.comments --partitions 3 --replication-factor 3 --if-not-exists --bootstrap-server localhost:9092 || true
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics --create --topic reddit.users --partitions 3 --replication-factor 3 --if-not-exists --bootstrap-server localhost:9092 || true

# Deploy HDFS
echo "Deploying HDFS..."
kubectl apply -f hdfs/manifests/namenode.yaml -n reddit-pipeline
kubectl apply -f hdfs/manifests/datanode.yaml -n reddit-pipeline

# Wait for HDFS to be ready
echo "Waiting for HDFS to be ready..."
kubectl wait --for=condition=ready pod -l app=namenode -n reddit-pipeline --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=datanode -n reddit-pipeline --timeout=300s || true

# Deploy Elasticsearch
echo "Deploying Elasticsearch..."
kubectl apply -f elasticsearch/manifests/elasticsearch.yaml -n reddit-pipeline

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
kubectl wait --for=condition=ready pod -l app=elasticsearch -n reddit-pipeline --timeout=600s || true

# Deploy Prometheus
echo "Deploying Prometheus..."
kubectl apply -f prometheus/manifests/prometheus.yaml -n reddit-pipeline

# Deploy Grafana
echo "Deploying Grafana..."
kubectl apply -f grafana/manifests/grafana.yaml -n reddit-pipeline

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
kubectl wait --for=condition=ready pod -l app=grafana -n reddit-pipeline --timeout=300s || true

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Access points:"
echo "- Grafana: http://localhost:30300 (admin/admin)"
echo "- Prometheus: http://localhost:30909"
echo "- Elasticsearch: http://localhost:30920"
echo "- HDFS NameNode: http://localhost:30870"
echo "- Kafka: localhost:30092"
echo ""
echo "To check status:"
echo "  kubectl get pods -n reddit-pipeline"
echo ""
