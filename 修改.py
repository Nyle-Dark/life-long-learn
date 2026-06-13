
import pandas as pd
import numpy as np

# ============ 请根据实际情况修改这两个路径 ============
INPUT_FILE = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitectSorting\output.csv"
OUTPUT_FILE = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitectSorting\output_cleaned.csv"


def drop_empty_skills(input_path, output_path):
    # 读取CSV，默认逗号分隔，分隔不对可改sep参数
    df = pd.read_csv(input_path)

    # 记录原始行数
    original_count = len(df)
    print(f"原始数据行数: {original_count}")

    # 将经验要求字段中的NaN空值替换为"经验不限"，兼容原生NaN和字符串空
    if "经验要求" in df.columns:
        # 先把原生空值直接替换，再处理字符串形式的空
        df["经验要求"] = df["经验要求"].replace([np.nan, "", "nan", "NaN", "null", "None"], "经验不限")
        print("已将经验要求分段中的所有空/NaN值修改为'经验不限'")
    else:
        print("警告：未找到'经验要求'列，跳过空值替换步骤")

    if "关键技能" in df.columns:
        # 处理关键技能列：兼容原生NaN，标记缺失值后删除空行
        df["关键技能"] = df["关键技能"].astype(str).str.strip()
        df["关键技能"] = df["关键技能"].replace(["", "nan", "NaN", "null", "None"], pd.NA)
        # 只保留有关键技能的行
        df = df.dropna(subset=["关键技能"]).copy()

        removed_count = original_count - len(df)
        print(f"已删除{removed_count}行无关键技能的数据")
        print(f"剩余保留有效行数: {len(df)}")
    else:
        print("警告：CSV文件中没有找到'关键技能'这一列，请检查表头列名是否正确。")
        return

    # 保存结果
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"处理完成，结果已保存至: {output_path}")


if __name__ == "__main__":
    drop_empty_skills(INPUT_FILE, OUTPUT_FILE)

