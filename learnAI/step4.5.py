import json
from pathlib import Path
from py2neo import Graph, Node, Relationship
from tqdm import tqdm
from collections import defaultdict

# 🔧 根据你的 Neo4j Desktop 2 信息配置
NEO4J_CONFIG = {
    "uri": "bolt://localhost:7687",  # 使用 bolt 协议
    "username": "neo4j",
    "password": "lwj070306"  # 请确认你的密码（创建数据库时设置的）
}

BASE_DIR = Path(__file__).parent
ALIGNED_ENTITIES_PATH = BASE_DIR / "output" / "aligned_entities.json"
RELATIONS_PATH = BASE_DIR / "output" / "relations.json"


def connect_neo4j(config):
    try:
        graph = Graph(config["uri"], auth=(config["username"], config["password"]))
        # 测试连接
        result = graph.run("MATCH (n) RETURN count(n) LIMIT 1").data()
        print(f"✅ 成功连接到Neo4j: {config['uri']}")
        print(f"   📦 数据库: lifelonglearn")
        print(f"   🆔 ID: 285a6b3d")
        return graph
    except Exception as e:
        print(f"❌ 连接Neo4j失败: {e}")
        print("\n💡 请检查：")
        print("1. Neo4j Desktop 2 中 lifelonglearn 数据库是否显示绿色运行状态？")
        print("2. 密码是否正确？如果不确定，可以：")
        print("   - 在 Desktop 中点击数据库的 '...' → 'Terminal'")
        print("   - 输入: neo4j-admin dbms set-initial-password 你的新密码")
        return None


def create_constraints(graph):
    constraints = [
        "CREATE CONSTRAINT 岗位唯一约束 IF NOT EXISTS FOR (n:岗位) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT 技能唯一约束 IF NOT EXISTS FOR (n:技能) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT 知识点唯一约束 IF NOT EXISTS FOR (n:知识点) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT 领域唯一约束 IF NOT EXISTS FOR (n:领域) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT 证书唯一约束 IF NOT EXISTS FOR (n:证书) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT 课程唯一约束 IF NOT EXISTS FOR (n:课程) REQUIRE n.name IS UNIQUE",
    ]

    print("\n📋 创建约束和索引...")
    for c in constraints:
        try:
            graph.run(c)
            print(f"  ✅ {c.split('FOR')[0].replace('CREATE CONSTRAINT ', '')}")
        except Exception as e:
            print(f"  ⚠️ 约束可能已存在: {str(e)[:50]}")
    print("  ✅ 完成")


