import pandas as pd
import re
import json

# -------------------- 新增：关键词相关函数 --------------------
def is_related(row, keywords):
    """
    判断职位是否与关键词相关（检查岗位名称和关键技能）
    :param row: DataFrame的一行（Series）
    :param keywords: 关键词列表（不区分大小写）
    :return: True/False
    """
    # 将待检查字段转为小写字符串
    name = str(row.get("岗位名称", "")).lower()
    skills = str(row.get("关键技能", "")).lower()
    text = name + " " + skills
    # 遍历关键词，任意一个命中即返回True
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False

# -------------------- 原有函数（保持不变） --------------------
def split_skills(skill_str):
    skill_list = re.split(r'[、，,\s]+', str(skill_str))
    filtered = []
    for s in skill_list:
        s = s.strip()
        if not s:
            continue
        if '经验' in s or '专业' in s:
            continue
        filtered.append(s)
    hard_skills = []
    domains = []
    domain_keywords = ['网络', '数据库', '云计算', '信息安全', '通信', '计算机', '服务', '硬件', '软件', '政务']
    for skill in filtered:
        is_domain = False
        for kw in domain_keywords:
            if kw in skill:
                domains.append(skill)
                is_domain = True
                break
        if not is_domain:
            hard_skills.append(skill)
    hard_skills = list(set(hard_skills))
    domains = list(set(domains))
    return hard_skills, domains

def process_salary(salary_str):
    salary_str = str(salary_str).strip()
    nums = re.findall(r'(\d+)', salary_str)
    if len(nums) >= 2:
        lower = int(nums[0])
        upper = int(nums[1])
    else:
        lower = None
        upper = None
    return {
        "原始区间": salary_str,
        "薪资下限": lower,
        "薪资上限": upper
    }

# -------------------- 修改后的主处理函数 --------------------
def process_csv_with_filter(input_path, output_json, related_csv, excluded_csv, keywords=None):
    """
    读取CSV，按关键词分流，分别保存为CSV，并对相关部分生成JSON
    :param input_path:  原始CSV路径
    :param output_json: 最终JSON输出路径（只包含相关职位）
    :param related_csv: 相关职位CSV保存路径
    :param excluded_csv: 无关职位CSV保存路径
    :param keywords:     关键词列表，若为None则使用默认列表
    """
    if keywords is None:
        keywords = ["云计算", "云", "Cloud", "云平台", "云架构", "云运维", "云工程师"]

    df = pd.read_csv(input_path)

    # 1. 分流：相关行和无关行
    related_mask = df.apply(lambda row: is_related(row, keywords), axis=1)
    df_related = df[related_mask].copy()
    df_excluded = df[~related_mask].copy()

    # 2. 保存分流后的CSV文件
    df_related.to_csv(related_csv, index=False, encoding='utf-8-sig')
    df_excluded.to_csv(excluded_csv, index=False, encoding='utf-8-sig')
    print(f"相关职位数: {len(df_related)} -> 已保存到 {related_csv}")
    print(f"无关职位数: {len(df_excluded)} -> 已保存到 {excluded_csv}")

    # 3. 对相关职位进行原有JSON处理
    result = []
    for _, row in df_related.iterrows():
        job_item = {}
        job_item["岗位ID"] = str(row["职位ID"]).strip()
        job_item["岗位名称"] = str(row["岗位名称"]).strip()
        job_item["城市"] = str(row["城市"]).strip()
        edu = str(row["学历要求"]).strip()
        job_item["门槛要求"] = {
            "学历": edu if edu and edu != "nan" else "不限",
            "经验": str(row["经验要求"]).strip() if str(row["经验要求"]).strip() and str(row["经验要求"]).strip() != "nan" else "不限"
        }
        job_item["薪资特征"] = process_salary(row["薪资范围"])
        hard, domain = split_skills(row["关键技能"])
        job_item["核心硬技能 (Hard_Skills)"] = hard
        job_item["宽泛领域 (Domains)"] = domain
        result.append(job_item)

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"相关职位JSON已保存到 {output_json}")

if __name__ == "__main__":
    # ----- 请按实际情况修改以下路径 -----
    INPUT_CSV = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitectSorting\output_cleaned.csv" #原始路径
    RELATED_CSV = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitectSorting\related_jobs.csv"  #相关
    EXCLUDED_CSV = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitectSorting\excluded_jobs.csv" #无关

    # 如果需要自定义关键词，可传参
    # my_keywords = ["云计算", "AWS", "阿里云", "腾讯云"]
    process_csv_with_filter(INPUT_CSV, RELATED_CSV, EXCLUDED_CSV, None)

