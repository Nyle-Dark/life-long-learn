import pandas as pd

# ---------- 请修改为你的实际路径 ----------
input_file = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingEngineerSorting\output.csv"
output_file = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingEngineerSorting\CloudComputingEngineerLearnign.csv"

# ---------- 1. 读取CSV ----------
# 如果编码报错，把 'utf-8' 改为 'gbk' 或 'utf-8-sig'
df = pd.read_csv(input_file, encoding='utf-8')

# ---------- 2. 统一岗位名称 ----------
df['岗位名称'] = '云计算工程师'

# ---------- 3. 关键技能按字母排序 ----------
def sort_skills(skill_str):
    if pd.isna(skill_str) or str(skill_str).strip() == '':
        return skill_str
    skills = [s.strip() for s in str(skill_str).split(',') if s.strip()]
    sorted_skills = sorted(skills, key=lambda x: x.lower())
    return ', '.join(sorted_skills)

df['关键技能'] = df['关键技能'].apply(sort_skills)

# ---------- 4. 保存为CSV（utf-8-sig编码，Excel打开不乱码）----------
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"处理完成！CSV文件已保存至：{output_file}")

