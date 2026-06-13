
import pandas as pd
import os
import glob
import chardet  # 自动检测编码，需要先安装：pip install chardet


folder_path = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitect"  # 根据你的实际路径调整
output_file = r"D:\PythonPRO\PycharmProjects\PythonProject\lifelonglearning\CloudComputingArchitectSorting\output.csv"
# --------------------------------------

# 获取所有CSV文件
csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
print(f"共发现 {len(csv_files)} 个CSV文件")

# 标记是否已写入表头
header_written = False
success_count = 0
fail_count = 0

def detect_encoding(file_path):
    """自动检测文件编码，返回最佳编码名称"""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)  # 只读前10000字节，提高速度
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        # 常见问题：chardet可能把UTF-8-BOM识别为UTF-8，不影响读取；若识别为ascii，实际可能是utf-8
        if encoding and 'ascii' in encoding.lower():
            return 'utf-8'
        return encoding if encoding else 'utf-8'

for i, file in enumerate(csv_files):
    try:
        # 先尝试UTF-8编码（爬虫输出的标准编码）
        for chunk in pd.read_csv(file, chunksize=10000, encoding='utf-8', low_memory=False):
            chunk.to_csv(output_file, mode='a', index=False, header=not header_written, encoding='utf-8-sig')
            header_written = True
        success_count += 1
    except (UnicodeDecodeError, UnicodeError):
        # UTF-8失败，尝试GBK
        try:
            for chunk in pd.read_csv(file, chunksize=10000, encoding='gbk', low_memory=False):
                chunk.to_csv(output_file, mode='a', index=False, header=not header_written, encoding='utf-8-sig')
                header_written = True
            success_count += 1
        except (UnicodeDecodeError, UnicodeError):
            # GBK也失败，自动检测编码
            try:
                detected_enc = detect_encoding(file)
                for chunk in pd.read_csv(file, chunksize=10000, encoding=detected_enc, low_memory=False):
                    chunk.to_csv(output_file, mode='a', index=False, header=not header_written, encoding='utf-8-sig')
                    header_written = True
                success_count += 1
            except Exception as e:
                print(f"文件 {file} 读取失败: {e}")
                fail_count += 1

    if (i + 1) % 50 == 0:
        print(f"已处理 {i+1}/{len(csv_files)} 个文件...")

print(f"合并完成！成功: {success_count}, 失败: {fail_count}")
print(f"输出文件: {output_file}")
