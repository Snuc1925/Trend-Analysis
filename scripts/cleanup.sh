#!/bin/bash
set -e

echo "=== Cleaning up Lambda Architecture Pipeline ==="

# Delete all resources
kubectl delete namespace reddit-pipeline || true

echo "Cleanup complete!"
