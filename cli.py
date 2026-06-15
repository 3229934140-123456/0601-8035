import argparse
import random
import string
import sys
import time
from typing import List, Tuple

from counting_bloom_filter import CountingBloomFilter
from cuckoo_filter import CuckooFilter


def generate_random_string(length: int = 12) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_items(n: int, prefix: str = "") -> List[str]:
    items = set()
    while len(items) < n:
        items.add(prefix + generate_random_string(12))
    return list(items)


def print_section(title: str) -> None:
    width = 72
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def run_benchmark(args):
    random.seed(args.seed)

    num_items = args.items
    target_fp = args.fp_rate
    counter_bits = args.counter_bits
    fp_bits = args.fp_bits
    bucket_size = args.bucket_size
    max_kicks = args.max_kicks
    num_test = args.test_queries
    delete_ratio = args.delete_ratio

    print_section("可删除过滤器对比工具")
    print(f"  元素数量        : {num_items}")
    print(f"  目标误判率      : {target_fp:.6f}")
    print(f"  CBF计数器位数   : {counter_bits}")
    print(f"  Cuckoo指纹位数  : {fp_bits}")
    print(f"  Cuckoo桶大小    : {bucket_size}")
    print(f"  Cuckoo最大踢出  : {max_kicks}")
    print(f"  随机种子        : {args.seed}")
    print(f"  查询测试数量    : {num_test}")
    print(f"  删除比例        : {delete_ratio:.2%}")

    cbf = CountingBloomFilter(
        expected_items=num_items,
        false_positive_rate=target_fp,
        counter_bits=counter_bits
    )

    cf = CuckooFilter(
        capacity=num_items,
        fingerprint_bits=fp_bits,
        bucket_size=bucket_size,
        max_kicks=max_kicks
    )

    print_section("配置参数")
    print(f"  {'参数':<25} {'计数布隆 (CBF)':<22} {'Cuckoo (CF)':<22}")
    print("  " + "-" * 69)
    print(f"  {'计数器/桶总数':<25} {cbf.num_counters:<22} {cf.num_buckets:<22}")
    print(f"  {'哈希/桶内槽':<25} {cbf.num_hashes:<22} {cf.bucket_size:<22}")
    print(f"  {'总容量(元素)':<25} {'N/A':<22} {cf.capacity:<22}")
    print(f"  {'用户请求容量':<25} {'N/A':<22} {cf._requested_capacity:<22}")
    if cf.capacity != cf._requested_capacity:
        print(f"  {'容量适配差异':<25} {'N/A':<22} +{cf.capacity - cf._requested_capacity:<22}")

    items = generate_items(num_items, prefix="ins_")
    test_items = generate_items(num_test, prefix="qry_")

    print_section("插入阶段")
    insert_start = time.perf_counter()
    for item in items:
        cbf.insert(item)
    cbf_insert_time = time.perf_counter() - insert_start

    insert_start = time.perf_counter()
    cf_insert_failures = 0
    for item in items:
        if not cf.insert(item):
            cf_insert_failures += 1
    cf_insert_time = time.perf_counter() - insert_start

    print(f"  {'指标':<25} {'计数布隆 (CBF)':<22} {'Cuckoo (CF)':<22}")
    print("  " + "-" * 69)
    print(f"  {'插入用时(秒)':<25} {cbf_insert_time:<22.4f} {cf_insert_time:<22.4f}")
    print(f"  {'插入失败次数':<25} {'0 (永不失败)':<22} {cf_insert_failures:<22}")
    if cf_insert_failures > 0:
        actual_inserted = sum(1 for it in items if cf.contains(it))
        print(f"  {'实际成功插入':<25} {num_items:<22} {actual_inserted:<22}")
    print(f"  {'CBF计数器溢出率':<25} {cbf.overflow_risk():<22.6f} {'N/A':<22}")
    print(f"  {'CF负载因子':<25} {'N/A':<22} {cf.load_factor():<22.4f}")

    print_section("查询阶段")
    query_start = time.perf_counter()
    cbf_true_pos = sum(1 for it in items if cbf.contains(it))
    cbf_fp_items = [t for t in test_items if t not in set(items)]
    cbf_false_pos = sum(1 for t in cbf_fp_items if cbf.contains(t))
    cbf_query_time = time.perf_counter() - query_start

    query_start = time.perf_counter()
    cf_true_pos = sum(1 for it in items if cf.contains(it))
    cf_false_pos = sum(1 for t in cbf_fp_items if cf.contains(t))
    cf_query_time = time.perf_counter() - query_start

    cbf_fp_rate = cbf_false_pos / max(1, len(cbf_fp_items))
    cf_fp_rate = cf_false_pos / max(1, len(cbf_fp_items))

    print(f"  {'指标':<25} {'计数布隆 (CBF)':<22} {'Cuckoo (CF)':<22}")
    print("  " + "-" * 69)
    print(f"  {'查询用时(秒)':<25} {cbf_query_time:<22.4f} {cf_query_time:<22.4f}")
    print(f"  {'真阳性/已插入':<25} {f'{cbf_true_pos}/{num_items}':<22} {f'{cf_true_pos}/{num_items}':<22}")
    print(f"  {'假阳性次数':<25} {cbf_false_pos:<22} {cf_false_pos:<22}")
    print(f"  {'实际误判率':<25} {cbf_fp_rate:<22.6f} {cf_fp_rate:<22.6f}")
    print(f"  {'与目标误判率比值':<25} {f'{cbf_fp_rate/target_fp:.2f}x':<22} {f'{cf_fp_rate/target_fp:.2f}x':<22}")

    print_section("删除阶段")
    num_delete = int(num_items * delete_ratio)
    to_delete = items[:num_delete]
    remaining = items[num_delete:]

    del_start = time.perf_counter()
    cbf_delete_ok = 0
    for it in to_delete:
        if cbf.delete(it):
            cbf_delete_ok += 1
    cbf_delete_time = time.perf_counter() - del_start

    del_start = time.perf_counter()
    cf_delete_ok = 0
    for it in to_delete:
        if cf.delete(it):
            cf_delete_ok += 1
    cf_delete_time = time.perf_counter() - del_start

    cbf_remaining_ok = sum(1 for it in remaining if cbf.contains(it))
    cf_remaining_ok = sum(1 for it in remaining if cf.contains(it))

    cbf_leftover = sum(1 for it in to_delete if cbf.contains(it))
    cf_leftover = sum(1 for it in to_delete if cf.contains(it))

    cbf_residual_rate = cbf_leftover / max(1, num_delete)
    cf_residual_rate = cf_leftover / max(1, num_delete)

    print(f"  删除数量                    : {num_delete} / {num_items} ({delete_ratio:.0%})")
    print()
    print(f"  {'指标':<25} {'计数布隆 (CBF)':<22} {'Cuckoo (CF)':<22}")
    print("  " + "-" * 69)
    print(f"  {'删除用时(秒)':<25} {cbf_delete_time:<22.4f} {cf_delete_time:<22.4f}")
    print(f"  {'删除成功次数':<25} {cbf_delete_ok:<22} {cf_delete_ok:<22}")
    print(f"  {'剩余元素仍存在':<25} {f'{cbf_remaining_ok}/{len(remaining)}':<22} {f'{cf_remaining_ok}/{len(remaining)}':<22}")
    print(f"  {'删除后残留数':<25} {cbf_leftover:<22} {cf_leftover:<22}")
    print(f"  {'删除残留率':<25} {cbf_residual_rate:<22.6f} {cf_residual_rate:<22.6f}")
    if cbf_leftover > 0:
        print(f"  {'CBF残留原因':<25} {'溢出/哈希共享':<22} {'N/A':<22}")

    print_section("内存占用")
    cbf_mem = cbf.memory_usage_bytes()
    cf_mem = cf.memory_usage_bytes()

    def fmt_mem(b: int) -> str:
        if b >= 1024 * 1024:
            return f"{b / 1024 / 1024:.2f} MB"
        if b >= 1024:
            return f"{b / 1024:.2f} KB"
        return f"{b} B"

    print(f"  {'指标':<25} {'计数布隆 (CBF)':<22} {'Cuckoo (CF)':<22}")
    print("  " + "-" * 69)
    print(f"  {'内存总字节':<25} {cbf_mem:<22} {cf_mem:<22}")
    print(f"  {'内存可读':<25} {fmt_mem(cbf_mem):<22} {fmt_mem(cf_mem):<22}")
    if num_items > 0:
        print(f"  {'每元素比特':<25} {cbf_mem * 8 / num_items:<22.2f} {cf_mem * 8 / num_items:<22.2f}")
    print(f"  {'CBF vs CF 空间比':<25} {f'{cbf_mem/max(1,cf_mem):.2f}x':<22} {'1.00x':<22}")

    print_section("汇总结论")
    space_win = "Cuckoo" if cf_mem < cbf_mem else "计数布隆"
    fp_win = "Cuckoo" if cf_fp_rate < cbf_fp_rate else "计数布隆"
    residual_win = "Cuckoo" if cf_residual_rate < cbf_residual_rate else "计数布隆"
    speed_insert = "计数布隆" if cbf_insert_time < cf_insert_time else "Cuckoo"

    print(f"  空间效率胜出  : {space_win} ({min(cbf_mem, cf_mem)} 字节)")
    print(f"  误判率更低    : {fp_win}")
    print(f"  删除最干净    : {residual_win}")
    print(f"  插入速度更快  : {speed_insert}")
    if cf_insert_failures > 0:
        print(f"  ⚠️  Cuckoo 插入失败: {cf_insert_failures} 次, 请考虑增加容量或指纹位数")
    if cbf.overflow_risk() > 0.01:
        print(f"  ⚠️  计数布隆溢出率较高: {cbf.overflow_risk():.2%}, 建议增加计数器位数")

    return {
        "cbf_mem": cbf_mem, "cf_mem": cf_mem,
        "cbf_fp": cbf_fp_rate, "cf_fp": cf_fp_rate,
        "cbf_residual": cbf_residual_rate, "cf_residual": cf_residual_rate,
        "cf_insert_failures": cf_insert_failures,
        "cbf_overflow": cbf.overflow_risk()
    }


