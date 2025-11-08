# Setup Guide for Lambda Architecture Pipeline

This guide provides step-by-step instructions for deploying and running the Lambda Architecture Big Data pipeline.

## Prerequisites

### Required Software

1. **Kubernetes Cluster**
   - Recommended: kind, k3s, or minikube for local development
   - Minimum 3 nodes for distributed testing
   - 8GB RAM per node recommended

2. **kubectl**
   ```bash
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   ```

3. **Python 3.8+**
   ```bash
   python3 --version
   ```

4. **Apache Spark 3.4+**
   ```bash
   # Download and install Spark
   wget https://archive.apache.org/dist/spark/spark-3.4.1/spark-3.4.1-bin-hadoop3.tgz
   tar -xzf spark-3.4.1-bin-hadoop3.tgz
   sudo mv spark-3.4.1-bin-hadoop3 /opt/spark
   export SPARK_HOME=/opt/spark
   export PATH=$PATH:$SPARK_HOME/bin
   ```

5. **Make**
   ```bash
   sudo apt-get install make  # Ubuntu/Debian
   # or
   brew install make  # macOS
   ```

## Step 1: Create Kubernetes Cluster

### Using kind (Recommended)

```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Create multi-node cluster
cat <<EOF | kind create cluster --name reddit-pipeline --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
- role: worker
EOF
```

### Using minikube

```bash
minikube start --nodes 3 --cpus 4 --memory 8192 --driver=docker
```

### Using k3s

```bash
# Install k3s
curl -sfL https://get.k3s.io | sh -
```

## Step 2: Install Dependencies

```bash
cd /path/to/Trend-Analysis
make install
```

This installs all required Python packages:
- kafka-python
- pyspark
- elasticsearch
- pandas
- Faker
- pytest

## Step 3: Deploy Infrastructure

```bash
make deploy
```

This deploys all components:
1. Zookeeper (3 replicas)
2. Kafka (3 brokers)
3. HDFS (1 NameNode + 3 DataNodes)
4. Elasticsearch (3 nodes)
5. Grafana
6. Prometheus

**Wait for all pods to be ready** (this may take 5-10 minutes):

```bash
watch kubectl get pods -n reddit-pipeline
```

All pods should show `Running` status and `1/1` or `3/3` ready.

## Step 4: Verify Deployment

Check the status:

```bash
make status
```

You should see output similar to:

```
NAME                   READY   STATUS    RESTARTS   AGE
elasticsearch-0        1/1     Running   0          5m
elasticsearch-1        1/1     Running   0          5m
elasticsearch-2        1/1     Running   0          5m
grafana-xxx            1/1     Running   0          5m
kafka-0                1/1     Running   0          5m
kafka-1                1/1     Running   0          5m
kafka-2                1/1     Running   0          5m
namenode-xxx           1/1     Running   0          5m
datanode-0             1/1     Running   0          5m
datanode-1             1/1     Running   0          5m
datanode-2             1/1     Running   0          5m
prometheus-xxx         1/1     Running   0          5m
zookeeper-0            1/1     Running   0          5m
zookeeper-1            1/1     Running   0          5m
zookeeper-2            1/1     Running   0          5m
```

## Step 5: Generate Historical Data

```bash
make generate-historical
```

This creates 7 days of historical data:
- 7,000 posts
- ~35,000 comments
- 1,000 users

Data is saved to `/tmp/historical_data/`.

## Step 6: Start Data Pipeline

### Terminal 1: Start Consumer

The consumer bootstraps historical data to HDFS and then streams from Kafka:

```bash
make run-consumer
```

Expected output:
```
Connected to HDFS at http://localhost:30870
Bootstrapping historical data from /tmp/historical_data...
Processing /tmp/historical_data/posts.json...
Processing /tmp/historical_data/comments.json...
Processing /tmp/historical_data/users.json...
Bootstrap complete!
Connected to Kafka and subscribed to ['reddit.posts', 'reddit.comments', 'reddit.users']
Consuming messages from Kafka...
```

### Terminal 2: Start Producer

The producer sends real-time data to Kafka:

```bash
make run-producer
```

Expected output:
```
Connected to Kafka at localhost:30092
Starting producer: 100 msg/sec
Produced 1000 messages (100.23 msg/sec)
Produced 2000 messages (100.11 msg/sec)
...
```

## Step 7: Run Processing Jobs

### Terminal 3: Run Batch Processing

Process all historical data in HDFS:

```bash
make run-batch
```

This computes:
- Top posts per subreddit per day
- User activity metrics
- Subreddit activity trends

