"""
工具函数 - 通用功能
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict


def setup_logging(step_name: str):
    """设置日志"""
    log_file = Path(__file__).parent / "output" / f"{step_name}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(step_name)


def save_json(data: Any, filepath: Path):
    """保存JSON文件"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"   💾 已保存: {filepath}")


def load_json(filepath: Path) -> Any:
    """加载JSON文件"""
    if not filepath.exists():
        print(f"   ⚠️ 文件不存在: {filepath}")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(step_num: int, title: str):
    """打印步骤标题"""
    print(f"\n{'─' * 40}")
    print(f"  📌 步骤 {step_num}: {title}")
    print(f"{'─' * 40}")
