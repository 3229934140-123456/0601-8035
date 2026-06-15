import time
import random
import string
from counting_bloom_filter import CountingBloomFilter
from cuckoo_filter import CuckooFilter


def generate_random_string(length: int = 10) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_items(n: int) -> list:
    items = set()
    while len(items) < n:
        items.add(generate_random_string(12))
    return list(items)


def test_counting_bloom_filter():
    print("=" * 60)
    print("Testing Counting Bloom Filter")
    print("=" * 60)

    cbf = CountingBloomFilter(
        expected_items=1000,
        false_positive_rate=0.01,
        counter_bits=4
    )

    print(f"Number of counters: {cbf.num_counters}")
    print(f"Number of hashes: {cbf.num_hashes}")
    print(f"Memory usage: {cbf.memory_usage_bytes()} bytes")
    print(f"Max counter value: {cbf.max_counter}")
    print()

    items = generate_items(100)

    for item in items:
        cbf.insert(item)

    print("After inserting 100 items:")
    true_positives = sum(1 for item in items if cbf.contains(item))
    print(f"  True positives: {true_positives}/100")

    false_items = generate_items(1000)
    false_positives = sum(1 for item in false_items if item not in set(items) and cbf.contains(item))
    print(f"  False positive rate: {false_positives / 1000:.4f}")
    print(f"  Overflow risk: {cbf.overflow_risk():.4f}")
    print()

    item_to_delete = items[0]
    result = cbf.delete(item_to_delete)
    print(f"Deleted '{item_to_delete}': {result}")
    print(f"  Contains after delete: {cbf.contains(item_to_delete)}")

    remaining = items[1:]
    true_positives_after = sum(1 for item in remaining if cbf.contains(item))
    print(f"  True positives of remaining: {true_positives_after}/99")
    print()

    print("Deleting non-existent item:")
    result = cbf.delete("nonexistent_item_xyz")
    print(f"  Result: {result}")
    print()

    print("Testing counter overflow:")
    cbf_small = CountingBloomFilter(
        expected_items=10,
        false_positive_rate=0.5,
        counter_bits=2
    )
    print(f"  Max counter: {cbf_small.max_counter}")
    for i in range(10):
        cbf_small.insert("overflow_test")
    print(f"  After 10 inserts of same item, contains: {cbf_small.contains('overflow_test')}")
    print(f"  Overflow risk: {cbf_small.overflow_risk():.4f}")
    cbf_small.delete("overflow_test")
    print(f"  After 1 delete, contains: {cbf_small.contains('overflow_test')}")
    print()


def test_cuckoo_filter():
    print("=" * 60)
    print("Testing Cuckoo Filter")
    print("=" * 60)

    cf = CuckooFilter(
        capacity=1024,
        fingerprint_bits=12,
        bucket_size=4,
        max_kicks=500
    )

    print(f"Number of buckets: {cf.num_buckets}")
    print(f"Bucket size: {cf.bucket_size}")
    print(f"Total capacity: {cf.capacity}")
    print(f"Fingerprint bits: {cf.fingerprint_bits}")
    print(f"Memory usage: {cf.memory_usage_bytes()} bytes")
    print()

    items = generate_items(800)

    insert_failures = 0
    for item in items:
        if not cf.insert(item):
            insert_failures += 1

    print(f"After inserting 800 items:")
    print(f"  Insert failures: {insert_failures}")
    print(f"  Current size: {cf.size}")
    print(f"  Load factor: {cf.load_factor():.4f}")

    true_positives = sum(1 for item in items if cf.contains(item))
    print(f"  True positives: {true_positives}/800")

    false_items = generate_items(1000)
    false_positives = sum(1 for item in false_items if item not in set(items) and cf.contains(item))
    print(f"  False positive rate: {false_positives / 1000:.4f}")
    print()

    items_to_delete = items[:100]
    delete_count = 0
    for item in items_to_delete:
        if cf.delete(item):
            delete_count += 1
    print(f"Deleted 100 items: {delete_count} successful")
    print(f"  Size after deletion: {cf.size}")
    print(f"  Load factor: {cf.load_factor():.4f}")

    remaining = items[100:]
    true_positives_after = sum(1 for item in remaining if cf.contains(item))
    print(f"  True positives of remaining: {true_positives_after}/700")

    deleted_still_present = sum(1 for item in items_to_delete if cf.contains(item))
    print(f"  Deleted items still present (false pos): {deleted_still_present}/100")
    print()

    print("Testing insertion at high load:")
    cf2 = CuckooFilter(capacity=256, fingerprint_bits=12, bucket_size=4, max_kicks=200)
    for i in range(300):
        item = f"item_{i:04d}"
        result = cf2.insert(item)
        if not result:
            print(f"  Insertion failed at item {i}, load factor: {cf2.load_factor():.4f}")
            break
    print(f"  Final load factor: {cf2.load_factor():.4f}")
    print()


