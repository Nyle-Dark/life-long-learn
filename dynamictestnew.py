from DrissionPage import ChromiumPage
import csv
import time
import random
from datetime import datetime
import os
import json
import tempfile          # 新增：用于创建独立临时目录
from dateutil.relativedelta import relativedelta
import subprocess


def convert_time_string(time_str):
    """转换BOSS直聘的时间描述为实际日期"""
    today = datetime.now()

    if time_str == "今天":
        return today.strftime("%Y-%m-%d")
    elif time_str == "昨天":
        return (today - relativedelta(days=1)).strftime("%Y-%m-%d")
    elif "天前" in time_str:
        days_ago = int(time_str.replace("天前", ""))
        return (today - relativedelta(days=days_ago)).strftime("%Y-%m-%d")
    elif "月" in time_str and "日" in time_str:
        month, day = time_str.split("月")
        day = day.replace("日", "")
        return f"{today.year}-{month.zfill(2)}-{day.zfill(2)}"
    else:
        return time_str


def load_existing_job_ids(folder_path):
    history_file = os.path.join(folder_path, "collected_job_ids.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_job_ids(folder_path, job_ids):
    history_file = os.path.join(folder_path, "collected_job_ids.json")
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(list(job_ids), f, ensure_ascii=False)


def crawl_boss_zhipin(city_code="101010100"):
    TARGET_COUNT = 150
    MAX_RETRIES = 5
    MAX_PAGES = 20

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    folder_path = os.path.join(base_dir, "NetworkEngineer")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"已创建文件夹: {folder_path}")

    existing_job_ids = load_existing_job_ids(folder_path)
    print(f"已加载 {len(existing_job_ids)} 个历史职位ID")

    csv_filename = os.path.join(folder_path, f'NetworkEngineer_jobs_{timestamp}.csv')
    seen_job_ids = set()

    with open(csv_filename, mode='w', encoding='utf-8-sig', newline='') as f:
        csv_fieldnames = [
            '职位ID', '岗位名称', '公司名称', '公司规模', '公司领域',
            '学历要求', '经验要求', '关键技能', '薪资范围', '城市',
            '发布时间', '爬取时间'
        ]
        csv_writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        csv_writer.writeheader()

        # ====== 修复冲突关键：独立用户数据目录 ======
        # 每个进程创建唯一的临时目录，彻底隔离浏览器实例
        user_data_dir = tempfile.mkdtemp(prefix=f"boss_network_{os.getpid()}_")
        dp = ChromiumPage()

        target_url = f'https://www.zhipin.com/web/geek/jobs?query=网络工程师&city={city_code}'
        print(f"开始爬取，城市编码: {city_code}")

        dp.get(target_url)
        time.sleep(random.uniform(2, 3))

        dp.listen.start('joblist')
        total_jobs = 0
        page = 1
        retry_count = 0
        new_job_count = 0

        while total_jobs < TARGET_COUNT and page <= MAX_PAGES:
            print(f"正在采集第 {page} 页 (已获取 {total_jobs}/{TARGET_COUNT}, 新增 {new_job_count})")

            resp = dp.listen.wait(timeout=15)
            if not resp:
                if retry_count < MAX_RETRIES:
                    print(f"未获取到数据，重试中 ({retry_count + 1}/{MAX_RETRIES})")
                    dp.scroll.to_bottom()
                    time.sleep(random.uniform(2, 3))
                    retry_count += 1
                    continue
                else:
                    print("连续获取失败，停止爬取")
                    break

            retry_count = 0

            try:
                json_data = resp.response.body
                job_list = json_data['zpData'].get('jobList', [])
                if not job_list:
                    print("未获取到职位数据，可能遇到限制")
                    break

                for job in job_list:
                    if total_jobs >= TARGET_COUNT:
                        break
                    job_id = job.get('encryptJobId')
                    if not job_id:
                        continue
                    if job_id in seen_job_ids or job_id in existing_job_ids:
                        continue
                    seen_job_ids.add(job_id)

                    publish_time_str = job.get('timeState', '')
                    publish_date = convert_time_string(publish_time_str)

                    job_info = {
                        '职位ID': job_id,
                        '岗位名称': job.get('jobName', ''),
                        '公司名称': job.get('brandName', ''),
                        '公司规模': job.get('brandScaleName', ''),
                        '公司领域': job.get('brandIndustry', ''),
                        '学历要求': job.get('jobDegree', ''),
                        '经验要求': job.get('jobExperience', ''),
                        '关键技能': ', '.join(job.get('skills', [])),
                        '薪资范围': job.get('salaryDesc', ''),
                        '城市': job.get('cityName', ''),
                        '发布时间': publish_date,
                        '爬取时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    csv_writer.writerow(job_info)
                    total_jobs += 1
                    new_job_count += 1
                    print(f"新增职位: {job_info['公司名称']} - {job_info['岗位名称']}")

                if total_jobs >= TARGET_COUNT:
                    print(f"已达到目标数量 {TARGET_COUNT}")
                    break

                print("滚动到底部加载下一页...")
                dp.scroll.to_bottom()
                wait_time = random.uniform(2.0, 4.0)
                time.sleep(wait_time)
                dp.listen.stop()
                dp.listen.start('joblist')
                page += 1

            except Exception as e:
                print(f"处理第 {page} 页数据时出错: {str(e)}")
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    continue
                else:
                    break

        try:
            dp.quit()
            # 自动清理临时用户数据目录（可选，建议保留以免遗留垃圾）
            # import shutil
            # shutil.rmtree(user_data_dir, ignore_errors=True)
        except:
            pass

        if seen_job_ids:
            existing_job_ids.update(seen_job_ids)
            save_job_ids(folder_path, existing_job_ids)
            print(f"已更新历史职位ID集合，新增 {len(seen_job_ids)} 个ID")

        print(f"爬取完成! 共获取 {total_jobs} 个职位，其中新增 {new_job_count} 个职位")
        print(f"结果已保存至: {csv_filename}")
        return csv_filename


if __name__ == '__main__':
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        print("正在安装 dateutil 库...")
        subprocess.check_call(["pip", "install", "python-dateutil"])
        from dateutil.relativedelta import relativedelta

    city_codes = [
        "101010100",  # 北京
        "101020100",  # 上海
        "101280600",  # 深圳
        "101280100",  # 广州
        "101210100",  # 杭州
        "101270100",  # 成都
        "101190100",  # 南京
        "101200100",  # 武汉
        "101190400",  # 苏州
        "101190200",  # 无锡
        "101040100",  # 重庆
        "101220100",  # 合肥
        "101260100",  # 贵阳
        "101080100",  # 呼和浩特

    ]

    total_runs_per_city = 30
    total_cities = len(city_codes)

    for city_idx, city_code in enumerate(city_codes):
        print(f"\n{'=' * 60}")
        print(f"开始处理城市 {city_idx + 1}/{total_cities} (编码: {city_code})")
        print(f"{'=' * 60}\n")

        for run in range(total_runs_per_city):
            print(f"\n{'=' * 40}")
            print(f"城市 {city_code} - 第 {run + 1}/{total_runs_per_city} 次爬取")
            print(f"{'=' * 40}\n")

            try:
                result_file = crawl_boss_zhipin(city_code=city_code)
                print(f"完成! 文件: {result_file}")
            except Exception as e:
                print(f"爬取失败: {str(e)}")

            if run < total_runs_per_city - 1:
                wait_minutes = random.randint(0, 1)
                time.sleep(wait_minutes * 60)

        if city_idx < total_cities - 1:
            wait_between_cities = 3
            time.sleep(wait_between_cities * 60)

    print("\n所有爬取任务已完成!")