def import_from_relations(graph, relations_path):
    with open(relations_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    relations = data.get("relations", [])
    print(f"\n📊 加载关系数据: {len(relations)} 条")

    # 中文标签映射
    type_to_label = {
        "Job": "岗位",
        "Skill": "技能",
        "Knowledge": "知识点",
        "Domain": "领域",
        "Cert": "证书",
        "Course": "课程",
    }

    # 中文关系类型映射
    relation_type_map = {
        "REQUIRE": "需要",
        "TEACH": "教授",
        "BELONG_TO": "属于",
        "EXAMINE": "考察",
        "SUPPORT": "支持",
    }

    tx = graph.begin()
    node_count = 0
    rel_count = 0
    batch_size = 1000

    print("\n🔄 开始导入节点和关系...")

    for i, rel in enumerate(tqdm(relations, desc="导入进度")):
        try:
            source = rel["source"]
            target = rel["target"]
            source_type = rel["source_type"]
            target_type = rel["target_type"]
            rel_type = rel["type"]

            cn_rel_type = relation_type_map.get(rel_type, rel_type)

            source_label = type_to_label.get(source_type, "实体")
            target_label = type_to_label.get(target_type, "实体")

            # 构建属性
            source_props = {
                "name": source,
                "类型": source_type
            }

            if source_type == "Job":
                source_props["岗位ID"] = rel.get("job_id", "")
                source_props["城市"] = rel.get("city", "")
                source_props["学历要求"] = rel.get("education", "")
                source_props["经验要求"] = rel.get("experience", "")
            elif source_type == "Cert":
                source_props["等级"] = rel.get("level", "")
                source_props["认证机构"] = rel.get("institution", "")
            elif source_type == "Course":
                source_props["模块"] = rel.get("module", "")

            target_props = {
                "name": target,
                "类型": target_type
            }

            # 使用中文标签和关系类型
            query = f"""
            MERGE (a:{source_label} {{name: $source_name}})
            SET a += $source_props
            MERGE (b:{target_label} {{name: $target_name}})
            SET b += $target_props
            MERGE (a)-[r:{cn_rel_type}]->(b)
            SET r.来源类型 = $source_type
            SET r.目标类型 = $target_type
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

            # 批量提交
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
        "岗位节点": "MATCH (n:岗位) RETURN count(n) as count",
        "技能节点": "MATCH (n:技能) RETURN count(n) as count",
        "知识点节点": "MATCH (n:知识点) RETURN count(n) as count",
        "领域节点": "MATCH (n:领域) RETURN count(n) as count",
        "证书节点": "MATCH (n:证书) RETURN count(n) as count",
        "课程节点": "MATCH (n:课程) RETURN count(n) as count",
        "关系总数": "MATCH ()-[r]->() RETURN count(r) as count",
    }

    for desc, query in queries.items():
        try:
            result = graph.run(query).data()
            count = result[0]['count'] if result else 0
            print(f"  📌 {desc}: {count}")
        except:
            print(f"  ❌ {desc}: 查询失败")

    print("\n📋 关系类型统计:")
    try:
        rel_stats = graph.run("""
            MATCH ()-[r]->() 
            RETURN type(r) as rel_type, count(r) as count 
            ORDER BY count DESC
        """).data()

        cn_type = {
            "需要": "（岗位→技能）",
            "教授": "（课程→技能）",
            "属于": "（技能→领域）",
            "考察": "（证书→知识点）",
            "支持": "（证书→岗位）"
        }

        for stat in rel_stats:
            desc = cn_type.get(stat['rel_type'], "")
            print(f"  🔗 {stat['rel_type']}{desc}: {stat['count']} 条")
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")

    print("\n📋 样例数据（前5条）:")
    try:
        samples = graph.run("""
            MATCH (n) 
            RETURN n.name as name, labels(n) as labels, n.类型 as type 
            LIMIT 5
        """).data()

        for s in samples:
            print(f"  🏷️ [{'|'.join(s['labels'])}] {s['name'][:50]} (类型: {s['type']})")
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")


def main():
    print("=" * 60)
    print("🏗️ 第四步：构建Neo4j知识图谱（中文版）")
    print("=" * 60)
    print(f"📌 目标数据库: lifelonglearn")
    print(f"   🆔 ID: 285a6b3d")
    print(f"   📍 URI: {NEO4J_CONFIG['uri']}")
    print(f"   📦 版本: 2026.05.0")
    print("=" * 60)

    # 连接数据库
    graph = connect_neo4j(NEO4J_CONFIG)
    if not graph:
        print("\n💡 提示：如果密码不对，可以重置密码：")
        print("   1. 在 Neo4j Desktop 2 中点击数据库的 '...'")
        print("   2. 选择 'Terminal'")
        print("   3. 输入: neo4j-admin dbms set-initial-password neo4j111")
        print("   4. 重启数据库")
        return

    # 创建约束
    create_constraints(graph)

    # 询问是否清空现有数据
    print("\n⚠️ 是否清空现有数据？")
    choice = input("   输入 y 清空，其他任意键保留: ").strip().lower()
    if choice == 'y':
        print("  🗑️ 清空所有节点和关系...")
        graph.run("MATCH (n) DETACH DELETE n")
        print("  ✅ 已清空")

    # 导入关系数据
    node_count, rel_count = import_from_relations(graph, RELATIONS_PATH)

    # 验证导入
    verify_import(graph)

    print("\n" + "=" * 60)
    print("✅ 第四步完成！知识图谱构建成功！")
    print("=" * 60)
    print(f"\n📊 导入统计:")
    print(f"   🟢 节点: ~{node_count} 个")
    print(f"   🔗 关系: {rel_count} 条")
    print(f"\n🌐 可视化查看:")
    print(f"   1. 打开: http://localhost:7474")
    print(f"   2. 登录: neo4j / {NEO4J_CONFIG['password']}")
    print(f"   3. 运行查询:")
    print(f"      MATCH (n) RETURN n LIMIT 25")
    print(f"\n💡 示例查询（中文）:")
    print(f"   - 查看岗位需要的技能:")
    print(f"     MATCH (j:岗位)-[:需要]->(s:技能) RETURN j, s LIMIT 50")
    print(f"   - 查看课程教授的技能:")
    print(f"     MATCH (c:课程)-[:教授]->(s:技能) RETURN c, s LIMIT 50")
    print(f"   - 查看证书支持的岗位:")
    print(f"     MATCH (c:证书)-[:支持]->(j:岗位) RETURN c, j LIMIT 50")


if __name__ == "__main__":
    main()
