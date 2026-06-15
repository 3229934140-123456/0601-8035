import math
import hashlib
import random
import json
import pickle
from typing import List, Optional, Tuple


class CuckooFilter:
    def __init__(self, capacity: int, fingerprint_bits: int = 12, bucket_size: int = 4, max_kicks: int = 500):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if fingerprint_bits < 4:
            raise ValueError("fingerprint_bits must be at least 4")
        if bucket_size <= 0:
            raise ValueError("bucket_size must be positive")

        self.fingerprint_bits = fingerprint_bits
        self.bucket_size = bucket_size
        self.max_kicks = max_kicks

        raw_buckets = (capacity + bucket_size - 1) // bucket_size
        num_buckets = self._next_power_of_two(raw_buckets)
        while num_buckets * bucket_size < capacity:
            num_buckets <<= 1
        self.num_buckets = num_buckets
        self.capacity = num_buckets * bucket_size
        self._requested_capacity = capacity

        self.buckets: List[List[Optional[int]]] = [
            [None] * bucket_size for _ in range(num_buckets)
        ]
        self.size = 0
        self._fingerprint_mask = (1 << fingerprint_bits) - 1

    def _next_power_of_two(self, n: int) -> int:
        if n == 0:
            return 1
        p = 1
        while p < n:
            p <<= 1
        return p

    def _fingerprint(self, item: str) -> int:
        data = item.encode('utf-8')
        h = int(hashlib.md5(data).hexdigest(), 16)
        fp = h & self._fingerprint_mask
        if fp == 0:
            fp = 1
        return fp

    def _index_hash(self, item: str) -> int:
        data = item.encode('utf-8')
        h = int(hashlib.sha1(data).hexdigest(), 16)
        return h % self.num_buckets

    def _alt_index(self, fp: int, i: int) -> int:
        fp_hash = hashlib.md5(str(fp).encode('utf-8')).hexdigest()
        h = int(fp_hash, 16)
        return (i ^ h) % self.num_buckets

    def _get_indices_and_fingerprint(self, item: str) -> Tuple[int, int, int]:
        fp = self._fingerprint(item)
        i1 = self._index_hash(item)
        i2 = self._alt_index(fp, i1)
        return i1, i2, fp

    def _find_bucket_index(self, bucket_idx: int, fp: int) -> Optional[int]:
        bucket = self.buckets[bucket_idx]
        for i, slot in enumerate(bucket):
            if slot == fp:
                return i
        return None

    def _find_empty_slot(self, bucket_idx: int) -> Optional[int]:
        bucket = self.buckets[bucket_idx]
        for i, slot in enumerate(bucket):
            if slot is None:
                return i
        return None

    def insert(self, item: str) -> bool:
        if self.contains(item):
            return True

        i1, i2, fp = self._get_indices_and_fingerprint(item)

        slot = self._find_empty_slot(i1)
        if slot is not None:
            self.buckets[i1][slot] = fp
            self.size += 1
            return True

        slot = self._find_empty_slot(i2)
        if slot is not None:
            self.buckets[i2][slot] = fp
            self.size += 1
            return True

        undo_log: List[Tuple[int, int, Optional[int]]] = []

        start_idx = i1 if random.random() < 0.5 else i2
        cur_idx = start_idx
        cur_fp = fp

        success = False

        for kick_step in range(self.max_kicks):
            bucket = self.buckets[cur_idx]
            slot_idx = random.randrange(len(bucket))
            evicted_fp = bucket[slot_idx]

            undo_log.append((cur_idx, slot_idx, evicted_fp))
            bucket[slot_idx] = cur_fp

            cur_fp = evicted_fp
            cur_idx = self._alt_index(cur_fp, cur_idx)

            slot = self._find_empty_slot(cur_idx)
            if slot is not None:
                undo_log.append((cur_idx, slot, None))
                self.buckets[cur_idx][slot] = cur_fp
                self.size += 1
                success = True
                break

        if not success:
            for b_idx, s_idx, orig_val in reversed(undo_log):
                self.buckets[b_idx][s_idx] = orig_val

        return success

    def contains(self, item: str) -> bool:
        i1, i2, fp = self._get_indices_and_fingerprint(item)

        if self._find_bucket_index(i1, fp) is not None:
            return True
        if self._find_bucket_index(i2, fp) is not None:
            return True

        return False

    def delete(self, item: str) -> bool:
        i1, i2, fp = self._get_indices_and_fingerprint(item)

        slot = self._find_bucket_index(i1, fp)
        if slot is not None:
            self.buckets[i1][slot] = None
            self.size -= 1
            return True

        slot = self._find_bucket_index(i2, fp)
        if slot is not None:
            self.buckets[i2][slot] = None
            self.size -= 1
            return True

        return False

    def load_factor(self) -> float:
        return self.size / self.capacity

    def memory_usage_bytes(self) -> int:
        total_bits = self.num_buckets * self.bucket_size * self.fingerprint_bits
        return (total_bits + 7) // 8

    def __len__(self) -> int:
        return self.size

    def reset(self) -> None:
        self.buckets = [[None] * self.bucket_size for _ in range(self.num_buckets)]
        self.size = 0

    def to_dict(self) -> dict:
        return {
            "requested_capacity": self._requested_capacity,
            "fingerprint_bits": self.fingerprint_bits,
            "bucket_size": self.bucket_size,
            "max_kicks": self.max_kicks,
            "num_buckets": self.num_buckets,
            "capacity": self.capacity,
            "size": self.size,
            "buckets": [
                [slot if slot is not None else 0 for slot in bucket]
                for bucket in self.buckets
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CuckooFilter":
        cf = cls(
            capacity=data["requested_capacity"],
            fingerprint_bits=data["fingerprint_bits"],
            bucket_size=data["bucket_size"],
            max_kicks=data["max_kicks"]
        )
        cf.num_buckets = data["num_buckets"]
        cf.capacity = data["capacity"]
        cf.size = data["size"]
        cf._requested_capacity = data["requested_capacity"]
        cf.buckets = [
            [slot if slot != 0 else None for slot in bucket]
            for bucket in data["buckets"]
        ]
        return cf

    def save(self, filepath: str) -> None:
        with open(filepath, 'wb') as f:
            pickle.dump(self.to_dict(), f)

    @classmethod
    def load(cls, filepath: str) -> "CuckooFilter":
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        return cls.from_dict(data)

    def save_json(self, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load_json(cls, filepath: str) -> "CuckooFilter":
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
