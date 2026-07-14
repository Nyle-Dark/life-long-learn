"""
配置文件 - 统一管理所有路径和参数
"""
from pathlib import Path

# ============ 路径配置 ============
# 自动定位到当前代码所在的项目根目录
BASE_DIR = Path(__file__).parent

# 原始数据目录
RAW_DATA_BASE = BASE_DIR / "raw_data"
PATH_CERT_JSON = RAW_DATA_BASE / "证书json"
PATH_COURSE_JSON = RAW_DATA_BASE / "课程大纲json"
PATH_JOB_JSON = RAW_DATA_BASE / "职业数据json"

# 缓存和输出目录（自动创建）
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 具体文件路径
EMBEDDING_CACHE_FILE = CACHE_DIR / "embedding_cache.json"
ENTITIES_STATS_FILE = OUTPUT_DIR / "entities_stats.json"
SEMANTIC_ALIGNMENTS_FILE = OUTPUT_DIR / "semantic_alignments.json"
GRAPH_EXPORT_FILE = OUTPUT_DIR / "graph_export.json"

# ============ DeepSeek API配置 ============
# 请在这里填写你的API密钥
DEEPSEEK_API_KEY = "sk-your-deepseek-api-key-here"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_EMBEDDING_MODEL = "deepseek-embedding"

# ============ Neo4j配置 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-password-here"

# ============ 处理参数 ============
SIMILARITY_THRESHOLD = 0.85  # 语义相似度阈值
BATCH_SIZE = 10  # API批处理大小

# ============ 本地同义词字典 ============
SYNONYM_DICT = {
    # 技术同义词
    'K8s': 'Kubernetes',
    'k8s': 'Kubernetes',
    'kube': 'Kubernetes',
    '容器编排': 'Kubernetes',

    # 编程语言变体
    'golang': 'Golang',
    'Go语言': 'Golang',
    'Go': 'Golang',

    # 工具同义词
    'docker容器': 'Docker',
    'docker引擎': 'Docker',

    # 概念同义词
    'linux系统': 'Linux',
    'linux操作系统': 'Linux',
    '云原生技术': '云原生',
    'cloud native': '云原生',

    # 证书名称映射
    'HCCDA': '华为HCCDA认证证书',
    'HCCDA证书': '华为HCCDA认证证书',
}

print(f"✅ 配置文件加载完成")
print(f"   项目根目录: {BASE_DIR}")
print(f"   原始数据目录: {RAW_DATA_BASE}")
print(f"   缓存目录: {CACHE_DIR}")
print(f"   输出目录: {OUTPUT_DIR}")
