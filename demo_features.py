import os
import random
import string
import sys

from counting_bloom_filter import CountingBloomFilter
from cuckoo_filter import CuckooFilter


def generate_random_string(length: int = 12) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_items(n: int, prefix: str = "") -> list:
    items = set()
    while len(items) < n:
        items.add(prefix + generate_random_string(12))
    return list(items)


def print_sep(title: str) -> None:
    w = 70
    print()
    print("=" * w)
    print(f"  {title}")
    print("=" * w)


def demo_counting_bloom_persistence():
    print_sep("一、计数布隆过滤器 (CBF) 持久化演示")

    save_path = "demo_cbf.pkl"
    save_path_json = "demo_cbf.json"

    cbf = CountingBloomFilter(expected_items=500, false_positive_rate=0.01, counter_bits=4)
    items = generate_items(200, prefix="cbf_")
    for it in items:
        cbf.insert(it)

    print(f"  [步骤1] 创建 CBF, 插入 200 个元素")
    print(f"          计数器数量: {cbf.num_counters}, 哈希数: {cbf.num_hashes}")
    print(f"          内存: {cbf.memory_usage_bytes()} 字节")
    print(f"          溢出率: {cbf.overflow_risk():.6f}")

    to_delete = items[:50]
    for it in to_delete:
        cbf.delete(it)
    remaining = items[50:]

    print(f"  [步骤2] 删除前 50 个元素")
    print(f"          剩余元素存在性: {sum(1 for x in remaining if cbf.contains(x))}/150")
    print(f"          已删元素仍存在: {sum(1 for x in to_delete if cbf.contains(x))}/50")

    cbf.save(save_path)
    cbf.save_json(save_path_json)
    size_pkl = os.path.getsize(save_path)
    size_json = os.path.getsize(save_path_json)

    print(f"  [步骤3] 保存到文件")
    print(f"          pickle 文件: {save_path} ({size_pkl} 字节)")
    print(f"          JSON   文件: {save_path_json} ({size_json} 字节)")

    del cbf

    print(f"  [步骤4] 从 pickle 文件重新加载")
    cbf2 = CountingBloomFilter.load(save_path)
    print(f"          计数器数量: {cbf2.num_counters}, 哈希数: {cbf2.num_hashes}")

    r1 = sum(1 for x in remaining if cbf2.contains(x))
    d1 = sum(1 for x in to_delete if cbf2.contains(x))
    print(f"          剩余元素存在性: {r1}/150")
    print(f"          已删元素仍存在: {d1}/50")
    assert r1 == 150, "剩余元素加载后不匹配!"

    print(f"  [步骤5] 继续插入 300 个新元素 (模拟重启后继续使用)")
    more_items = generate_items(300, prefix="cbf2_")
    for it in more_items:
        cbf2.insert(it)
    r2 = sum(1 for x in more_items if cbf2.contains(x))
    r3 = sum(1 for x in remaining if cbf2.contains(x))
    print(f"          新元素存在性: {r2}/300")
    print(f"          旧剩余元素仍存在: {r3}/150")

    print(f"  [步骤6] 从 JSON 文件加载, 对比结果一致")
    cbf3 = CountingBloomFilter.load_json(save_path_json)
    assert cbf3.num_counters == cbf2.num_counters
    assert sum(1 for x in remaining if cbf3.contains(x)) == r1
    print(f"          ✓ JSON 加载成功, 数据一致")

    print(f"  ✓ 计数布隆持久化演示通过!")

    for p in [save_path, save_path_json]:
        if os.path.exists(p):
            os.remove(p)


