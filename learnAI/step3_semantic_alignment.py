import json
import sys
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os

# 可选：使用镜像加速下载
# os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

SIMILARITY_THRESHOLD = 0.85
EMBEDDING_CACHE_FILE = CACHE_DIR / "embedding_cache.json"
BATCH_SIZE = 500

LOCAL_SYNONYMS = {
    "K8s": "Kubernetes", "k8s": "Kubernetes", "K8S": "Kubernetes",
    "Go语言": "Golang", "GO语言": "Golang", "go": "Golang", "GOLANG": "Golang",
    "Python3": "Python", "Node.js": "NodeJS", "nodejs": "NodeJS",
    "Vue.js": "Vue", "React.js": "React",
    "PostgreSQL": "Postgres", "postgresql": "Postgres",
}


class SemanticAligner:

    def __init__(self):
        self.entities = {
            'skills': set(),
            'knowledge': set(),
            'domains': set(),
            'cert_names': set()
        }
        self.embedding_cache = {}
        self.load_embedding_cache()

        print("\n📦 加载本地Embedding模型...")
        print("   (首次运行需要下载模型，约120MB，请耐心等待)")
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ 模型加载完成")

    def load_embedding_cache(self):
        if EMBEDDING_CACHE_FILE.exists():
            with open(EMBEDDING_CACHE_FILE, 'r', encoding='utf-8') as f:
                self.embedding_cache = json.load(f)
            print(f"📦 加载缓存: {len(self.embedding_cache)} 个向量")

    def save_embedding_cache(self):
        with open(EMBEDDING_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.embedding_cache, f, ensure_ascii=False, indent=2)

    def load_entities_from_step2(self):
        entity_file = OUTPUT_DIR / "extracted_entities.json"

        if not entity_file.exists():
            print(f"❌ 未找到: {entity_file}")
            print("请先运行: python step2_extract_entities.py")
            sys.exit(1)

        with open(entity_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for category in ['skills', 'knowledge', 'domains', 'cert_names']:
            self.entities[category] = set(data['entities'][category])

        print(f"📂 加载实体: 技能{len(self.entities['skills'])}个, "
              f"知识点{len(self.entities['knowledge'])}个, "
              f"领域{len(self.entities['domains'])}个, "
              f"证书{len(self.entities['cert_names'])}个")

    def apply_local_synonyms(self) -> Dict[str, str]:
        print("\n📖 应用本地同义词字典...")

        replacements = {}
        all_entities = set()
        for entities_set in self.entities.values():
            all_entities.update(entities_set)

        for entity in tqdm(all_entities, desc="  匹配同义词", unit="个"):
            if entity in LOCAL_SYNONYMS:
                replacements[entity] = LOCAL_SYNONYMS[entity]

        for category in self.entities:
            cleaned = set()
            for entity in self.entities[category]:
                cleaned.add(LOCAL_SYNONYMS.get(entity, entity))
            self.entities[category] = cleaned

        print(f"  ✅ 替换了 {len(replacements)} 个同义词")
        return replacements

    def compute_embeddings_batch(self, entities_list: List[str]):
        uncached = [e for e in entities_list if e not in self.embedding_cache]

        if not uncached:
            print(f"\n✅ 所有向量已缓存 ({len(entities_list)}个)")
            return

        print(f"\n🔄 实体向量化: 计算 {len(uncached)} 个向量...")

        with tqdm(total=len(uncached), desc="  向量化进度", unit="个") as pbar:
            for i in range(0, len(uncached), BATCH_SIZE):
                batch = uncached[i:i + BATCH_SIZE]
                embeddings = self.model.encode(batch)

                for entity, embedding in zip(batch, embeddings):
                    self.embedding_cache[entity] = embedding.tolist()

                pbar.update(len(batch))

                if (i // BATCH_SIZE) % 5 == 0:
                    self.save_embedding_cache()

        self.save_embedding_cache()
        print(f"💾 缓存已保存: {len(self.embedding_cache)} 个向量")

    def find_semantic_groups(self, entities_list: List[str]) -> List[Set[str]]:
        print(f"\n🔍 查找语义相似的实体组...")

        groups = []
        processed = set()

        for i, entity1 in enumerate(tqdm(entities_list, desc="  相似度计算", unit="个")):
            if entity1 in processed:
                continue

            if entity1 not in self.embedding_cache:
                processed.add(entity1)
                continue

            group = {entity1}
            vec1 = np.array(self.embedding_cache[entity1])

            for entity2 in entities_list[i + 1:]:
                if entity2 in processed or entity2 not in self.embedding_cache:
                    continue

                vec2 = np.array(self.embedding_cache[entity2])
                similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

                if similarity >= SIMILARITY_THRESHOLD:
                    group.add(entity2)
                    processed.add(entity2)

            processed.add(entity1)
            if len(group) > 1:
                groups.append(group)

        print(f"  ✅ 找到 {len(groups)} 个语义相似组")
        return groups

    def merge_semantic_groups(self, groups: List[Set[str]]) -> Dict[str, str]:
        print(f"\n🔗 合并语义相似的实体...")

        mapping = {}

        for group in tqdm(groups, desc="  合并进度", unit="组"):
            sorted_group = sorted(group, key=len, reverse=True)
            canonical = sorted_group[0]

            for entity in group:
                if entity != canonical:
                    mapping[entity] = canonical

        for category in self.entities:
            cleaned = set()
            for entity in self.entities[category]:
                cleaned.add(mapping.get(entity, entity))
            self.entities[category] = cleaned

        print(f"  ✅ 合并了 {len(mapping)} 个实体")
        return mapping

    def align_all(self) -> Dict:
        print("\n" + "=" * 60)
        print("🔍 第三步：语义对齐（本地Embedding）")
        print("=" * 60)

        self.load_entities_from_step2()

        local_mapping = self.apply_local_synonyms()

        all_entities = set()
        for entities_set in self.entities.values():
            all_entities.update(entities_set)

        entities_list = sorted(all_entities)
        print(f"\n📊 待处理实体总数: {len(entities_list)}")

        self.compute_embeddings_batch(entities_list)

        groups = self.find_semantic_groups(entities_list)

        semantic_mapping = self.merge_semantic_groups(groups)

        return {
            'local_mapping': local_mapping,
            'semantic_mapping': semantic_mapping,
            'total_groups': len(groups)
        }

    def print_final_stats(self):
        print("\n" + "=" * 60)
        print("📊 语义对齐后统计")
        print("=" * 60)

        for category in ['skills', 'knowledge', 'domains', 'cert_names']:
            name = {'skills': '技能', 'knowledge': '知识点',
                    'domains': '领域', 'cert_names': '证书名称'}[category]
            count = len(self.entities[category])
            print(f"  {name}: {count} 个")

    def save_aligned_entities(self):
        output_file = OUTPUT_DIR / "aligned_entities.json"

        result = {
            'entities': {k: sorted(list(v)) for k, v in self.entities.items()}
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n💾 对齐后的实体已保存至: {output_file}")


def main():
    print("=" * 60)
    print("🚀 知识图谱构建 - 第三步：语义对齐（本地方案）")
    print("=" * 60)

    aligner = SemanticAligner()
    result = aligner.align_all()

    aligner.print_final_stats()
    aligner.save_aligned_entities()

    print(f"\n✅ 第三步完成！")
    print(f"   本地同义词替换: {len(result['local_mapping'])} 个")
    print(f"   语义相似合并: {len(result['semantic_mapping'])} 个")
    print(f"   语义相似组: {result['total_groups']} 组")
    print("👉 可以运行第四步: python step4_build_neo4j.py")


if __name__ == "__main__":
    main()
