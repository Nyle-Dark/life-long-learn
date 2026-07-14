import json
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

BASE_DIR = Path(__file__).parent
RAW_DATA_BASE = BASE_DIR / "raw_data"
PATH_CERT_JSON = RAW_DATA_BASE / "证书json"
PATH_COURSE_JSON = RAW_DATA_BASE / "课程大纲json"
PATH_JOB_JSON = RAW_DATA_BASE / "职业数据json"
OUTPUT_DIR = BASE_DIR / "output"
ALIGNED_ENTITIES_PATH = OUTPUT_DIR / "aligned_entities.json"


def load_entity_mapping():
    print("📂 加载语义对齐后的实体...")

    if not ALIGNED_ENTITIES_PATH.exists():
        print(f"  ⚠️ 未找到文件: {ALIGNED_ENTITIES_PATH}")
        print("  将使用原始名称（不做标准化）")
        return {}

    with open(ALIGNED_ENTITIES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    name_mapping = {}

    if isinstance(data, dict):
        if "entities" in data:
            entities_dict = data["entities"]
        else:
            entities_dict = data

        for entity_type, entities in entities_dict.items():
            if isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict):
                        standard_name = entity.get("name", "")
                        if not standard_name:
                            continue
                        name_mapping[standard_name] = standard_name
                        for alias in entity.get("aliases", []):
                            name_mapping[alias] = standard_name
                        original = entity.get("original_name", "")
                        if original:
                            name_mapping[original] = standard_name
                    elif isinstance(entity, str):
                        name_mapping[entity] = entity

    elif isinstance(data, list):
        for entity in data:
            if isinstance(entity, dict):
                standard_name = entity.get("name", "")
                if standard_name:
                    name_mapping[standard_name] = standard_name

    print(f"  ✅ 加载 {len(name_mapping)} 个实体名映射")
    return name_mapping


def normalize_name(name, mapping):
    if not name:
        return None
    name = str(name).strip()
    if not mapping:
        return name
    return mapping.get(name, name)


