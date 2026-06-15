import math
import hashlib
import json
import pickle
from typing import List


class CountingBloomFilter:
    def __init__(self, expected_items: int, false_positive_rate: float, counter_bits: int = 4):
        if expected_items <= 0:
            raise ValueError("expected_items must be positive")
        if not (0 < false_positive_rate < 1):
            raise ValueError("false_positive_rate must be between 0 and 1")
        if counter_bits < 1:
            raise ValueError("counter_bits must be at least 1")

        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate
        self.counter_bits = counter_bits
        self.max_counter = (1 << counter_bits) - 1

        self.num_counters = self._calculate_num_counters(expected_items, false_positive_rate)
        self.num_hashes = self._calculate_num_hashes(self.num_counters, expected_items)

        self.counters: List[int] = [0] * self.num_counters
        self._seed = 0x9E3779B1

    def _calculate_num_counters(self, n: int, p: float) -> int:
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return max(1, int(math.ceil(m)))

    def _calculate_num_hashes(self, m: int, n: int) -> int:
        k = (m / n) * math.log(2)
        return max(1, int(round(k)))

    def _get_hashes(self, item: str) -> List[int]:
        hashes = []
        data = item.encode('utf-8')
        h1 = int(hashlib.md5(data).hexdigest(), 16)
        h2 = int(hashlib.sha1(data).hexdigest(), 16)

        for i in range(self.num_hashes):
            combined_hash = (h1 + i * h2) % self.num_counters
            hashes.append(combined_hash)

        return hashes

    def insert(self, item: str) -> None:
        indices = self._get_hashes(item)
        for idx in indices:
            if self.counters[idx] < self.max_counter:
                self.counters[idx] += 1

    def contains(self, item: str) -> bool:
        indices = self._get_hashes(item)
        for idx in indices:
            if self.counters[idx] == 0:
                return False
        return True

    def delete(self, item: str) -> bool:
        if not self.contains(item):
            return False

        indices = self._get_hashes(item)
        for idx in indices:
            if self.counters[idx] > 0:
                self.counters[idx] -= 1
        return True

    def count(self) -> int:
        min_count = float('inf')
        for c in self.counters:
            if c > 0:
                min_count = min(min_count, c)
        return 0 if min_count == float('inf') else min_count

    def __len__(self) -> int:
        return self.num_counters

    def memory_usage_bytes(self) -> int:
        return (self.num_counters * self.counter_bits + 7) // 8

    def overflow_risk(self) -> float:
        overflowed = sum(1 for c in self.counters if c >= self.max_counter)
        return overflowed / self.num_counters

    def reset(self) -> None:
        self.counters = [0] * self.num_counters

    def to_dict(self) -> dict:
        return {
            "expected_items": self.expected_items,
            "false_positive_rate": self.false_positive_rate,
            "counter_bits": self.counter_bits,
            "max_counter": self.max_counter,
            "num_counters": self.num_counters,
            "num_hashes": self.num_hashes,
            "counters": list(self.counters)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CountingBloomFilter":
        cbf = cls(
            expected_items=data["expected_items"],
            false_positive_rate=data["false_positive_rate"],
            counter_bits=data["counter_bits"]
        )
        cbf.max_counter = data["max_counter"]
        cbf.num_counters = data["num_counters"]
        cbf.num_hashes = data["num_hashes"]
        cbf.counters = list(data["counters"])
        return cbf

    def save(self, filepath: str) -> None:
        with open(filepath, 'wb') as f:
            pickle.dump(self.to_dict(), f)

    @classmethod
    def load(cls, filepath: str) -> "CountingBloomFilter":
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        return cls.from_dict(data)

    def save_json(self, filepath: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load_json(cls, filepath: str) -> "CountingBloomFilter":
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
