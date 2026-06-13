import pandas as pd
import json

def csv_to_json(input_csv, output_json, encoding='utf-8-sig'):
    """
    将CSV文件直接转换为JSON文件（扁平结构，每行一个对象）
    :param input_csv:  输入CSV路径
    :param output_json: 输出JSON路径
    :param encoding:    CSV读取编码（中文常用 utf-8-sig）
    """
    # 读取CSV
    df = pd.read_csv(input_csv, encoding=encoding)
    # 转换为JSON字符串（orient='records' 得到 [{col:val}, ...] 格式）
    json_str = df.to_json(orient='records', force_ascii=False, indent=2)
    # 写入文件
    with open(output_json, 'w', encoding='utf-8') as f:
        f.write(json_str)
    print(f"✅ 转换完成，共 {len(df)} 行，JSON 已保存至：{output_json}")

if __name__ == "__main__":
    # ----- 请按实际路径修改 -----
    INPUT_CSV = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingEngineerSorting\related_jobs.csv"
    OUTPUT_JSON = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingEngineerSorting\CloudComputingEngineerEND.json"

    csv_to_json(INPUT_CSV, OUTPUT_JSON)
