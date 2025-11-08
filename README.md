# Lambda Architecture Big Data Pipeline

A comprehensive Big Data pipeline implementing the Lambda Architecture for processing simulated Reddit-like data. The system processes both batch and real-time streaming data using Apache Kafka, HDFS, Spark, Elasticsearch, and Grafana, all deployed on Kubernetes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Generation                          │
│  ┌──────────────────┐         ┌─────────────────────────────┐  │
│  │ Historical Data  │────────▶│ Real-time Data Producer     │  │
│  │   Generator      │         │   (Kafka Producer)          │  │
│  └──────────────────┘         └─────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   Apache Kafka      │
                          │  (3 brokers)        │
                          └──────────┬──────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                  │                  │
        ┌─────────▼─────────┐       │      ┌──────────▼─────────┐
        │   Batch Layer     │       │      │   Speed Layer      │
        │                   │       │      │                    │
        │  HDFS Storage     │       │      │  Spark Streaming   │
        │  (partitioned by  │       │      │  (Kafka → ES)      │
        │   year/month/day) │       │      │                    │
        │       ↓           │       │      └──────────┬─────────┘
        │  Spark Batch      │       │                 │
        │  Processing       │       │                 │
        └─────────┬─────────┘       │                 │
                  │                 │                 │
                  └─────────────────┼─────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  Elasticsearch    │
                          │  (Serving Layer)  │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │     Grafana       │
                          │  (Visualization)  │
                          └───────────────────┘
```

## Features

### Lambda Architecture Components

1. **Batch Layer**
   - Historical data stored in HDFS (partitioned by year/month/day/hour)
   - Spark batch jobs compute precomputed views
   - Metrics: top-k posts per subreddit, user activity, subreddit trends

2. **Speed Layer**
   - Spark Structured Streaming processes real-time Kafka data
   - Incremental updates written directly to Elasticsearch
   - Low-latency processing for real-time insights

3. **Serving Layer**
   - Elasticsearch stores both batch and streaming results
   - Unified query interface for batch and real-time views

### Infrastructure

- **Kubernetes Deployment**: Multi-node setup with StatefulSets for distributed components
- **Kafka**: 3-broker cluster with Zookeeper for coordination
- **HDFS**: NameNode + 3 DataNodes with replication factor 3
- **Elasticsearch**: 3-node cluster for high availability
- **Grafana**: Visualization dashboards
- **Prometheus**: Metrics collection and monitoring

### Data Pipeline

1. **Bootstrap Phase**: Historical data loaded from JSON files into HDFS
2. **Streaming Phase**: Real-time data flows through Kafka to both HDFS and Spark Streaming
3. **Processing**: Batch and speed layers compute aggregated views
4. **Visualization**: Grafana dashboards display real-time metrics

## Prerequisites

- Kubernetes cluster (kind, k3s, or minikube recommended)
- kubectl configured
- Python 3.8+
- Apache Spark 3.4+
- Make

## Quick Start

### 1. Install Dependencies

```bash
make install
```

### 2. Deploy Infrastructure

```bash
make deploy
```

This will deploy:
- Zookeeper (3 replicas)
- Kafka (3 brokers)
- HDFS (1 NameNode, 3 DataNodes)
- Elasticsearch (3 nodes)
- Grafana
- Prometheus

Wait for all pods to be ready:

```bash
make status
```

### 3. Generate Historical Data

```bash
make generate-historical
```

This creates 7 days of historical data in `/tmp/historical_data/`.

### 4. Start Data Pipeline

#### Start Consumer (Bootstrap + Streaming)

```bash
make run-consumer
```

This will:
1. Bootstrap historical data to HDFS
2. Start consuming real-time data from Kafka

#### Start Producer (in another terminal)

```bash
make run-producer
```

This produces data to Kafka at 100 messages/second.

### 5. Run Processing Jobs

#### Batch Processing

```bash
make run-batch
```

Processes all HDFS data and computes aggregated views.

#### Streaming Processing

```bash
make run-streaming
```

Processes real-time Kafka data and writes to Elasticsearch.

### 6. Access Dashboards

- **Grafana**: http://localhost:30300 (admin/admin)
- **Prometheus**: http://localhost:30909
- **Elasticsearch**: http://localhost:30920
- **HDFS UI**: http://localhost:30870

## Testing

### Scalability Testing

Test the pipeline with increasing throughput:

```bash
make test-scalability
```

This gradually increases message rate from 10 to 1000 msg/sec.

### Fault Tolerance Testing

Test system resilience by killing pods:

```bash
make test-fault-tolerance
```

This kills one replica each of:
- Kafka broker
- HDFS DataNode
- Elasticsearch node

The system should self-recover without data loss.

## Project Structure

```
.
├── backend/
│   └── data-generator/
│       ├── schemas.py              # Data schemas
│       ├── historical_generator.py # Historical data generator
│       ├── realtime_producer.py    # Kafka producer
│       └── consumer.py             # Data consumer (bootstrap + streaming)
├── spark/
│   ├── batch/
│   │   └── batch_processor.py      # Batch layer processing
│   └── streaming/
│       └── speed_processor.py      # Speed layer processing
├── kafka/
│   └── manifests/
│       ├── zookeeper.yaml          # Zookeeper StatefulSet
│       └── kafka.yaml              # Kafka StatefulSet
├── hdfs/
│   └── manifests/
│       ├── namenode.yaml           # HDFS NameNode
│       └── datanode.yaml           # HDFS DataNode StatefulSet
├── elasticsearch/
│   └── manifests/
│       └── elasticsearch.yaml      # Elasticsearch StatefulSet
├── grafana/
│   └── manifests/
│       └── grafana.yaml            # Grafana Deployment
├── prometheus/
│   └── manifests/
│       └── prometheus.yaml         # Prometheus Deployment
├── scripts/
│   ├── deploy.sh                   # Deployment script
│   ├── cleanup.sh                  # Cleanup script
│   ├── test_scalability.sh         # Scalability test
│   └── test_fault_tolerance.sh     # Fault tolerance test
├── Makefile                        # Build automation
└── requirements.txt                # Python dependencies
```

## Data Schemas

### Post

```json
{
  "post_id": "string",
  "user_id": "string",
  "subreddit": "string",
  "title": "string",
  "content": "string",
  "score": "integer",
  "num_comments": "integer",
  "created_utc": "timestamp",
  "timestamp": "timestamp"
}
```

### Comment

```json
{
  "comment_id": "string",
  "post_id": "string",
  "user_id": "string",
  "content": "string",
  "score": "integer",
  "created_utc": "timestamp",
  "timestamp": "timestamp"
}
```

### User

```json
{
  "user_id": "string",
  "username": "string",
  "karma": "integer",
  "created_utc": "timestamp",
  "timestamp": "timestamp"
}
```

## Kafka Topics

- `reddit.posts`: Post events
- `reddit.comments`: Comment events
- `reddit.users`: User update events

All topics use 3 partitions with replication factor 3.

## HDFS Structure

```
/data/
  ├── posts/
  │   └── year=2024/
  │       └── month=11/
  │           └── day=08/
  │               └── hour=06/
  │                   └── data_*.json
  ├── comments/
  │   └── ...
  └── users/
      └── ...
