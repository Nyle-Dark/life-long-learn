from DrissionPage import ChromiumPage
import csv
import time
import random
from datetime import datetime
import os
import json
from dateutil.relativedelta import relativedelta
import subprocess

#此代码可删可不删，曾用于爬取发布时间，但毫无作用，也可作预留位
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
        # 格式如 "03月15日"
        month, day = time_str.split("月")
        day = day.replace("日", "")
        return f"{today.year}-{month.zfill(2)}-{day.zfill(2)}"
    else:
        return time_str  # 返回原始字符串

#历史ID的保存位置，可以让数据不重复，进行去重管理
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

# 配置的参数，一三 不用改，二 五次就不错，这个参数很完美
def crawl_boss_zhipin():
    # 配置参数
    TARGET_COUNT = 150  # 目标数据量
    MAX_RETRIES = 5  # 翻页失败重试次数
    MAX_PAGES = 20  # 最大翻页次数

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # 获取当前脚本所在目录作为项目根路径
    base_dir = os.path.dirname(os.path.abspath(__file__))

#之后换职业的时候记得改一个名字，要求英文名，不要带空格，数据会无法上传
    # 修改文件夹名称为CloudComputingEngineer
    folder_path = os.path.join(base_dir, "CloudComputingEngineer")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"已创建文件夹: {folder_path}")

    # 加载历史爬取的职位ID（在现有基础上增量更新）
    existing_job_ids = load_existing_job_ids(folder_path)
    print(f"已加载 {len(existing_job_ids)} 个历史职位ID")

#此处同上，名字后面可以加地区英文，方便管理
    # 修改文件名为CloudComputingEngineer
    csv_filename = os.path.join(folder_path, f'CloudComputingEngineer_jobs_{timestamp}.csv')

    # 本次运行的去重集合
    seen_job_ids = set()

    with open(csv_filename, mode='w', encoding='utf-8-sig', newline='') as f:
        # 字段列表
        csv_fieldnames = [
            '职位ID',
            '岗位名称',
            '公司名称',
            '公司规模',
            '公司领域',
            '学历要求',
            '经验要求',
            '关键技能',
            '薪资范围',
            '城市',
            '发布时间',
            '爬取时间'
        ]
        csv_writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        csv_writer.writeheader()

        # 浏览器初始化 - 使用原始代码的设置
        dp = ChromiumPage()

#能看到职位不，把职位改了，一定是要存在的职业，后面的编码是城市的编码，这样就可以固定区域
        # 设置真正的全国搜索URL
        target_url = 'https://www.zhipin.com/web/geek/jobs?query=云计算工程师&city=101080100'
        print("开始全国搜索")

        dp.get(target_url)
        time.sleep(random.uniform(2, 3))  # 初始加载等待

        # 设置监听 - 使用原始代码的设置
        dp.listen.start('joblist')
        total_jobs = 0
        page = 1
        retry_count = 0
        new_job_count = 0  # 新增职位计数器

        while total_jobs < TARGET_COUNT and page <= MAX_PAGES:
            print(f"正在采集第 {page} 页 (已获取 {total_jobs}/{TARGET_COUNT}, 新增 {new_job_count})")

            # 获取接口数据
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

            retry_count = 0  # 重置重试计数器

            try:
                # 使用原始代码的数据解析方式
                json_data = resp.response.body
                job_list = json_data['zpData'].get('jobList', [])

                if not job_list:
                    print("未获取到职位数据，可能遇到限制")
                    break

                # 处理职位数据
                for job in job_list:
                    if total_jobs >= TARGET_COUNT:
                        break

                    job_id = job.get('encryptJobId')
                    if not job_id:
                        continue

                    # 三重去重检查（基于历史ID集合）：
                    # 1. 本次运行已处理过
                    # 2. 历史数据中已存在
                    if job_id in seen_job_ids or job_id in existing_job_ids:
                        continue

                    seen_job_ids.add(job_id)

                    # 获取发布时间
                    publish_time_str = job.get('timeState', '')
                    publish_date = convert_time_string(publish_time_str)

                    # 构建职位数据
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

                # 目标达成检查
                if total_jobs >= TARGET_COUNT:
                    print(f"已达到目标数量 {TARGET_COUNT}")
                    break

                # 翻页操作
                print("滚动到底部加载下一页...")
                dp.scroll.to_bottom()

                # 智能等待
                wait_time = random.uniform(2.0, 4.0)
                time.sleep(wait_time)

                # 刷新监听 - 使用原始代码的设置
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

        # 关闭浏览器
        try:
            dp.quit()
            print("浏览器已关闭")
        except:
            pass

        # 更新历史职位ID集合（在现有基础上添加新ID）
        if seen_job_ids:
            existing_job_ids.update(seen_job_ids)
            save_job_ids(folder_path, existing_job_ids)
            print(f"已更新历史职位ID集合，新增 {len(seen_job_ids)} 个ID")

        print(f"爬取完成! 共获取 {total_jobs} 个职位，其中新增 {new_job_count} 个职位")
        print(f"结果已保存至: {csv_filename}")

        # 返回结果文件路径
        return csv_filename


if __name__ == '__main__':
    # 安装必要的依赖
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        print("正在安装 dateutil 库...")
        import subprocess

        subprocess.check_call(["pip", "install", "python-dateutil"])
        from dateutil.relativedelta import relativedelta

    # 连续运行10次（不做任何优化），如果想挂的时间长一点，就变大一些，现在的代码完全运行一次大概1h
    for i in range(30):
        print(f"\n{'=' * 50}")
        print(f"开始第 {i + 1}/30 次爬取任务")
        print(f"{'=' * 50}\n")

        try:
            result_file = crawl_boss_zhipin()
            print(f"第 {i + 1} 次爬取完成! 文件路径: {result_file}")
        except Exception as e:
            print(f"第 {i + 1} 次爬取失败: {str(e)}")

        # 如果不是最后一次，添加等待时间，2-3挺合理，太大等的心烦，太小运行会可能触发机制
        if i < 19:
            wait_minutes = random.randint(2, 3)  # 2-3分钟随机等待
            print(f"等待 {wait_minutes} 分钟后开始下次爬取...")
            time.sleep(wait_minutes * 60)  # 转换为秒

    print("\n所有30次爬取任务已完成!")
