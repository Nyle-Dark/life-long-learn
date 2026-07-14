import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).parent
RAW_DATA_BASE = BASE_DIR / "raw_data"
PATH_CERT_JSON = RAW_DATA_BASE / "证书json"
PATH_COURSE_JSON = RAW_DATA_BASE / "课程大纲json"
PATH_JOB_JSON = RAW_DATA_BASE / "职业数据json"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class DataLoader:

    def __init__(self):
        self.jobs_data = []
        self.courses_data = []
        self.certs_data = []
        self.load_report = {
            'cert_files': [],
            'course_files': [],
            'job_files': [],
            'failed_files': []
        }

    def scan_directory(self, directory: Path, file_type: str) -> List[Path]:
        print(f"\n📂 扫描目录: {directory}")

        if not directory.exists():
            print(f"   ❌ 目录不存在！")
            print(f"   📍 完整路径: {directory.absolute()}")
            return []

        json_files = sorted(directory.glob("*.json"))

        if not json_files:
            print(f"   ⚠️  未找到JSON文件")
            return []

        print(f"   ✅ 找到 {len(json_files)} 个JSON文件:")
        for i, f in enumerate(json_files, 1):
            size_kb = f.stat().st_size / 1024
            print(f"      {i}. {f.name} ({size_kb:.1f} KB)")

        return json_files

    def load_single_file(self, file_path: Path) -> Optional[Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data is None:
                print(f"   ⚠️  {file_path.name}: 文件内容为空")
                return None

            if isinstance(data, list):
                print(f"   ✅ {file_path.name}: 加载成功 ({len(data)} 条记录)")
            elif isinstance(data, dict):
                print(f"   ✅ {file_path.name}: 加载成功 (单个对象)")
            else:
                print(f"   ⚠️  {file_path.name}: 未知数据格式")
                return None

            return data

        except json.JSONDecodeError as e:
            print(f"   ❌ {file_path.name}: JSON格式错误 - {e}")
            self.load_report['failed_files'].append(str(file_path))
            return None
        except Exception as e:
            print(f"   ❌ {file_path.name}: {e}")
            self.load_report['failed_files'].append(str(file_path))
            return None

    def load_all_data(self) -> Dict[str, List[Dict]]:
        print("\n" + "=" * 60)
        print("📥 第一步：加载所有JSON数据文件")
        print("=" * 60)

        print("\n📜 加载证书数据...")
        cert_files = self.scan_directory(PATH_CERT_JSON, "证书")
        self.load_report['cert_files'] = [str(f) for f in cert_files]
        for cert_file in cert_files:
            data = self.load_single_file(cert_file)
            if data:
                if isinstance(data, list):
                    self.certs_data.extend(data)
                else:
                    self.certs_data.append(data)

        print("\n📚 加载课程数据...")
        course_files = self.scan_directory(PATH_COURSE_JSON, "课程大纲")
        self.load_report['course_files'] = [str(f) for f in course_files]
        for course_file in course_files:
            data = self.load_single_file(course_file)
            if data:
                if isinstance(data, list):
                    self.courses_data.extend(data)
                else:
                    self.courses_data.append(data)

        print("\n💼 加载岗位数据...")
        job_files = self.scan_directory(PATH_JOB_JSON, "职业数据")
        self.load_report['job_files'] = [str(f) for f in job_files]
        for job_file in job_files:
            data = self.load_single_file(job_file)
            if data:
                if isinstance(data, list):
                    self.jobs_data.extend(data)
                else:
                    self.jobs_data.append(data)

        return {
            'certs': self.certs_data,
            'courses': self.courses_data,
            'jobs': self.jobs_data
        }

    def print_summary(self):
        print("\n" + "=" * 60)
        print("📊 数据加载汇总")
        print("=" * 60)

        total_files = (
                len(self.load_report['cert_files']) +
                len(self.load_report['course_files']) +
                len(self.load_report['job_files'])
        )

        print(f"\n📁 扫描文件总数: {total_files}")
        print(f"   - 证书文件: {len(self.load_report['cert_files'])} 个")
        print(f"   - 课程文件: {len(self.load_report['course_files'])} 个")
        print(f"   - 岗位文件: {len(self.load_report['job_files'])} 个")

        print(f"\n📄 加载记录总数: {len(self.certs_data) + len(self.courses_data) + len(self.jobs_data)}")
        print(f"   - 📜 证书记录: {len(self.certs_data)} 条")
        print(f"   - 📚 课程记录: {len(self.courses_data)} 条")
        print(f"   - 💼 岗位记录: {len(self.jobs_data)} 条")

        if self.load_report['failed_files']:
            print(f"\n⚠️  加载失败的文件 ({len(self.load_report['failed_files'])} 个):")
            for f in self.load_report['failed_files']:
                print(f"   - {f}")


class DataValidator:

    def __init__(self, jobs_data, courses_data, certs_data):
        self.jobs_data = jobs_data
        self.courses_data = courses_data
        self.certs_data = certs_data
        self.validation_results = {
            'jobs': {'valid': 0, 'invalid': 0, 'issues': []},
            'courses': {'valid': 0, 'invalid': 0, 'issues': []},
            'certs': {'valid': 0, 'invalid': 0, 'issues': []}
        }

    def validate_jobs(self) -> bool:
        print("\n💼 验证岗位数据...")
        required_fields = ['岗位ID', '岗位名称', '核心硬技能 (Hard_Skills)']
        all_valid = True

        for i, job in enumerate(self.jobs_data):
            issues = []
            for field in required_fields:
                if field not in job:
                    issues.append(f"缺少字段: {field}")

            if '核心硬技能 (Hard_Skills)' in job:
                if not job['核心硬技能 (Hard_Skills)']:
                    issues.append("硬技能列表为空")

            if issues:
                all_valid = False
                self.validation_results['jobs']['invalid'] += 1
                job_name = job.get('岗位名称', f'第{i + 1}条')
                self.validation_results['jobs']['issues'].append({
                    'index': i, 'name': job_name, 'issues': issues
                })
                print(f"   ❌ [{job_name}]: {', '.join(issues)}")
            else:
                self.validation_results['jobs']['valid'] += 1
                print(f"   ✅ [{job.get('岗位名称')}] 格式正确")

        return all_valid

    def validate_courses(self) -> bool:
        print("\n📚 验证课程数据...")
        all_valid = True

        for i, course in enumerate(self.courses_data):
            issues = []
            if '课程名称合集' not in course:
                issues.append("缺少字段: 课程名称")

            has_skill = '技能点实体 (Skill)' in course and course['技能点实体 (Skill)']
            has_knowledge = '知识点实体 (Knowledge)' in course and course['知识点实体 (Knowledge)']
            if not has_skill and not has_knowledge:
                issues.append("既无技能点也无知识点")

            if issues:
                all_valid = False
                self.validation_results['courses']['invalid'] += 1
                course_name = course.get('课程名称合集', f'第{i + 1}条')
                self.validation_results['courses']['issues'].append({
                    'index': i, 'name': course_name, 'issues': issues
                })
                print(f"   ❌ [{course_name}]: {', '.join(issues)}")
            else:
                self.validation_results['courses']['valid'] += 1
                print(f"   ✅ [{course.get('课程名称合集')}] 格式正确")

        return all_valid

    def validate_certs(self) -> bool:
        print("\n📜 验证证书数据...")
        all_valid = True

        for i, cert in enumerate(self.certs_data):
            issues = []
            if '证书唯一ID' not in cert:
                issues.append("缺少字段: 证书唯一ID")
            if '证书/竞赛名称' not in cert:
                issues.append("缺少字段: 证书/竞赛名称")

            if issues:
                all_valid = False
                self.validation_results['certs']['invalid'] += 1
                cert_name = cert.get('证书/竞赛名称', f'第{i + 1}条')
                self.validation_results['certs']['issues'].append({
                    'index': i, 'name': cert_name, 'issues': issues
                })
                print(f"   ❌ [{cert_name}]: {', '.join(issues)}")
            else:
                self.validation_results['certs']['valid'] += 1
                print(f"   ✅ [{cert.get('证书/竞赛名称')}] 格式正确")

        return all_valid

    def validate_all(self) -> bool:
        print("\n" + "=" * 60)
        print("🔍 第二步：验证数据格式")
        print("=" * 60)

        jobs_valid = self.validate_jobs()
        courses_valid = self.validate_courses()
        certs_valid = self.validate_certs()

        print("\n" + "-" * 40)
        total_valid = (self.validation_results['jobs']['valid'] +
                       self.validation_results['courses']['valid'] +
                       self.validation_results['certs']['valid'])
        total_invalid = (self.validation_results['jobs']['invalid'] +
                         self.validation_results['courses']['invalid'] +
                         self.validation_results['certs']['invalid'])

        print(f"验证结果: ✅ {total_valid} 条通过 | ❌ {total_invalid} 条有问题")

        return jobs_valid and courses_valid and certs_valid


class DataPreviewer:

    def __init__(self, jobs_data, courses_data, certs_data):
        self.jobs_data = jobs_data
        self.courses_data = courses_data
        self.certs_data = certs_data

    def preview_job(self):
        if not self.jobs_data:
            print("\n💼 无岗位数据可预览")
            return

        print("\n" + "=" * 60)
        print("💼 岗位数据样本")
        print("=" * 60)

        for i, job in enumerate(self.jobs_data[:3]):
            print(f"\n--- 岗位 {i + 1} ---")
            print(f"  ID: {job.get('岗位ID', 'N/A')}")
            print(f"  名称: {job.get('岗位名称', 'N/A')}")
            print(f"  城市: {job.get('城市', 'N/A')}")

            if '门槛要求' in job:
                req = job['门槛要求']
                print(f"  学历要求: {req.get('学历', 'N/A')}")
                print(f"  经验要求: {req.get('经验', 'N/A')}")

            if '薪资特征' in job:
                salary = job['薪资特征']
                print(f"  薪资范围: {salary.get('原始区间', 'N/A')}")

            if '核心硬技能 (Hard_Skills)' in job:
                skills = job['核心硬技能 (Hard_Skills)']
                print(f"  硬技能 ({len(skills)}个): {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}")

    def preview_course(self):
        if not self.courses_data:
            print("\n📚 无课程数据可预览")
            return

        print("\n" + "=" * 60)
        print("📚 课程数据样本")
        print("=" * 60)

        for i, course in enumerate(self.courses_data[:3]):
            print(f"\n--- 课程 {i + 1} ---")
            print(f"  名称: {course.get('课程名称合集', 'N/A')}")
            print(f"  模块: {course.get('任务模块合集', 'N/A')}")

            if '技能点实体 (Skill)' in course:
                skills = course['技能点实体 (Skill)']
                print(f"  技能点 ({len(skills)}个): {', '.join(skills[:3])}{'...' if len(skills) > 3 else ''}")

            if '知识点实体 (Knowledge)' in course:
                knowledge = course['知识点实体 (Knowledge)']
                print(f"  知识点 ({len(knowledge)}个): {', '.join(knowledge[:3])}{'...' if len(knowledge) > 3 else ''}")

    def preview_cert(self):
        if not self.certs_data:
            print("\n📜 无证书数据可预览")
            return

        print("\n" + "=" * 60)
        print("📜 证书数据样本")
        print("=" * 60)

        for i, cert in enumerate(self.certs_data[:3]):
            print(f"\n--- 证书 {i + 1} ---")
            print(f"  ID: {cert.get('证书唯一ID', 'N/A')}")
            print(f"  名称: {cert.get('证书/竞赛名称', 'N/A')}")
            print(f"  机构: {cert.get('发证/主办机构', 'N/A')}")
            print(f"  级别: {cert.get('认证级别', 'N/A')}")

            if '考核知识点 (Exam_Knowledge_Points)' in cert:
                points = cert['考核知识点 (Exam_Knowledge_Points)']
                print(f"  考核知识点 ({len(points)}个): {', '.join(points[:3])}{'...' if len(points) > 3 else ''}")


def main():
    print("=" * 60)
    print("🚀 知识图谱构建 - 第一步：数据加载与验证")
    print("=" * 60)
    print(f"项目目录: {BASE_DIR}")
    print(f"数据目录: {RAW_DATA_BASE}")

    loader = DataLoader()
    all_data = loader.load_all_data()
    loader.print_summary()

    if not any([loader.jobs_data, loader.courses_data, loader.certs_data]):
        print("\n❌ 没有加载到任何数据，请检查数据目录")
        sys.exit(1)

    previewer = DataPreviewer(loader.jobs_data, loader.courses_data, loader.certs_data)
    previewer.preview_job()
    previewer.preview_course()
    previewer.preview_cert()

    validator = DataValidator(loader.jobs_data, loader.courses_data, loader.certs_data)
    if validator.validate_all():
        print("\n✅ 第一步完成！数据加载验证通过")
        print("👉 可以运行第二步: python step2_extract_entities.py")
    else:
        print("\n❌ 数据验证未通过，请检查上述问题")
        sys.exit(1)


if __name__ == "__main__":
    main()