```

## Elasticsearch Indices

- `views_top_posts_v1`: Top posts per subreddit
- `views_subreddit_activity_v1`: Subreddit activity metrics
- `views_user_activity_v1`: User activity metrics

## Performance Characteristics

- **Target Throughput**: 5,000 messages/second
- **Latency**: <1 second for speed layer
- **Replication Factor**: 3 (Kafka, HDFS, Elasticsearch)
- **Fault Tolerance**: Survives single node failures
- **Scalability**: Horizontal scaling of all components

## Monitoring

### Prometheus Metrics

- Kafka broker metrics
- HDFS metrics
- Elasticsearch cluster health
- Spark job metrics

### Grafana Dashboards

Create dashboards for:
- Posts per minute
- Active users
- Top subreddits
- System throughput (TPS)
- Pipeline latency

## Cleanup

Remove all deployed resources:

```bash
make clean
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n reddit-pipeline
```

### View Logs

```bash
# All logs
make logs

# Specific component
kubectl logs -n reddit-pipeline <pod-name>
```

### Restart Failed Pods

```bash
kubectl delete pod <pod-name> -n reddit-pipeline
```

### Check Kafka Topics

```bash
kubectl exec -n reddit-pipeline kafka-0 -- kafka-topics --list --bootstrap-server localhost:9092
```

### Check HDFS Health

```bash
kubectl exec -n reddit-pipeline <namenode-pod> -- hdfs dfsadmin -report
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Apache Kafka for message streaming
- Apache Spark for batch and streaming processing
- Apache Hadoop HDFS for distributed storage
- Elasticsearch for search and analytics
- Grafana for visualization
- Prometheus for monitoring