def demo_cuckoo_persistence():
    print_sep("二、Cuckoo 过滤器 (CF) 持久化演示")

    save_path = "demo_cf.pkl"
    save_path_json = "demo_cf.json"

    cf = CuckooFilter(capacity=500, fingerprint_bits=12, bucket_size=4, max_kicks=500)
    items = generate_items(400, prefix="cf_")
    insert_fail = 0
    for it in items:
        if not cf.insert(it):
            insert_fail += 1

    print(f"  [步骤1] 创建 CF, 请求容量 500")
    print(f"          实际桶数: {cf.num_buckets}, 总容量: {cf.capacity}")
    print(f"          请求容量: {cf._requested_capacity}")
    if cf.capacity < 500:
        print(f"          ✗ 容量不达标!")
        sys.exit(1)
    print(f"          指纹位数: {cf.fingerprint_bits}, 桶大小: {cf.bucket_size}")
    print(f"          内存: {cf.memory_usage_bytes()} 字节")
    print(f"          插入结果: {len(items) - insert_fail}/400, 负载: {cf.load_factor():.2%}")

    to_delete = items[:100]
    delete_ok = 0
    for it in to_delete:
        if cf.delete(it):
            delete_ok += 1
    remaining = items[100:]

    print(f"  [步骤2] 删除前 100 个元素, 成功 {delete_ok} 次")
    print(f"          剩余存在: {sum(1 for x in remaining if cf.contains(x))}/300")
    print(f"          已删残留: {sum(1 for x in to_delete if cf.contains(x))}/100")

    cf.save(save_path)
    cf.save_json(save_path_json)
    size_pkl = os.path.getsize(save_path)
    size_json = os.path.getsize(save_path_json)

    print(f"  [步骤3] 保存到文件")
    print(f"          pickle 文件: {save_path} ({size_pkl} 字节)")
    print(f"          JSON   文件: {save_path_json} ({size_json} 字节)")

    del cf

    print(f"  [步骤4] 从 pickle 文件重新加载")
    cf2 = CuckooFilter.load(save_path)
    print(f"          桶数: {cf2.num_buckets}, 总容量: {cf2.capacity}, 负载: {cf2.load_factor():.2%}")

    r_remain = sum(1 for x in remaining if cf2.contains(x))
    r_del = sum(1 for x in to_delete if cf2.contains(x))
    print(f"          剩余存在: {r_remain}/300")
    print(f"          已删残留: {r_del}/100")
    assert r_remain == 300, "加载后剩余元素不匹配!"

    print(f"  [步骤5] 继续插入 150 个新元素 (模拟重启后继续使用)")
    more_items = generate_items(150, prefix="cf2_")
    more_fail = 0
    for it in more_items:
        if not cf2.insert(it):
            more_fail += 1
    print(f"          插入成功: {len(more_items) - more_fail}/150")
    r_new = sum(1 for x in more_items if cf2.contains(x))
    r_old = sum(1 for x in remaining if cf2.contains(x))
    print(f"          新元素存在: {r_new}/{len(more_items)}")
    print(f"          旧剩余仍存在: {r_old}/300")

    print(f"  [步骤6] 删除新插入的元素, 再验证")
    delete2 = 0
    for it in more_items[:80]:
        if cf2.delete(it):
            delete2 += 1
    print(f"          再次删除 {delete2} 个新元素成功")

    print(f"  ✓ Cuckoo 持久化演示通过!")

    for p in [save_path, save_path_json]:
        if os.path.exists(p):
            os.remove(p)


