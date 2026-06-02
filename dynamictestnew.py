from DrissionPage import ChromiumPage, ChromiumOptions #版本是V4
import csv
import time
import random
from datetime import datetime
import os
import json
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
    """加载历史爬取的职位ID集合"""
    history_file = os.path.join(folder_path, "collected_job_ids.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_job_ids(folder_path, job_ids):
    """保存爬取到的职位ID集合"""
    history_file = os.path.join(folder_path, "collected_job_ids.json")
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(list(job_ids), f, ensure_ascii=False)

def crawl_boss_zhipin(city_code="101010100"):
    """爬取单个城市的职位信息（DrissionPage V4 版本）"""
    # 配置参数
    TARGET_COUNT = 150
    MAX_RETRIES = 5
    MAX_PAGES = 20

    #修改处1，文件夹名称
    base_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(base_dir, "NetworkEngineer")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"已创建文件夹: {folder_path}")

    existing_job_ids = load_existing_job_ids(folder_path)
    print(f"已加载 {len(existing_job_ids)} 个历史职位ID")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    #修改处2，CSV文件命名
    csv_filename = os.path.join(folder_path, f'NetworkEngineer_jobs_{timestamp}.csv')
    seen_job_ids = set()

    with open(csv_filename, mode='w', encoding='utf-8-sig', newline='') as f:
        fieldnames = [
            '职位ID', '岗位名称', '公司名称', '公司规模', '公司领域',
            '学历要求', '经验要求', '关键技能', '薪资范围', '城市',
            '发布时间', '爬取时间'
        ]
        csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
        csv_writer.writeheader()

        # ========== 登录态持久化配置（DrissionPage V4） ==========
        user_data_dir = os.path.join(base_dir, "boss_login_profile")
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)

        # 清理可能残留的锁文件
        for lock_file in ['SingletonLock', 'SingletonCookie']:
            lock_path = os.path.join(user_data_dir, lock_file)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except:
                    pass

        # V4 正确写法：直接传入 ChromiumOptions 对象
        co = ChromiumOptions()
        co.set_user_data_path(user_data_dir)
        #！！！！！第一次运行，把这行代码注释掉，不然你来你登陆界面也看不到
        # 此代码作用为将页面极小化，这样可以去忙别的事情
        #不要使用无头代码，会BOSS直聘反爬虫
        co.set_argument('--window-position=-32000,-32000')
        #这个是端口，新的记住要尾数+1，有效避免一个页面，修改8个小时的就为了这一行
        co.set_local_port(9222)

        # 固定用户数据目录
        # V4 自动处理端口，无需额外设置
        page = ChromiumPage(co)                   # 关键修正：直接传对象，不要关键字参数
        # =========================================================

        #修改处3：网站地址，只改职业就行，城市代码后面都写了，不用管
        target_url = f'https://www.zhipin.com/web/geek/jobs?query=网络工程师&city={city_code}'
        print(f"开始爬取，城市编码: {city_code}")

        page.get(target_url)
        time.sleep(random.uniform(2, 3))

        page.listen.start('joblist')
        total_jobs = 0
        page_num = 1
        retry_count = 0
        new_job_count = 0

        while total_jobs < TARGET_COUNT and page_num <= MAX_PAGES:
            print(f"正在采集第 {page_num} 页 (已获取 {total_jobs}/{TARGET_COUNT}, 新增 {new_job_count})")
            resp = page.listen.wait(timeout=15)
            if not resp:
                if retry_count < MAX_RETRIES:
                    print(f"未获取到数据，重试中 ({retry_count + 1}/{MAX_RETRIES})")
                    page.scroll.to_bottom()
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

                    publish_date = convert_time_string(job.get('timeState', ''))
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
                page.scroll.to_bottom()
                time.sleep(random.uniform(2.0, 4.0))
                page.listen.stop()
                page.listen.start('joblist')
                page_num += 1

            except Exception as e:
                print(f"处理第 {page_num} 页数据时出错: {str(e)}")
                if retry_count < MAX_RETRIES:
                    retry_count += 1
                    continue
                else:
                    break

        try:
            page.quit()
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

    #这是14座城市，横着看，每一座都可以对应上，昨晚修改代码的时候，注释自己掉了
    city_codes = [
        "101010100", "101020100", "101280600", "101280100",
        "101210100", "101270100", "101190100", "101200100",
        "101190400", "101190200", "101040100", "101220100",
        "101260100", "101080100"
    ]

    #循环30次，有点多，但优先考虑数据的采集完整性，避免误差
    total_runs_per_city = 30   # 测试用，正式跑改为30
    total_cities = len(city_codes)

    for city_idx, city_code in enumerate(city_codes):
        print(f"\n{'='*60}")
        print(f"开始处理城市 {city_idx+1}/{total_cities} (编码: {city_code})")
        print(f"{'='*60}\n")

        for run in range(total_runs_per_city):
            print(f"\n{'='*40}")
            print(f"城市 {city_code} - 第 {run+1}/{total_runs_per_city} 次爬取")
            print(f"{'='*40}\n")
            try:
                result_file = crawl_boss_zhipin(city_code)
                print(f"完成! 文件: {result_file}")
            except Exception as e:
                print(f"爬取失败: {str(e)}")

            if run < total_runs_per_city - 1:
                wait = random.randint(2, 3) #每次循环结束，停顿2-3分钟
                print(f"等待 {wait} 分钟后继续...")
                time.sleep(wait * 60)

        if city_idx < total_cities - 1:
            #每切换一座城市，停顿5分钟
            wait = 5
            print(f"\n城市 {city_code} 完成，等待 {wait} 分钟后切换下一城市...")
            time.sleep(wait * 60)

    print("\n所有爬取任务已完成!")
