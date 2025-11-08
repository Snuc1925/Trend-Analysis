# Quick Start Guide

Get the Lambda Architecture pipeline running in 10 minutes!

## Prerequisites Check

```bash
# Check Kubernetes
kubectl version --short

# Check Python
python3 --version

# Check Make
make --version
```

All should return version information. If not, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## 5-Step Deployment

### Step 1: Deploy Infrastructure (2 minutes)

```bash
make deploy
```

This deploys all components to Kubernetes. Wait for all pods to be ready:

```bash
# Watch until all show "Running" and "1/1" or "3/3" ready
watch kubectl get pods -n reddit-pipeline
```

Expected: 15 pods total (Zookeeper×3, Kafka×3, DataNode×3, Elasticsearch×3, + 3 others)

### Step 2: Generate Data (30 seconds)

```bash
make generate-historical
```

Creates 7,000 posts and 35,000 comments in `/tmp/historical_data/`

### Step 3: Start Data Flow (10 seconds)

**Terminal 1 - Consumer:**
```bash
make run-consumer
```

**Terminal 2 - Producer:**
```bash
make run-producer
```

### Step 4: Process Data (1 minute)

**Terminal 3 - Batch Processing:**
```bash
make run-batch
```

**Terminal 4 - Streaming Processing:**
```bash
make run-streaming
```

### Step 5: View Results (immediate)

Open in browser:
- **Grafana**: http://localhost:30300 (admin/admin)
- **Elasticsearch**: http://localhost:30920
- **HDFS**: http://localhost:30870
- **Prometheus**: http://localhost:30909

## What You Should See

### In the Consumer Terminal:
```
Connected to HDFS at http://localhost:30870
Bootstrapping historical data...
Saved 7000 posts to HDFS
Saved 34907 comments to HDFS
Saved 1000 users to HDFS
Bootstrap complete!
Consuming messages from Kafka...
Consumed 100 messages
Consumed 200 messages
...
```

### In the Producer Terminal:
```
Connected to Kafka at localhost:30092
Starting producer: 100 msg/sec
Produced 1000 messages (100.23 msg/sec)
Produced 2000 messages (100.11 msg/sec)
...
```

### In the Batch Processing Terminal:
```
Starting batch job...
Loaded 7000 posts, 34907 comments, 1000 users
Computing top posts per subreddit...
Computing user activity...
Computing subreddit activity...
Batch job complete!
```

### In the Streaming Terminal:
```
Starting streaming job...
Processing posts stream...
Batch: 0
+----------+----------+----------+
|window    |subreddit |num_posts |
+----------+----------+----------+
|[2024-... |python    |45        |
|[2024-... |datascien.|32        |
...
```

### In Grafana:

You should see:
1. Posts per minute graph (live updating)
2. Active subreddits table
3. Top posts by score
4. User activity trends

## Quick Tests

### Test Scalability (2 minutes)
```bash
make test-scalability
```

Gradually increases load from 10 to 1000 msg/sec and reports metrics.

### Test Fault Tolerance (2 minutes)
```bash
make test-fault-tolerance
```

Kills pods and verifies auto-recovery.

## Cleanup

When done:
```bash
make clean
```

Removes all deployed resources.

## Troubleshooting

### Pods not starting?
```bash
# Check events
kubectl describe pods -n reddit-pipeline

# Common fix: Reduce replicas if low on resources
# Edit manifests and change replicas: 3 → 1
```

### Can't connect to services?
```bash
# Check if running on minikube
minikube service list -n reddit-pipeline

# May need to use minikube IP instead of localhost
```

### Consumer can't connect to Kafka?
```bash
# Verify Kafka is ready
kubectl exec -n reddit-pipeline kafka-0 -- \
  kafka-broker-api-versions --bootstrap-server localhost:9092

# Check topics exist
kubectl exec -n reddit-pipeline kafka-0 -- \
  kafka-topics --list --bootstrap-server localhost:9092
```

## Next Steps

1. **Customize Data Generation:**
   - Edit `backend/data-generator/schemas.py` for different data
   - Modify `config.yaml` for different subreddits/users

2. **Create Dashboards:**
   - Import `grafana/dashboards/pipeline-metrics.json` in Grafana
   - Create custom queries and visualizations

3. **Add Metrics:**
   - Extend Spark jobs in `spark/batch/batch_processor.py`
   - Add new aggregations to `spark/streaming/speed_processor.py`

4. **Scale Up:**
   - Increase replicas in Helm values
   - Increase producer throughput
   - Monitor with `make status`

## Architecture at a Glance

```
Data Flow:
                                    
Producer ────▶ Kafka ────┬────▶ Speed Layer ────▶ Elasticsearch ────▶ Grafana
                         │
                         └────▶ Consumer ────▶ HDFS ────▶ Batch Layer ────┘
                                                               
Historical Data ────────────────────┘
```

## Commands Reference

| Command | Purpose |
|---------|---------|
| `make deploy` | Deploy all components |
| `make clean` | Remove all components |
| `make generate-historical` | Generate sample data |
| `make run-producer` | Start real-time producer |
| `make run-consumer` | Start consumer |
| `make run-batch` | Run batch processing |
| `make run-streaming` | Run streaming processing |
| `make test-scalability` | Test throughput |
| `make test-fault-tolerance` | Test resilience |
| `make status` | Check deployment |
| `make logs` | View logs |

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:30300 | admin/admin |
| Prometheus | http://localhost:30909 | - |
| Elasticsearch | http://localhost:30920 | - |
| HDFS UI | http://localhost:30870 | - |
| Kafka | localhost:30092 | - |

## Support

- Full documentation: [README.md](README.md)
- Setup guide: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Testing: [TESTING.md](TESTING.md)
- Deliverables: [DELIVERABLES.md](DELIVERABLES.md)

---

**Happy Data Processing! 🚀**