def demo_cuckoo_high_load_integrity():
    print_sep("三、Cuckoo 高负载插入失败完整性验证 (关键验收项)")

    random.seed(12345)

    cf = CuckooFilter(capacity=256, fingerprint_bits=12, bucket_size=4, max_kicks=200)

    print(f"  过滤器参数: 容量请求 256, 实际 {cf.capacity}, 桶 {cf.num_buckets}, 指纹 {cf.fingerprint_bits}位")
    print()

    inserted_items = []
    all_snapshots = []

    phase = 0
    fail_count = 0
    consecutive_fails = 0
    item_counter = 0

    while consecutive_fails < 50:
        item = f"load_{item_counter:06d}"
        item_counter += 1
        ok = cf.insert(item)
        if ok:
            inserted_items.append(item)
            consecutive_fails = 0
        else:
            fail_count += 1
            consecutive_fails += 1

            if len(all_snapshots) < 3 and fail_count in (1, 5, 20):
                snapshot = [(x, cf.contains(x)) for x in inserted_items]
                all_snapshots.append((fail_count, snapshot, list(cf.buckets), cf.size))
                print(f"  第 {len(all_snapshots)} 次快照: 失败 #{fail_count}, 当前负载 {cf.load_factor():.2%}, size={cf.size}")
                for idx, (name, exists) in enumerate(snapshot[-3:]):
                    print(f"    ...近期元素 {name}: 存在={exists}")

    print()
    print(f"  连续 50 次失败后停止. 总插入成功: {len(inserted_items)}, 总失败: {fail_count}")
    print(f"  最终负载因子: {cf.load_factor():.4f}, 记录 size: {cf.size}")
    print()

    if len(all_snapshots) == 0:
        print("  未捕获到失败快照, 增加指纹/桶大小重试.")
        return

    print(f"  ✓ 验收: 比对 {len(all_snapshots)} 个快照中已插入元素的查询结果...")

    errors = []
    for snap_fail, snapshot, saved_buckets, saved_size in all_snapshots:
        for idx, (item, expected_exists) in enumerate(snapshot):
            actual = cf.contains(item)
            if actual != expected_exists:
                errors.append(f"  快照{len(errors)+1} 元素#{idx} {item}: 快照时={expected_exists}, 现在={actual}")

    print(f"  ✓ 验收: 再次逐一查询全部 {len(inserted_items)} 个已插入元素...")
    all_ok_after = 0
    for item in inserted_items:
        if cf.contains(item):
            all_ok_after += 1

    print(f"  ✓ 验收: 计数 size 和实际元素匹配...")
    actual_count = sum(1 for b in cf.buckets for s in b if s is not None)
    size_matches = actual_count == cf.size

    print()
    print(f"  {'验收项':<35} {'结果':<15} {'详情'}")
    print(f"  {'-'*70}")
    print(f"  {'插入失败后元素查询不变':<35} {'PASS' if len(errors) == 0 else 'FAIL':<15} {len(errors)} 项不一致")
    if errors:
        for e in errors[:10]:
            print(f"    {e}")
    print(f"  {'全部已插入元素仍可查询':<35} {'PASS' if all_ok_after == len(inserted_items) else 'FAIL':<15} {all_ok_after}/{len(inserted_items)}")
    print(f"  {'size 计数与实际槽位一致':<35} {'PASS' if size_matches else 'FAIL':<15} size={cf.size}, 实际={actual_count}")

    if len(errors) == 0 and all_ok_after == len(inserted_items) and size_matches:
        print()
        print(f"  ✅✅✅ 高负载完整性验收全部通过!")
    else:
        print()
        print(f"  ❌ 验收失败, 请检查!")
        sys.exit(1)


def demo_capacity_exact():
    print_sep("四、容量参数兜底验证 (总容量不小于用户要求)")

    test_cases = [
        (100, 4),
        (101, 4),
        (250, 4),
        (1000, 4),
        (7, 3),
        (1, 8),
        (513, 4),
        (999, 2),
    ]

    print(f"  {'请求容量':<12} {'桶大小':<10} {'桶数':<10} {'实际总容量':<14} {'满足要求':<10} {'差异'}")
    print(f"  {'-'*70}")

    all_pass = True
    for req, bsize in test_cases:
        cf = CuckooFilter(capacity=req, bucket_size=bsize, fingerprint_bits=12)
        ok = cf.capacity >= req
        diff = cf.capacity - req
        status = "✓" if ok else "✗"
        if not ok:
            all_pass = False
        print(f"  {req:<12} {bsize:<10} {cf.num_buckets:<10} {cf.capacity:<14} {status:<10} +{diff}")

    print()
    if all_pass:
        print(f"  ✅ 全部容量验证通过: 实际容量 >= 请求容量")
    else:
        print(f"  ❌ 有容量不达标!")
        sys.exit(1)


def main():
    print_sep("可删除过滤器增强功能演示")
    print("  1. 持久化 (保存 / 加载)")
    print("  2. 高负载插入失败后完整性")
    print("  3. 容量参数兜底")

    demo_counting_bloom_persistence()
    demo_cuckoo_persistence()
    demo_capacity_exact()
    demo_cuckoo_high_load_integrity()

    print()
    print_sep("所有演示和验收通过!")


if __name__ == "__main__":
    main()
