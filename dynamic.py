from DrissionPage import ChromiumPage
from pprint import pprint
import csv
import time
import random
from datetime import datetime


def crawl_boss_zhipin():
    # 当前时间戳（用于文件名）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_filename = f'boss_cloud_jobs_{timestamp}.csv'

    # 1. 初始化CSV文件
    with open(csv_filename, mode='w', encoding='utf-8-sig', newline='') as f:
        csv_fieldnames = [
            '岗位名称',
            '公司名称',
            '公司规模',
            '公司领域',
            '学历要求',
            '经验要求',
            '关键技能',
            '职位描述',
            '薪资范围',
            '城市',
            '区域',
            '商圈',
            '发布时间',
            '爬取时间'
        ]
        csv_writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        csv_writer.writeheader()

        # 2. 初始化浏览器对象
        dp = ChromiumPage()

        # 监听正确的接口 - 恢复原始监听目标
        dp.listen.start('joblist')

        # 访问BOSS直聘云计算工程师岗位页面
        target_url = 'https://www.zhipin.com/web/geek/jobs?query=云计算工程师'
        dp.get(target_url)
        time.sleep(3)

        # 3. 循环翻页，爬取数据
        page = 1
        max_pages = 10
        total_jobs = 0

        while page <= max_pages:
            print(f'========== 正在采集第 {page} 页数据 ==========')

            try:
                # 等待接口数据返回 - 恢复原始逻辑
                resp = dp.listen.wait(timeout=30)
                if not resp:
                    print(f"第 {page} 页未获取到数据，可能已达最后一页")
                    break

                # 解析JSON数据 - 恢复原始数据结构
                json_data = resp.response.body

                # 检查是否包含jobList - 恢复原始键名
                if 'zpData' not in json_data or 'jobList' not in json_data['zpData']:
                    print(f"第 {page} 页未找到职位数据，可能遇到反爬限制")
                    break

                job_list = json_data['zpData']['jobList']
                print(f"本页获取到 {len(job_list)} 个职位")

                # 4. 处理每个职位数据
                for job in job_list:
                    # 处理职位描述
                    job_desc = job.get('jobDesc', '')
                    if isinstance(job_desc, str):
                        job_desc = job_desc.replace('<br/>', '\n').replace('&nbsp;', ' ')

                    # 构建职位数据 - 恢复原始字段名
                    job_info = {
                        '岗位名称': job.get('jobName', ''),
                        '公司名称': job.get('brandName', ''),
                        '公司规模': job.get('brandScaleName', ''),
                        '公司领域': job.get('brandIndustry', ''),
                        '学历要求': job.get('jobDegree', ''),
                        '经验要求': job.get('jobExperience', ''),
                        '关键技能': ', '.join(job.get('skills', [])),
                        '职位描述': job_desc,
                        '薪资范围': job.get('salaryDesc', ''),
                        '城市': job.get('cityName', ''),
                        '区域': job.get('areaDistrict', ''),
                        '商圈': job.get('businessDistrict', ''),
                        '发布时间': job.get('publishTime', ''),
                        '爬取时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    # 写入CSV
                    csv_writer.writerow(job_info)
                    total_jobs += 1

                    # 调试输出（每页第一个）
                    if job == job_list[0]:
                        pprint(job_info)

                # 5. 翻页操作 - 恢复原始翻页逻辑
                # 滚动到底部触发下一页加载
                print("滚动到底部加载下一页...")
                dp.scroll.to_bottom()

                # 随机等待时间（模拟人类操作）
                wait_time = random.uniform(2.5, 4.0)
                print(f"等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)

                # 更新页码
                page += 1

                # 检查是否有下一页
                next_page_indicator = dp.ele('css:.ui-page-next', timeout=5)
                if not next_page_indicator or 'disabled' in next_page_indicator.classes:
                    print("已到达最后一页，停止爬取")
                    break

            except Exception as e:
                print(f"处理第 {page} 页数据时出错: {str(e)}")
                # 尝试保存错误页截图
                dp.get_screenshot(f'error_page_{page}.png')
                break

        # 6. 爬取完成
        dp.quit()
        print(f'========== 爬取完成! 共获取 {total_jobs} 个职位 ==========')
        print(f'========== 结果已保存至: {csv_filename} ==========')


if __name__ == '__main__':
    crawl_boss_zhipin()
