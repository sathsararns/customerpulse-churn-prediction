"""Create the local stream topics without changing existing topics or offsets."""

from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaError, KafkaException
from streaming.runtime import StreamSettings


def main():
    settings = StreamSettings.from_env()
    admin = AdminClient({"bootstrap.servers": settings.bootstrap_servers})
    topics = [settings.customer_topic, settings.prediction_topic, settings.dead_letter_topic]
    futures = admin.create_topics([NewTopic(name, num_partitions=3, replication_factor=1,
                                           config={"retention.ms": "604800000"}) for name in topics])
    for name, future in futures.items():
        try:
            future.result(timeout=30)
        except KafkaException as error:
            if error.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                raise
        print(f"Topic ready: {name}", flush=True)


if __name__ == "__main__":
    main()