### Terminal 4: Run Streaming Processing

Process real-time data from Kafka:

```bash
make run-streaming
```

This writes real-time aggregations to Elasticsearch.

## Step 8: Access Dashboards

### Grafana

1. Open browser: http://localhost:30300
2. Login: admin / admin
3. Add Elasticsearch data source (already configured)
4. Import dashboard from `grafana/dashboards/pipeline-metrics.json`

### Prometheus

- URL: http://localhost:30909
- View Kubernetes metrics and system health

### Elasticsearch

- URL: http://localhost:30920
- Check indices: `curl http://localhost:30920/_cat/indices`

### HDFS NameNode UI

- URL: http://localhost:30870
- View HDFS filesystem and DataNode health

## Step 9: Testing

### Scalability Test

Test system performance with increasing load:

```bash
make test-scalability
```

This gradually increases throughput from 10 to 1000 msg/sec.

Monitor:
- Kafka consumer lag
- HDFS write throughput
- Spark processing latency
- Elasticsearch indexing rate

### Fault Tolerance Test

Test system resilience:

```bash
make test-fault-tolerance
```

This kills one replica each of:
- Kafka broker (kafka-1)
- HDFS DataNode (datanode-1)
- Elasticsearch node (elasticsearch-1)

**Expected behavior**: All components should self-recover within 30-60 seconds without data loss.

Verify recovery:
```bash
kubectl get pods -n reddit-pipeline -w
```

## Troubleshooting

### Pods Not Starting

Check pod events:
```bash
kubectl describe pod <pod-name> -n reddit-pipeline
```

Common issues:
- Insufficient resources: Reduce replicas in manifests
- Image pull errors: Check internet connectivity
- PVC issues: Ensure storage class exists

### Kafka Connection Failures

Check if Kafka is ready:
```bash
kubectl exec -n reddit-pipeline kafka-0 -- kafka-broker-api-versions --bootstrap-server localhost:9092
```

List topics:
```bash
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics --list --bootstrap-server localhost:9092
```

### HDFS Connection Issues

Check NameNode logs:
```bash
kubectl logs -n reddit-pipeline <namenode-pod>
```

Check HDFS health:
```bash
kubectl exec -n reddit-pipeline <namenode-pod> -- hdfs dfsadmin -report
```

### Elasticsearch Not Responding

Check cluster health:
```bash
curl http://localhost:30920/_cluster/health?pretty
```

Check node status:
```bash
kubectl logs -n reddit-pipeline elasticsearch-0
```

### Spark Jobs Failing

Check driver logs:
```bash
# Batch job logs will appear in terminal
# Check for Java heap issues or connection errors
```

Common fixes:
- Increase memory: Adjust `ES_JAVA_OPTS` in manifests
- Check connectivity: Verify Kafka/HDFS/ES endpoints

## Cleanup

Remove all deployed resources:

```bash
make clean
```

This deletes the entire `reddit-pipeline` namespace.

Delete the Kubernetes cluster:

```bash
# kind
kind delete cluster --name reddit-pipeline

# minikube
minikube delete

# k3s
/usr/local/bin/k3s-uninstall.sh
```

## Performance Tuning

### Increase Kafka Throughput

Edit `kafka/manifests/kafka.yaml`:
```yaml
- name: KAFKA_NUM_NETWORK_THREADS
  value: "8"
- name: KAFKA_NUM_IO_THREADS
  value: "16"
```

### Increase Spark Parallelism

Edit Makefile targets:
```makefile
run-batch:
    spark-submit --master local[8] \  # Increase from 4 to 8
        --executor-memory 4g \
        --driver-memory 2g \
        ...
```

### Increase Elasticsearch Performance

Edit `elasticsearch/manifests/elasticsearch.yaml`:
```yaml
- name: ES_JAVA_OPTS
  value: "-Xms1g -Xmx1g"  # Increase from 512m
```

## Next Steps

1. **Create Custom Dashboards**: Use Grafana to visualize your metrics
2. **Add More Metrics**: Extend Spark jobs to compute additional views
3. **Implement Alerts**: Configure Prometheus alerting rules
4. **Add Security**: Enable authentication for Kafka, Elasticsearch, Grafana
5. **Production Deployment**: Use cloud Kubernetes (EKS, GKE, AKS) for real workloads

## Additional Resources

- [Lambda Architecture Paper](http://nathanmarz.com/blog/how-to-beat-the-cap-theorem.html)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Spark Structured Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Elasticsearch Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