def benchmark_comparison():
    print("=" * 60)
    print("Benchmark Comparison")
    print("=" * 60)

    target_fp_rate = 0.01
    num_items = 10000

    cbf = CountingBloomFilter(
        expected_items=num_items,
        false_positive_rate=target_fp_rate,
        counter_bits=4
    )

    cf = CuckooFilter(
        capacity=num_items,
        fingerprint_bits=12,
        bucket_size=4,
        max_kicks=500
    )

    items = generate_items(num_items)
    test_items = generate_items(5000)

    print(f"\n{'Metric':<30} {'Counting Bloom':<20} {'Cuckoo':<20}")
    print("-" * 75)

    cbf_mem = cbf.memory_usage_bytes()
    cf_mem = cf.memory_usage_bytes()
    print(f"{'Memory (bytes)':<30} {cbf_mem:<20} {cf_mem:<20}")
    print(f"{'Memory per item (bits)':<30} {cbf_mem*8/num_items:<20.2f} {cf_mem*8/num_items:<20.2f}")

    start = time.perf_counter()
    for item in items:
        cbf.insert(item)
    cbf_insert_time = time.perf_counter() - start

    start = time.perf_counter()
    for item in items:
        cf.insert(item)
    cf_insert_time = time.perf_counter() - start

    print(f"{'Insert time (s)':<30} {cbf_insert_time:<20.4f} {cf_insert_time:<20.4f}")

    start = time.perf_counter()
    for item in test_items:
        cbf.contains(item)
    cbf_query_time = time.perf_counter() - start

    start = time.perf_counter()
    for item in test_items:
        cf.contains(item)
    cf_query_time = time.perf_counter() - start

    print(f"{'Query time (s)':<30} {cbf_query_time:<20.4f} {cf_query_time:<20.4f}")

    delete_items = items[:5000]
    start = time.perf_counter()
    for item in delete_items:
        cbf.delete(item)
    cbf_delete_time = time.perf_counter() - start

    start = time.perf_counter()
    for item in delete_items:
        cf.delete(item)
    cf_delete_time = time.perf_counter() - start

    print(f"{'Delete time (s)':<30} {cbf_delete_time:<20.4f} {cf_delete_time:<20.4f}")

    cbf_fp = sum(1 for item in test_items if item not in set(items) and cbf.contains(item))
    cf_fp = sum(1 for item in test_items if item not in set(items) and cf.contains(item))
    print(f"{'False positives':<30} {cbf_fp:<20} {cf_fp:<20}")
    print(f"{'FP rate':<30} {cbf_fp/len(test_items):<20.4f} {cf_fp/len(test_items):<20.4f}")

    print()


def test_deletion_correctness():
    print("=" * 60)
    print("Deletion Correctness Test")
    print("=" * 60)

    cbf = CountingBloomFilter(
        expected_items=1000,
        false_positive_rate=0.01,
        counter_bits=4
    )

    cf = CuckooFilter(
        capacity=1024,
        fingerprint_bits=12,
        bucket_size=4,
        max_kicks=500
    )

    items = [f"item_{i:04d}" for i in range(500)]

    for item in items:
        cbf.insert(item)
        cf.insert(item)

    print("Inserting 500 items, then deleting them one by one...")
    print()

    cbf_errors = 0
    cf_errors = 0

    for i, item in enumerate(items):
        cbf_result = cbf.delete(item)
        cf_result = cf.delete(item)

        if cbf.contains(item) and i < 490:
            cbf_errors += 1
        if cf.contains(item):
            cf_errors += 1

    print(f"Counting Bloom false positives after all deletes: {cbf_errors}")
    print(f"Cuckoo false positives after all deletes: {cf_errors}")
    print()

    cbf_empty = all(c == 0 for c in cbf.counters)
    print(f"Counting Bloom all counters zero: {cbf_empty}")
    print(f"Cuckoo size after all deletes: {cf.size}")
    print()


def main():
    random.seed(42)

    test_counting_bloom_filter()
    test_cuckoo_filter()
    benchmark_comparison()
    test_deletion_correctness()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
