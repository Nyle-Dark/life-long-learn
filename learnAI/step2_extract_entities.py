import json
import re
import sys
from pathlib import Path
from typing import Dict, Set, List
from collections import defaultdict

BASE_DIR = Path(__file__).parent
RAW_DATA_BASE = BASE_DIR / "raw_data"
PATH_CERT_JSON = RAW_DATA_BASE / "证书json"
PATH_COURSE_JSON = RAW_DATA_BASE / "课程大纲json"
PATH_JOB_JSON = RAW_DATA_BASE / "职业数据json"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class EntityExtractor:

    def __init__(self):
        self.jobs_data = []
        self.courses_data = []
        self.certs_data = []

        self.entities = {
            'skills': set(),
            'knowledge': set(),
            'domains': set(),
            'cert_names': set()
        }

        self.original_counts = {
            'skills': 0,
            'knowledge': 0,
            'domains': 0,
            'cert_names': 0
        }

    def load_data(self):
        print("\n📂 加载数据文件...")

        def load_json_dir(directory: Path) -> List[Dict]:
            data = []
            if directory.exists():
                for json_file in directory.glob("*.json"):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        if isinstance(content, list):
                            data.extend(content)
                        else:
                            data.append(content)
            return data

        self.certs_data = load_json_dir(PATH_CERT_JSON)
        self.courses_data = load_json_dir(PATH_COURSE_JSON)
        self.jobs_data = load_json_dir(PATH_JOB_JSON)

        print(f"  证书: {len(self.certs_data)} 条")
        print(f"  课程: {len(self.courses_data)} 条")
        print(f"  岗位: {len(self.jobs_data)} 条")

    def extract_from_jobs(self):
        print("\n💼 从岗位数据提取实体...")

        for job in self.jobs_data:
            job_name = job.get('岗位名称', 'Unknown')

            if '核心硬技能 (Hard_Skills)' in job:
                skills = job['核心硬技能 (Hard_Skills)']
                self.original_counts['skills'] += len(skills)
                for skill in skills:
                    cleaned = self.clean_entity_name(skill)
                    if cleaned:
                        self.entities['skills'].add(cleaned)
                print(f"  [{job_name}]: 提取 {len(skills)} 个技能")

            if '宽泛领域 (Domains)' in job:
                domains = job['宽泛领域 (Domains)']
                self.original_counts['domains'] += len(domains)
                for domain in domains:
                    cleaned = self.clean_entity_name(domain)
                    if cleaned:
                        self.entities['domains'].add(cleaned)
                print(f"  [{job_name}]: 提取 {len(domains)} 个领域")

    def extract_from_courses(self):
        print("\n📚 从课程数据提取实体...")

        for course in self.courses_data:
            course_name = course.get('课程名称合集', 'Unknown')

            if '技能点实体 (Skill)' in course:
                skills = course['技能点实体 (Skill)']
                self.original_counts['skills'] += len(skills)
                for skill in skills:
                    cleaned = self.clean_entity_name(skill)
                    if cleaned:
                        self.entities['skills'].add(cleaned)
                print(f"  [{course_name}]: 提取 {len(skills)} 个技能点")

            if '知识点实体 (Knowledge)' in course:
                knowledge = course['知识点实体 (Knowledge)']
                self.original_counts['knowledge'] += len(knowledge)
                for k in knowledge:
                    cleaned = self.clean_entity_name(k)
                    if cleaned:
                        self.entities['knowledge'].add(cleaned)
                print(f"  [{course_name}]: 提取 {len(knowledge)} 个知识点")

            if '关联证书 (Certification)' in course:
                certs = course['关联证书 (Certification)']
                self.original_counts['cert_names'] += len(certs)
                for cert in certs:
                    cleaned = self.clean_entity_name(cert)
                    if cleaned:
                        self.entities['cert_names'].add(cleaned)
                print(f"  [{course_name}]: 提取 {len(certs)} 个证书")

    def extract_from_certs(self):
        print("\n📜 从证书数据提取实体...")

        for cert in self.certs_data:
            cert_name = cert.get('证书/竞赛名称', 'Unknown')

            if '考核知识点 (Exam_Knowledge_Points)' in cert:
                knowledge = cert['考核知识点 (Exam_Knowledge_Points)']
                self.original_counts['knowledge'] += len(knowledge)
                for k in knowledge:
                    cleaned = self.clean_entity_name(k)
                    if cleaned:
                        self.entities['knowledge'].add(cleaned)
                print(f"  [{cert_name}]: 提取 {len(knowledge)} 个考核知识点")

            if '证书/竞赛名称' in cert:
                self.original_counts['cert_names'] += 1
                cleaned = self.clean_entity_name(cert['证书/竞赛名称'])
                if cleaned:
                    self.entities['cert_names'].add(cleaned)

    def clean_entity_name(self, name: str) -> str:
        if not name or not isinstance(name, str):
            return ""
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', name)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def extract_all(self) -> Dict[str, Set[str]]:
        print("\n" + "=" * 60)
        print("🔍 开始提取实体")
        print("=" * 60)

        self.load_data()
        self.extract_from_jobs()
        self.extract_from_courses()
        self.extract_from_certs()

        return self.entities

    def print_statistics(self):
        print("\n" + "=" * 60)
        print("📊 实体提取统计")
        print("=" * 60)

        stats = {}
        category_names = {
            'skills': '技能',
            'knowledge': '知识点',
            'domains': '领域',
            'cert_names': '证书名称'
        }

        for category in ['skills', 'knowledge', 'domains', 'cert_names']:
            original = self.original_counts[category]
            unique = len(self.entities[category])
            dedup_rate = (1 - unique / original) * 100 if original > 0 else 0

            print(f"\n{category_names[category]}实体:")
            print(f"  原始数量（含重复）: {original}")
            print(f"  去重后数量: {unique}")
            print(f"  去重率: {dedup_rate:.1f}%")

            stats[category] = {
                'original': original,
                'unique': unique,
                'dedup_rate': f"{dedup_rate:.1f}%"
            }

        return stats

    def preview_entities(self):
        print("\n" + "=" * 60)
        print("👀 实体预览")
        print("=" * 60)

        if self.entities['skills']:
            skills_list = sorted(self.entities['skills'])
            print(f"\n技能实体 ({len(skills_list)}个):")
            for skill in skills_list[:10]:
                print(f"  - {skill}")
            if len(skills_list) > 10:
                print(f"  ... 还有 {len(skills_list) - 10} 个")

        if self.entities['knowledge']:
            knowledge_list = sorted(self.entities['knowledge'])
            print(f"\n知识点实体 ({len(knowledge_list)}个):")
            for k in knowledge_list[:10]:
                print(f"  - {k}")
            if len(knowledge_list) > 10:
                print(f"  ... 还有 {len(knowledge_list) - 10} 个")

        if self.entities['domains']:
            domains_list = sorted(self.entities['domains'])
            print(f"\n领域实体 ({len(domains_list)}个):")
            for domain in domains_list:
                print(f"  - {domain}")

        if self.entities['cert_names']:
            certs_list = sorted(self.entities['cert_names'])
            print(f"\n证书名称实体 ({len(certs_list)}个):")
            for cert in certs_list:
                print(f"  - {cert}")

    def save_results(self):
        output_file = OUTPUT_DIR / "extracted_entities.json"

        result = {
            'entities': {k: sorted(list(v)) for k, v in self.entities.items()},
            'statistics': {
                k: {
                    'original': self.original_counts[k],
                    'unique': len(self.entities[k]),
                    'dedup_rate': f"{(1 - len(self.entities[k]) / self.original_counts[k]) * 100:.1f}%" if
                    self.original_counts[k] > 0 else "0%"
                }
                for k in ['skills', 'knowledge', 'domains', 'cert_names']
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n💾 实体数据已保存至: {output_file}")


def main():
    print("=" * 60)
    print("🚀 知识图谱构建 - 第二步：实体提取与去重")
    print("=" * 60)

    extractor = EntityExtractor()
    entities = extractor.extract_all()

    if not any(entities.values()):
        print("\n❌ 没有提取到任何实体")
        sys.exit(1)

    extractor.print_statistics()
    extractor.preview_entities()
    extractor.save_results()

    print("\n✅ 第二步完成！实体提取成功")
    print(f"   技能: {len(entities['skills'])} 个")
    print(f"   知识点: {len(entities['knowledge'])} 个")
    print(f"   领域: {len(entities['domains'])} 个")
    print(f"   证书: {len(entities['cert_names'])} 个")
    print("👉 可以运行第三步: python step3_semantic_alignment.py")


if __name__ == "__main__":
    main()
