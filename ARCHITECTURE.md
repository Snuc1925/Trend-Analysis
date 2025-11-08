# Architecture Documentation

## System Overview

The Lambda Architecture Big Data pipeline processes both historical and real-time Reddit-like data through separate batch and speed layers, providing a unified view of data through a serving layer.

## Architecture Layers

### 1. Data Generation Layer

#### Components

**Historical Data Generator**
- Generates bootstrap data for the past N days
- Creates JSON files partitioned by entity type (posts, comments, users)
- Configurable volume and date range
- Output: JSON line-delimited files

**Real-time Producer**
- Kafka producer generating continuous stream of events
- Configurable throughput (messages/second)
- Three event types: posts (70%), comments (25%), user updates (5%)
- Realistic data distribution across subreddits and users

#### Data Flow
```
Historical Generator → JSON Files → Consumer (Bootstrap)
Real-time Producer → Kafka Topics → Consumer (Streaming)
```

### 2. Ingestion Layer (Apache Kafka)

#### Architecture
```
┌─────────────┐
│ Zookeeper   │ (3 nodes - coordination)
│  Cluster    │
└─────────────┘
      ↓
┌─────────────────────────────────┐
│     Kafka Cluster               │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │Broker│ │Broker│ │Broker│   │ (3 brokers)
│  │  0   │ │  1   │ │  2   │   │
│  └──────┘ └──────┘ └──────┘   │
└─────────────────────────────────┘
```

#### Topics
- **reddit.posts**: Post events (3 partitions, RF=3)
- **reddit.comments**: Comment events (3 partitions, RF=3)
- **reddit.users**: User update events (3 partitions, RF=3)

#### Configuration
- Replication Factor: 3
- Min In-Sync Replicas: 2
- Log Retention: 168 hours (7 days)
- Auto-create Topics: Enabled

### 3. Batch Layer (HDFS + Spark)

#### HDFS Architecture
```
┌──────────────────┐
│    NameNode      │ (Metadata management)
│   (Active)       │
└──────────────────┘
        ↓
┌────────────────────────────────────┐
│         DataNode Cluster            │
│  ┌──────────┐ ┌──────────┐ ┌─────┐│
│  │DataNode 0│ │DataNode 1│ │DN 2 ││ (3 nodes)
│  │          │ │          │ │     ││
│  └──────────┘ └──────────┘ └─────┘│
└────────────────────────────────────┘
```

**Storage Layout:**
```
/data/
  ├── posts/
  │   └── year=YYYY/
  │       └── month=MM/
  │           └── day=DD/
  │               └── hour=HH/
  │                   └── data_TIMESTAMP.json
  ├── comments/
  │   └── [same structure]
  └── users/
      └── [same structure]
```

**Partitioning Strategy:**
- Time-based partitioning (year/month/day/hour)
- Enables efficient query pruning
- Supports incremental batch processing

#### Spark Batch Processing

**Job Architecture:**
```
┌─────────────────────────────────────────┐
│         Spark Batch Job                  │
│                                          │
│  ┌────────────┐      ┌────────────┐    │
│  │   Read     │─────▶│  Process   │    │
│  │   HDFS     │      │  Transform │    │
│  └────────────┘      └────────────┘    │
│                            ↓            │
│                      ┌────────────┐    │
│                      │   Write    │    │
│                      │   Output   │    │
│                      └────────────┘    │
└─────────────────────────────────────────┘
```

**Computed Views:**

1. **Top Posts per Subreddit**
   - Aggregation: GROUP BY subreddit, date
   - Sort: By total_score DESC
   - Output: Top-K posts per subreddit per day

2. **User Activity**
   - Join: Posts + Comments
   - Metrics: post_count, comment_count, total_score
   - Output: User activity summary

3. **Subreddit Activity**
   - Aggregation: Posts per subreddit per day
   - Metrics: num_posts, avg_score, total_comments
   - Output: Subreddit trending data

**Scheduling:**
- Cron-based periodic execution (hourly recommended)
- Incremental processing using time-based partitions
- Checkpoint support for resumable jobs

### 4. Speed Layer (Spark Structured Streaming)

