import requests
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor


def single_tts_request(request_id):
    """单次TTS请求"""
    url = "http://127.0.0.1:11996/tts_url"
    data = {
        "text": f"还是会想你，还是想登你。请求{request_id}",
        "audio_paths": [
            "./wavs/[纳西妲]好吧，我的想法是..wav",
        ]
    }

    start_time = time.time()
    try:
        response = requests.post(url, json=data)
        end_time = time.time()

        # 保存音频文件
        with open(f"output_{request_id}.wav", "wb") as f:
            f.write(response.content)

        return {
            'request_id': request_id,
            'duration': end_time - start_time,
            'status_code': response.status_code,
            'success': True
        }
    except Exception as e:
        end_time = time.time()
        return {
            'request_id': request_id,
            'duration': end_time - start_time,
            'error': str(e),
            'success': False
        }


def parallel_test(concurrent_count):
    """并行测试函数"""
    print(f"\n=== 并行数: {concurrent_count} ===")

    start_time = time.time()

    # 使用ThreadPoolExecutor进行并行请求
    with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
        # 提交任务
        futures = [executor.submit(single_tts_request, i) for i in range(concurrent_count)]

        # 等待所有任务完成并获取结果
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    end_time = time.time()

    # 统计结果
    total_time = end_time - start_time
    successful_requests = [r for r in results if r['success']]
    failed_requests = [r for r in results if not r['success']]

    if successful_requests:
        individual_times = [r['duration'] for r in successful_requests]
        avg_individual_time = sum(individual_times) / len(individual_times)
        max_individual_time = max(individual_times)
        min_individual_time = min(individual_times)
    else:
        avg_individual_time = max_individual_time = min_individual_time = 0

    # 打印结果
    print(f"总耗时: {total_time:.2f}s")
    print(f"成功请求数: {len(successful_requests)}/{concurrent_count}")
    print(f"失败请求数: {len(failed_requests)}")
    print(f"平均单次耗时: {avg_individual_time:.2f}s")
    print(f"最长单次耗时: {max_individual_time:.2f}s")
    print(f"最短单次耗时: {min_individual_time:.2f}s")

    if failed_requests:
        print(f"失败请求详情:")
        for req in failed_requests:
            print(f"  请求{req['request_id']}: {req.get('error', 'Unknown error')}")

    return {
        'concurrent_count': concurrent_count,
        'total_time': total_time,
        'avg_individual_time': avg_individual_time,
        'successful_count': len(successful_requests),
        'failed_count': len(failed_requests)
    }


def main():
    """主函数"""
    print("TTS服务并行请求测试开始...")

    concurrent_levels = [2, 3, 4, 5]
    all_results = []

    for i, concurrent_count in enumerate(concurrent_levels):
        # 执行测试
        result = parallel_test(concurrent_count)
        all_results.append(result)

        # 测试间隔（最后一次测试后不需要等待）
        if i < len(concurrent_levels) - 1:
            print(f"\n等待2秒后进行下一轮测试...")
            time.sleep(2)

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    print(f"{'并行数':<8} {'总耗时(s)':<12} {'平均耗时(s)':<12} {'成功数':<8} {'失败数':<8}")
    print("-" * 50)

    for result in all_results:
        print(f"{result['concurrent_count']:<8} "
              f"{result['total_time']:<12.2f} "
              f"{result['avg_individual_time']:<12.2f} "
              f"{result['successful_count']:<8} "
              f"{result['failed_count']:<8}")


if __name__ == "__main__":
    main()