def main():
    parser = argparse.ArgumentParser(
        description="可删除布隆过滤器对比工具 (计数布隆 vs Cuckoo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py                                      # 默认参数运行
  python cli.py --items 10000 --fp-rate 0.001        # 1万元素, 0.1%误判率
  python cli.py --counter-bits 8 --fp-bits 16        # 8位计数器, 16位指纹
  python cli.py --items 5000 --bucket-size 8 --max-kicks 1000
  python cli.py --items 2000 --delete-ratio 0.5      # 删除50%元素后测试残留
        """
    )

    parser.add_argument("--items", type=int, default=5000,
                        help="插入的元素数量 (默认: 5000)")
    parser.add_argument("--fp-rate", type=float, default=0.01,
                        help="目标误判率, 0到1之间 (默认: 0.01 = 1%%)")
    parser.add_argument("--counter-bits", type=int, default=4,
                        help="计数布隆过滤器每个计数器位数 (默认: 4)")
    parser.add_argument("--fp-bits", type=int, default=12,
                        help="Cuckoo过滤器指纹位数 (默认: 12)")
    parser.add_argument("--bucket-size", type=int, default=4,
                        help="Cuckoo过滤器桶大小, 每桶槽位数 (默认: 4)")
    parser.add_argument("--max-kicks", type=int, default=500,
                        help="Cuckoo插入时最大踢出次数 (默认: 500)")
    parser.add_argument("--seed", type=int, default=42,
                        help="随机种子 (默认: 42)")
    parser.add_argument("--test-queries", type=int, default=5000,
                        help="用于误判率测试的查询数量 (默认: 5000)")
    parser.add_argument("--delete-ratio", type=float, default=0.3,
                        help="删除阶段删除的元素比例 0到1 (默认: 0.3 = 30%%)")

    args = parser.parse_args()

    try:
        run_benchmark(args)
    except ValueError as e:
        print(f"参数错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断。", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
