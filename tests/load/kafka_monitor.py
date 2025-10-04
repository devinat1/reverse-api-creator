#!/usr/bin/env python3
"""
Kafka Consumer Lag Monitor for CloudCruise Load Testing.

This script monitors Kafka consumer lag in real-time during load testing
to help identify bottlenecks and measure throughput.

Usage:
    python tests/load/kafka_monitor.py

    # Monitor for specific duration (seconds)
    python tests/load/kafka_monitor.py --duration 120

    # Export metrics to file
    python tests/load/kafka_monitor.py --output metrics.json

Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS: Kafka broker address (default: localhost:9094)
    KAFKA_TOPIC: Topic to monitor (default: har-uploads)
    KAFKA_CONSUMER_GROUP: Consumer group to monitor (default: har-processor)
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List
from kafka.protocol.commit import OffsetFetchRequest_v1
from kafka.protocol.offset import OffsetRequest_v0

try:
    from kafka import KafkaAdminClient, KafkaConsumer
    from kafka.admin import ConfigResource, ConfigResourceType
    from kafka.structs import TopicPartition, OffsetAndMetadata
except ImportError:
    print("ERROR: kafka-python not installed. Run: uv pip install kafka-python")
    sys.exit(1)


class KafkaMonitor:
    """Monitor Kafka consumer lag and throughput."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        consumer_group: str
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.consumer_group = consumer_group
        self.metrics_history: List[Dict] = []

        # Initialize Kafka clients
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id="lag_monitor"
            )
            self.consumer = KafkaConsumer(
                bootstrap_servers=bootstrap_servers,
                group_id=f"{consumer_group}_monitor",
                enable_auto_commit=False
            )
        except Exception as e:
            print(f"ERROR: Failed to connect to Kafka: {e}")
            sys.exit(1)

    def get_topic_partitions(self) -> List[TopicPartition]:
        """Get all partitions for the topic."""
        partitions = self.consumer.partitions_for_topic(self.topic)
        if partitions is None:
            return []
        return [TopicPartition(self.topic, p) for p in partitions]

    def get_consumer_offsets(self, partitions: List[TopicPartition]) -> Dict[int, int]:
        """Get current consumer offsets for all partitions."""
        offsets = {}

        try:
            for partition in partitions:
                try:
                    # Try to get committed offset for this partition
                    committed = self.consumer.committed(partition)
                    offsets[partition.partition] = committed if committed is not None else 0
                except Exception as e:
                    print(f"Warning: Could not get offset for partition {partition.partition}: {e}")
                    offsets[partition.partition] = 0

        except Exception as e:
            print(f"ERROR getting consumer offsets: {e}")

        return offsets

    def get_end_offsets(self, partitions: List[TopicPartition]) -> Dict[int, int]:
        """Get the end (latest) offsets for all partitions."""
        end_offsets = self.consumer.end_offsets(partitions)
        return {tp.partition: offset for tp, offset in end_offsets.items()}

    def calculate_lag(self) -> Dict:
        """Calculate consumer lag for all partitions."""
        partitions = self.get_topic_partitions()

        if not partitions:
            return {
                "error": f"Topic '{self.topic}' not found or has no partitions",
                "total_lag": 0,
                "partitions": {}
            }

        consumer_offsets = self.get_consumer_offsets(partitions)
        end_offsets = self.get_end_offsets(partitions)

        partition_lag = {}
        total_lag = 0

        for partition in partitions:
            p_num = partition.partition
            consumer_offset = consumer_offsets.get(p_num, 0)
            end_offset = end_offsets.get(p_num, 0)
            lag = max(0, end_offset - consumer_offset)

            partition_lag[p_num] = {
                "consumer_offset": consumer_offset,
                "end_offset": end_offset,
                "lag": lag
            }
            total_lag += lag

        return {
            "timestamp": datetime.now().isoformat(),
            "total_lag": total_lag,
            "partitions": partition_lag,
            "num_partitions": len(partitions)
        }

    def monitor_loop(self, duration: int = None, interval: int = 2):
        """
        Continuously monitor consumer lag.

        Args:
            duration: How long to monitor in seconds (None = forever)
            interval: Seconds between checks
        """
        start_time = time.time()
        iteration = 0

        print(f"\nMonitoring Kafka Consumer Lag")
        print(f"Topic: {self.topic}")
        print(f"Consumer Group: {self.consumer_group}")
        print(f"Interval: {interval}s")
        if duration:
            print(f"Duration: {duration}s")
        print("=" * 80)

        try:
            while True:
                iteration += 1
                lag_data = self.calculate_lag()

                if "error" in lag_data:
                    print(f"\nERROR: {lag_data['error']}")
                    break

                # Store metrics
                self.metrics_history.append(lag_data)

                # Display current metrics
                elapsed = time.time() - start_time
                print(f"\n[{iteration}] Time: {elapsed:.1f}s | "
                      f"Total Lag: {lag_data['total_lag']} messages")

                # Display per-partition details
                for p_num, p_data in lag_data["partitions"].items():
                    print(f"  Partition {p_num}: "
                          f"consumer={p_data['consumer_offset']:>8} | "
                          f"end={p_data['end_offset']:>8} | "
                          f"lag={p_data['lag']:>6}")

                # Calculate throughput if we have history
                if len(self.metrics_history) >= 2:
                    prev = self.metrics_history[-2]
                    curr = self.metrics_history[-1]

                    # Calculate messages processed per second
                    total_processed = 0
                    for p_num in curr["partitions"]:
                        curr_offset = curr["partitions"][p_num]["consumer_offset"]
                        prev_offset = prev["partitions"][p_num]["consumer_offset"]
                        total_processed += (curr_offset - prev_offset)

                    throughput = total_processed / interval
                    print(f"  Throughput: {throughput:.2f} messages/second")

                # Check duration
                if duration and elapsed >= duration:
                    print(f"\nMonitoring complete after {duration}s")
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")

    def export_metrics(self, output_file: str):
        """Export collected metrics to JSON file."""
        if not self.metrics_history:
            print("No metrics to export")
            return

        with open(output_file, "w") as f:
            json.dump({
                "topic": self.topic,
                "consumer_group": self.consumer_group,
                "bootstrap_servers": self.bootstrap_servers,
                "metrics": self.metrics_history,
                "summary": self._calculate_summary()
            }, f, indent=2)

        print(f"\nMetrics exported to: {output_file}")

    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics from metrics history."""
        if not self.metrics_history:
            return {}

        lags = [m["total_lag"] for m in self.metrics_history]

        return {
            "total_measurements": len(self.metrics_history),
            "avg_lag": sum(lags) / len(lags),
            "max_lag": max(lags),
            "min_lag": min(lags),
            "final_lag": lags[-1]
        }

    def print_summary(self):
        """Print summary of monitoring session."""
        summary = self._calculate_summary()

        if not summary:
            return

        print("\n" + "=" * 80)
        print("MONITORING SUMMARY")
        print("=" * 80)
        print(f"Total Measurements: {summary['total_measurements']}")
        print(f"Average Lag: {summary['avg_lag']:.2f} messages")
        print(f"Max Lag: {summary['max_lag']} messages")
        print(f"Min Lag: {summary['min_lag']} messages")
        print(f"Final Lag: {summary['final_lag']} messages")
        print("=" * 80)

    def close(self):
        """Close Kafka connections."""
        self.consumer.close()
        self.admin_client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Kafka consumer lag during load testing"
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094"),
        help="Kafka bootstrap servers"
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("KAFKA_TOPIC", "har-uploads"),
        help="Kafka topic to monitor"
    )
    parser.add_argument(
        "--consumer-group",
        default=os.getenv("KAFKA_CONSUMER_GROUP", "har-processor"),
        help="Consumer group to monitor"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Monitoring duration in seconds (default: run forever)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Interval between checks in seconds (default: 2)"
    )
    parser.add_argument(
        "--output",
        help="Export metrics to JSON file"
    )

    args = parser.parse_args()

    # Create monitor
    monitor = KafkaMonitor(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        consumer_group=args.consumer_group
    )

    try:
        # Run monitoring loop
        monitor.monitor_loop(duration=args.duration, interval=args.interval)

        # Print summary
        monitor.print_summary()

        # Export if requested
        if args.output:
            monitor.export_metrics(args.output)

    finally:
        monitor.close()


if __name__ == "__main__":
    main()