def load_json_files(directory, file_desc="文件"):
    all_data = []

    if not directory.exists():
        print(f"  ⚠️ 目录不存在: {directory}")
        return all_data

    json_files = list(directory.glob("*.json"))
    if not json_files:
        print(f"  ⚠️ 目录下无JSON文件: {directory}")
        return all_data

    print(f"  📁 {directory.name}: 找到 {len(json_files)} 个JSON文件")

    for json_file in tqdm(json_files, desc=f"  加载{file_desc}"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                has_list = False
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        if isinstance(value[0], dict):
                            all_data.extend(value)
                            has_list = True
                            break

                if not has_list:
                    all_data.append(data)
        except Exception as e:
            print(f"  ❌ 加载失败 {json_file.name}: {e}")

    print(f"  ✅ 共加载 {len(all_data)} 条记录")
    return all_data


def extract_job_relations(jobs_data, mapping):
    print("\n📊 提取岗位关系...")
    relations = []
    stats = defaultdict(int)

    for job in tqdm(jobs_data, desc="处理岗位"):
        job_name = job.get("岗位名称", "")
        job_id = job.get("岗位ID", "")

        if not job_name:
            continue

        job_name_normalized = normalize_name(job_name, mapping)
        if not job_name_normalized:
            continue

        skills = job.get("核心硬技能 (Hard_Skills)", [])
        if not isinstance(skills, list):
            skills = []
        for skill in skills:
            skill_normalized = normalize_name(skill, mapping)
            if skill_normalized:
                relations.append({
                    "source": job_name_normalized,
                    "target": skill_normalized,
                    "type": "REQUIRE",
                    "source_type": "Job",
                    "target_type": "Skill",
                    "job_id": job_id,
                    "city": job.get("城市", ""),
                    "education": job.get("门槛要求", {}).get("学历", ""),
                    "experience": job.get("门槛要求", {}).get("经验", ""),
                    "original_source": job_name,
                    "original_target": skill,
                })
                stats["REQUIRE"] += 1

        domains = job.get("宽泛领域 (Domains)", [])
        if not isinstance(domains, list):
            domains = []
        for domain in domains:
            domain_normalized = normalize_name(domain, mapping)
            if domain_normalized:
                relations.append({
                    "source": job_name_normalized,
                    "target": domain_normalized,
                    "type": "BELONG_TO",
                    "source_type": "Job",
                    "target_type": "Domain",
                    "job_id": job_id,
                    "original_source": job_name,
                    "original_target": domain,
                })
                stats["BELONG_TO"] += 1

    print(f"  ✅ 提取岗位关系: {len(relations)} 条")
    for rel_type, count in stats.items():
        print(f"     {rel_type}: {count} 条")

    return relations


def extract_course_relations(courses_data, mapping):
    print("\n📊 提取课程关系...")
    relations = []
    stats = defaultdict(int)

    for course in tqdm(courses_data, desc="处理课程"):
        course_name = course.get("课程名称合集", "")

        if not course_name:
            continue

        course_name_normalized = normalize_name(course_name, mapping)
        if not course_name_normalized:
            continue

        skills = course.get("技能点实体 (Skill)", [])
        if not isinstance(skills, list):
            skills = []
        for skill in skills:
            skill_normalized = normalize_name(skill, mapping)
            if skill_normalized:
                relations.append({
                    "source": course_name_normalized,
                    "target": skill_normalized,
                    "type": "TEACH",
                    "source_type": "Course",
                    "target_type": "Skill",
                    "module": course.get("任务模块合集", ""),
                    "original_source": course_name,
                    "original_target": skill,
                })
                stats["TEACH_SKILL"] += 1

        knowledge_points = course.get("知识点实体 (Knowledge)", [])
        if not isinstance(knowledge_points, list):
            knowledge_points = []
        for kp in knowledge_points:
            kp_normalized = normalize_name(kp, mapping)
            if kp_normalized:
                relations.append({
                    "source": course_name_normalized,
                    "target": kp_normalized,
                    "type": "TEACH",
                    "source_type": "Course",
                    "target_type": "Knowledge",
                    "module": course.get("任务模块合集", ""),
                    "original_source": course_name,
                    "original_target": kp,
                })
                stats["TEACH_KNOWLEDGE"] += 1

        certs = course.get("关联证书 (Certification)", [])
        if not isinstance(certs, list):
            certs = []
        for cert in certs:
            cert_normalized = normalize_name(cert, mapping)
            if cert_normalized:
                relations.append({
                    "source": course_name_normalized,
                    "target": cert_normalized,
                    "type": "RELATED_TO",
                    "source_type": "Course",
                    "target_type": "Cert",
                    "original_source": course_name,
                    "original_target": cert,
                })
                stats["RELATED_TO"] += 1

    print(f"  ✅ 提取课程关系: {len(relations)} 条")
    for rel_type, count in stats.items():
        print(f"     {rel_type}: {count} 条")

    return relations


def extract_cert_relations(certs_data, mapping):
    print("\n📊 提取证书关系...")
    relations = []
    stats = defaultdict(int)

    for cert in tqdm(certs_data, desc="处理证书"):
        cert_name = cert.get("证书/竞赛名称", "")

        if not cert_name:
            continue

        cert_name_normalized = normalize_name(cert_name, mapping)
        if not cert_name_normalized:
            continue

        knowledge_points = cert.get("考核知识点 (Exam_Knowledge_Points)", [])
        if not isinstance(knowledge_points, list):
            knowledge_points = []
        for kp in knowledge_points:
            kp_normalized = normalize_name(kp, mapping)
            if kp_normalized:
                relations.append({
                    "source": cert_name_normalized,
                    "target": kp_normalized,
                    "type": "EXAMINE",
                    "source_type": "Cert",
                    "target_type": "Knowledge",
                    "level": cert.get("认证级别", ""),
                    "institution": cert.get("发证/主办机构", ""),
                    "original_source": cert_name,
                    "original_target": kp,
                })
                stats["EXAMINE"] += 1

        jobs = cert.get("关联支撑岗位 (Target_Jobs)", [])
        if not isinstance(jobs, list):
            jobs = []
        for job in jobs:
            job_normalized = normalize_name(job, mapping)
            if job_normalized:
                relations.append({
                    "source": cert_name_normalized,
                    "target": job_normalized,
                    "type": "SUPPORT",
                    "source_type": "Cert",
                    "target_type": "Job",
                    "original_source": cert_name,
                    "original_target": job,
                })
                stats["SUPPORT"] += 1

    print(f"  ✅ 提取证书关系: {len(relations)} 条")
    for rel_type, count in stats.items():
        print(f"     {rel_type}: {count} 条")

    return relations


def deduplicate_relations(relations):
    print(f"\n🔄 去重前: {len(relations)} 条关系")

    seen = set()
    unique_relations = []

    for rel in relations:
        key = (rel["source"], rel["target"], rel["type"])
        if key not in seen:
            seen.add(key)
            unique_relations.append(rel)

    duplicates = len(relations) - len(unique_relations)
    print(f"  ✅ 去重后: {len(unique_relations)} 条关系 (移除 {duplicates} 条重复)")

    return unique_relations


def calculate_node_degrees(relations):
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for rel in relations:
        out_degree[rel["source"]] += 1
        in_degree[rel["target"]] += 1

    all_nodes = set(list(out_degree.keys()) + list(in_degree.keys()))

    print("\n📊 Top 10 关系最多的源节点:")
    top_sources = sorted(out_degree.items(), key=lambda x: x[1], reverse=True)[:10]
    for node, degree in top_sources:
        print(f"  {node[:50]}: {degree} 条出边")

    print("\n📊 Top 10 被关联最多的目标节点:")
    top_targets = sorted(in_degree.items(), key=lambda x: x[1], reverse=True)[:10]
    for node, degree in top_targets:
        print(f"  {node[:50]}: {degree} 条入边")

    return {
        "total_nodes_in_graph": len(all_nodes),
        "avg_out_degree": sum(out_degree.values()) / len(out_degree) if out_degree else 0,
        "avg_in_degree": sum(in_degree.values()) / len(in_degree) if in_degree else 0,
    }


def main():
    print("=" * 60)
    print("🔗 第3.5步：提取实体关系")
    print("=" * 60)

    mapping = load_entity_mapping()

    print("\n📂 检查数据目录:")
    dirs = {
        "岗位数据": PATH_JOB_JSON,
        "课程数据": PATH_COURSE_JSON,
        "证书数据": PATH_CERT_JSON,
    }

    for name, path in dirs.items():
        if path.exists():
            json_count = len(list(path.glob("*.json")))
            print(f"  ✅ {name}: {path} ({json_count} 个JSON文件)")
        else:
            print(f"  ❌ {name}: {path} (目录不存在)")

    all_relations = []

    if PATH_JOB_JSON.exists():
        jobs_data = load_json_files(PATH_JOB_JSON, "岗位文件")
        if jobs_data:
            all_relations.extend(extract_job_relations(jobs_data, mapping))

    if PATH_COURSE_JSON.exists():
        courses_data = load_json_files(PATH_COURSE_JSON, "课程文件")
        if courses_data:
            all_relations.extend(extract_course_relations(courses_data, mapping))

    if PATH_CERT_JSON.exists():
        certs_data = load_json_files(PATH_CERT_JSON, "证书文件")
        if certs_data:
            all_relations.extend(extract_cert_relations(certs_data, mapping))

    if not all_relations:
        print("\n❌ 未提取到任何关系！请检查数据格式和字段名。")
        return

    all_relations = deduplicate_relations(all_relations)
    graph_stats = calculate_node_degrees(all_relations)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "relations.json"

    rel_type_counts = defaultdict(int)
    for r in all_relations:
        rel_type_counts[r["type"]] += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total_relations": len(all_relations),
            "relations": all_relations,
            "statistics": {
                "relation_types": {k: v for k, v in sorted(rel_type_counts.items())},
                "source_types": list(set(r["source_type"] for r in all_relations)),
                "target_types": list(set(r["target_type"] for r in all_relations)),
                "graph_stats": graph_stats,
            }
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 关系数据已保存至: {output_path}")

    print("\n" + "=" * 60)
    print("📊 关系提取完成统计")
    print("=" * 60)
    print(f"  总关系数: {len(all_relations)} 条")
    print(f"  图谱节点数: {graph_stats['total_nodes_in_graph']} 个")

    print("\n  关系类型分布:")
    for rel_type, count in sorted(rel_type_counts.items()):
        bar = "█" * min(count // max(1, len(all_relations) // 50), 50)
        print(f"    {rel_type:20s}: {count:6d} 条 {bar}")

    print("\n✅ 第3.5步完成！")
    print("👉 现在可以运行第四步: python step4_build_neo4j.py")


if __name__ == "__main__":
    main()