#### Architecture
```
┌──────────────────────────────────────────┐
│    Spark Structured Streaming            │
│                                          │
│  ┌──────────┐      ┌──────────────┐    │
│  │  Kafka   │─────▶│   Stream     │    │
│  │  Source  │      │  Processing  │    │
│  └──────────┘      └──────────────┘    │
│                          ↓              │
│                    ┌──────────────┐    │
│                    │ Elasticsearch│    │
│                    │    Sink      │    │
│                    └──────────────┘    │
└──────────────────────────────────────────┘
```

**Processing:**
- Windowed Aggregations (1-minute windows)
- Watermarking (10-minute delay tolerance)
- Stateful Processing for incremental updates

**Output Modes:**
- Update: For aggregations
- Append: For individual records

**Checkpointing:**
- Location: `/tmp/checkpoint` (configurable)
- Enables exactly-once semantics
- Supports failure recovery

### 5. Serving Layer (Elasticsearch)

#### Architecture
```
┌─────────────────────────────────────┐
│    Elasticsearch Cluster            │
│                                     │
│  ┌──────┐  ┌──────┐  ┌──────┐     │
│  │ ES-0 │  │ ES-1 │  │ ES-2 │     │ (3 nodes)
│  │Master│  │Master│  │Master│     │
│  │ Data │  │ Data │  │ Data │     │
│  └──────┘  └──────┘  └──────┘     │
└─────────────────────────────────────┘
```

**Indices:**

1. **views_top_posts_v1**
   - Source: Batch layer
   - Schema: subreddit, date, post_id, title, score
   - Purpose: Display top posts

2. **views_subreddit_activity_v1**
   - Source: Speed layer + Batch layer
   - Schema: subreddit, window, num_posts, total_score
   - Purpose: Real-time subreddit metrics

3. **views_user_activity_v1**
   - Source: Batch layer
   - Schema: user_id, num_posts, num_comments, total_score
   - Purpose: User engagement metrics

**Configuration:**
- Replicas: 3
- Shards: Auto-configured
- Security: Disabled for dev (enable for prod)

### 6. Visualization Layer (Grafana)

#### Architecture
```
┌───────────────────────────────────┐
│         Grafana                    │
│                                    │
│  ┌──────────────────────────┐    │
│  │   Dashboard Engine       │    │
│  └──────────────────────────┘    │
│              ↓                    │
│  ┌──────────────────────────┐    │
│  │ Elasticsearch Datasource │    │
│  └──────────────────────────┘    │
└───────────────────────────────────┘
```

**Dashboards:**
- **Pipeline Metrics**: Real-time throughput, posts per minute
- **Subreddit Activity**: Top subreddits by activity
- **User Engagement**: Active users, top contributors
- **System Health**: Kafka lag, HDFS utilization, ES cluster health

### 7. Monitoring Layer (Prometheus)

#### Architecture
```
┌─────────────────────────────────────┐
│         Prometheus                   │
│                                      │
│  ┌────────────────────────────┐    │
│  │    Metrics Scraper         │    │
│  └────────────────────────────┘    │
│              ↓                      │
│  ┌────────────────────────────┐    │
│  │      Time Series DB        │    │
│  └────────────────────────────┘    │
└─────────────────────────────────────┘
```

**Scraped Metrics:**
- Kubernetes pod metrics
- Kafka broker metrics
- HDFS metrics
- Elasticsearch cluster metrics
- Spark job metrics

**Retention:**
- Default: 15 days
- Configurable via prometheus.yaml

## Data Flow

### Bootstrap Flow
```
Historical Data → Consumer → HDFS (partitioned)
                              ↓
                         Batch Processing
                              ↓
                        Elasticsearch
```

### Streaming Flow
```
Real-time Producer → Kafka → Speed Layer → Elasticsearch
                       ↓
                   Consumer → HDFS → Batch Layer → Elasticsearch
```

### Query Flow
```
User → Grafana → Elasticsearch → [Batch Views + Speed Views]
```

## Scalability

### Horizontal Scaling

**Kafka:**
- Add brokers: Increase `kafka.replicas` in values.yaml
- Rebalance partitions automatically

**HDFS:**
- Add DataNodes: Increase `hdfs.datanode.replicas`
- Rebalance blocks: `hdfs balancer`

**Elasticsearch:**
- Add nodes: Increase `elasticsearch.replicas`
- Rebalance shards automatically

