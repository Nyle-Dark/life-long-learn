import json
from pathlib import Path
from py2neo import Graph, Node, Relationship
from tqdm import tqdm
from collections import defaultdict

NEO4J_CONFIG = {
    "uri": "bolt://localhost:7687",
    "username": "neo4j",
    "password": "neo4j111"
}

BASE_DIR = Path(__file__).parent
ALIGNED_ENTITIES_PATH = BASE_DIR / "output" / "aligned_entities.json"
RELATIONS_PATH = BASE_DIR / "output" / "relations.json"


def connect_neo4j(config):
    try:
        graph = Graph(config["uri"], auth=(config["username"], config["password"]))
        graph.run("MATCH (n) RETURN count(n) LIMIT 1")
        print(f"✅ 成功连接到Neo4j: {config['uri']}")
        return graph
    except Exception as e:
        print(f"❌ 连接Neo4j失败: {e}")
        print("\n请检查：")
        print("1. Neo4j是否已启动？")
        print("2. 用户名密码是否正确？")
        return None


def create_constraints(graph):
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Job) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Skill) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Knowledge) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Domain) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Cert) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Course) REQUIRE n.name IS UNIQUE",
    ]

    print("📋 创建约束和索引...")
    for c in constraints:
        try:
            graph.run(c)
        except Exception as e:
            pass
    print("  ✅ 完成")


def import_from_relations(graph, relations_path):
    with open(relations_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    relations = data.get("relations", [])
    print(f"📊 加载关系: {len(relations)} 条")

    type_to_label = {
        "Job": "Job",
        "Skill": "Skill",
        "Knowledge": "Knowledge",
        "Domain": "Domain",
        "Cert": "Cert",
        "Course": "Course",
    }

    tx = graph.begin()
    node_count = 0
    rel_count = 0
    batch_size = 1000

    print("\n🔄 导入节点和关系...")

    for i, rel in enumerate(tqdm(relations, desc="导入")):
        try:
            source = rel["source"]
            target = rel["target"]
            source_type = rel["source_type"]
            target_type = rel["target_type"]
            rel_type = rel["type"]

            source_label = type_to_label.get(source_type, "Entity")
            target_label = type_to_label.get(target_type, "Entity")

            source_props = {"name": source, "type": source_type}
            if source_type == "Job":
                source_props["job_id"] = rel.get("job_id", "")
                source_props["city"] = rel.get("city", "")
                source_props["education"] = rel.get("education", "")
                source_props["experience"] = rel.get("experience", "")
            elif source_type == "Cert":
                source_props["level"] = rel.get("level", "")
                source_props["institution"] = rel.get("institution", "")
            elif source_type == "Course":
                source_props["module"] = rel.get("module", "")

            target_props = {"name": target, "type": target_type}

            query = f"""
            MERGE (a:{source_label} {{name: $source_name}})
            SET a += $source_props
            MERGE (b:{target_label} {{name: $target_name}})
            SET b += $target_props
            MERGE (a)-[r:{rel_type}]->(b)
            SET r.source_type = $source_type
            SET r.target_type = $target_type
            """

            tx.run(query,
                   source_name=source,
                   target_name=target,
                   source_props=source_props,
                   target_props=target_props,
                   source_type=source_type,
                   target_type=target_type)

            node_count += 2
            rel_count += 1

            if i > 0 and i % batch_size == 0:
                graph.commit(tx)
                tx = graph.begin()

        except Exception as e:
            continue

    graph.commit(tx)
    print(f"\n  ✅ 导入完成: ~{node_count} 个节点, {rel_count} 条关系")
    return node_count, rel_count


def verify_import(graph):
    print("\n" + "=" * 60)
    print("📊 导入验证")
    print("=" * 60)

    queries = {
        "总节点数": "MATCH (n) RETURN count(n) as count",
        "岗位节点": "MATCH (n:Job) RETURN count(n) as count",
        "技能节点": "MATCH (n:Skill) RETURN count(n) as count",
        "知识点节点": "MATCH (n:Knowledge) RETURN count(n) as count",
        "领域节点": "MATCH (n:Domain) RETURN count(n) as count",
        "证书节点": "MATCH (n:Cert) RETURN count(n) as count",
        "课程节点": "MATCH (n:Course) RETURN count(n) as count",
        "关系总数": "MATCH ()-[r]->() RETURN count(r) as count",
    }

    for desc, query in queries.items():
        try:
            result = graph.run(query).data()
            count = result[0]['count'] if result else 0
            print(f"  {desc}: {count}")
        except:
            print(f"  {desc}: 查询失败")

    print("\n📋 关系类型统计:")
    try:
        rel_stats = graph.run("""
            MATCH ()-[r]->() 
            RETURN type(r) as rel_type, count(r) as count 
            ORDER BY count DESC
        """).data()

        for stat in rel_stats:
            print(f"  {stat['rel_type']}: {stat['count']} 条")
    except Exception as e:
        print(f"  查询失败: {e}")

    print("\n📋 样例数据:")
    try:
        samples = graph.run("""
            MATCH (n) 
            RETURN n.name as name, labels(n) as labels, n.type as type 
            LIMIT 5
        """).data()

        for s in samples:
            print(f"  [{', '.join(s['labels'])}] {s['name'][:50]} (类型: {s['type']})")
    except Exception as e:
        print(f"  查询失败: {e}")


def main():
    print("=" * 60)
    print("🏗️ 第四步：构建Neo4j知识图谱")
    print("=" * 60)

    graph = connect_neo4j(NEO4J_CONFIG)
    if not graph:
        return

    create_constraints(graph)

    print("\n⚠️ 是否清空现有数据？")
    choice = input("   输入 y 清空，其他任意键保留: ").strip().lower()
    if choice == 'y':
        print("  🗑️ 清空所有节点和关系...")
        graph.run("MATCH (n) DETACH DELETE n")
        print("  ✅ 已清空")

    node_count, rel_count = import_from_relations(graph, RELATIONS_PATH)

    verify_import(graph)

    print("\n" + "=" * 60)
    print("✅ 第四步完成！")
    print("=" * 60)
    print(f"\n📊 导入统计:")
    print(f"   节点: ~{node_count} 个")
    print(f"   关系: {rel_count} 条")
    print(f"\n🔗 访问Neo4j浏览器: http://localhost:7474")
    print(f"   用户名: {NEO4J_CONFIG['username']}")
    print(f"   密码: {NEO4J_CONFIG['password']}")
    print(f"\n💡 查询示例:")
    print(f"   MATCH (n) RETURN n LIMIT 25")
    print(f"   MATCH (n:Job)-[:REQUIRE]->(s:Skill) RETURN n, s LIMIT 50")
    print(f"   MATCH (c:Course)-[:TEACH]->(s:Skill) RETURN c, s LIMIT 50")
    print(f"   MATCH (c:Cert)-[:SUPPORT]->(j:Job) RETURN c, j LIMIT 50")


if __name__ == "__main__":
    main()