**Spark:**
- Increase executors: Modify `--num-executors` flag
- Increase cores: Modify `--executor-cores` flag

### Vertical Scaling

**Memory:**
- Kafka: Adjust `KAFKA_HEAP_OPTS`
- Spark: Adjust `--executor-memory`, `--driver-memory`
- Elasticsearch: Adjust `ES_JAVA_OPTS`

**CPU:**
- Kubernetes: Modify resource requests/limits
- Spark: Increase parallelism in jobs

## Fault Tolerance

### Component Failures

**Kafka Broker Failure:**
- Impact: Minimal (RF=3, min ISR=2)
- Recovery: Automatic leader election
- Data Loss: None if min ISR maintained

**HDFS DataNode Failure:**
- Impact: Minimal (RF=3)
- Recovery: Automatic block replication
- Data Loss: None if ≥1 replica available

**Elasticsearch Node Failure:**
- Impact: Minimal (3 nodes)
- Recovery: Automatic shard reallocation
- Data Loss: None if replicas exist

**Spark Executor Failure:**
- Impact: Task retry
- Recovery: Automatic from checkpoint
- Data Loss: None (checkpointing enabled)

### Network Partitions

**Kafka:**
- Unclean leader election: Disabled
- Min ISR: Prevents data loss

**HDFS:**
- Lease recovery for files
- Automatic failover (HA setup)

**Elasticsearch:**
- Split-brain prevention
- Minimum master nodes configuration

## Performance Characteristics

### Throughput

**Target:**
- Kafka: 5,000 messages/second
- HDFS Write: 100 MB/second
- Spark Batch: Process 1M records/minute
- Spark Streaming: <1 second latency
- Elasticsearch: 10,000 docs/second

**Actual (Typical):**
- Depends on resource allocation
- Tune using scalability tests

### Latency

**Batch Layer:**
- Processing: Hours (full dataset)
- Query: Seconds (indexed data)

**Speed Layer:**
- Processing: <1 second
- Query: Milliseconds

**End-to-End:**
- Producer → Elasticsearch: <2 seconds
- Producer → HDFS: <1 second

## Security Considerations

### Current (Development)

- No authentication
- No encryption
- No authorization

### Production Recommendations

**Kafka:**
- Enable SASL/SSL
- ACLs for topic access
- Encryption in transit and at rest

**HDFS:**
- Kerberos authentication
- HDFS permissions
- Encryption zones

**Elasticsearch:**
- X-Pack Security
- Role-based access control
- TLS/SSL encryption

**Grafana:**
- LDAP/OAuth integration
- Dashboard permissions
- API key management

## Monitoring & Alerts

### Key Metrics

**Pipeline Health:**
- Kafka consumer lag
- HDFS disk utilization
- Elasticsearch indexing rate
- Spark job duration

**System Health:**
- Pod restarts
- CPU/Memory utilization
- Network I/O
- Disk I/O

### Alerting Rules

- Consumer lag > 1000 messages
- HDFS disk > 80% full
- Elasticsearch heap > 75%
- Pod restart rate > 3/hour
- Job failure rate > 10%

## Deployment Topology

### Development (Local)

```
Kind Cluster
├── Control Plane (1 node)
└── Workers (3 nodes)
    ├── Kafka + Zookeeper
    ├── HDFS
    ├── Elasticsearch
    └── Monitoring
```

### Production (Cloud)

```
Kubernetes Cluster
├── Master Nodes (3)
├── Kafka Nodes (3-5)
├── HDFS Nodes (3-10)
├── Spark Nodes (5-20)
├── Elasticsearch Nodes (3-5)
└── Monitoring Nodes (2-3)
```

## Future Enhancements

1. **Exactly-Once Semantics**: Enable Kafka transactions
2. **Schema Evolution**: Integrate Schema Registry
3. **ML Integration**: Add ML models for predictions
4. **Advanced Analytics**: Sentiment analysis, trend detection
5. **Multi-Region**: Deploy across regions for HA
6. **Data Lake**: Add S3/MinIO for long-term storage
7. **Stream Processing**: Add Flink as alternative to Spark
8. **Real-time Alerts**: Integrate with PagerDuty/Slack
