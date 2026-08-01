"""
知识体系分类树 (Knowledge / Academic Curriculum Taxonomy)

以中美大学本科 — 研究生典型「课程体系」为骨架的可下钻知识树,
供用户从「知识体系」而非「职业」角度打标, 暴露自己的认知路径与到达的末梢深度。

结构参考:
  - 中国大学「学科门类 → 一级学科 → 课程」
  - 美国大学「Division / Department → 课程编号 (如 CS101, MATH210) 体系」
  - 通识教育 (General Education / 通识必修) 单列, 体现中美共同基础课

标注沿用全局 6 态 (可叠加):
  like=感兴趣  skill=精通/擅长  know=听说过(认知态, 最浅)
  want=想学    learning=在修/进行中  tried=修过/应用过
派生写回 knowledge.yaml 的 knowledge_topics / knowledge_* 字段,
引擎据此把"你真正学过的知识体系"纳入推荐匹配。
"""

# ============================================================
# 1. 内置知识体系种子树 (中美大学课程骨架)
# ============================================================
KNOWLEDGE_TREE = [
    {
        "id": "acad.math", "name": "数学与逻辑 (理学)", "children": [
            {"id": "acad.math.calc", "name": "微积分", "children": [
                {"id": "acad.math.calc.single", "name": "单变量微积分 (Calculus I)"},
                {"id": "acad.math.calc.multi", "name": "多变量微积分 (Calculus III)"},
                {"id": "acad.math.calc.diff", "name": "微分方程 (ODE/PDE)"},
            ]},
            {"id": "acad.math.lin", "name": "线性代数", "children": [
                {"id": "acad.math.lin.matrix", "name": "矩阵论"},
                {"id": "acad.math.lin.vect", "name": "向量空间"},
            ]},
            {"id": "acad.math.disc", "name": "离散数学", "children": [
                {"id": "acad.math.disc.logic", "name": "数理逻辑"},
                {"id": "acad.math.disc.graph", "name": "图论"},
                {"id": "acad.math.disc.comb", "name": "组合数学"},
            ]},
            {"id": "acad.math.prob", "name": "概率与统计", "children": [
                {"id": "acad.math.prob.theory", "name": "概率论"},
                {"id": "acad.math.prob.stat", "name": "数理统计"},
                {"id": "acad.math.prob.bayes", "name": "贝叶斯推断"},
                {"id": "acad.math.prob.stochastic", "name": "随机过程 (研究生)"},
            ]},
            {"id": "acad.math.real", "name": "实变/复变函数"},
            {"id": "acad.math.num", "name": "数值分析", "children": [
                {"id": "acad.math.num.opt", "name": "最优化方法"},
                {"id": "acad.math.num.convex", "name": "凸优化 (研究生)"},
                {"id": "acad.math.num.sim", "name": "数值模拟"},
            ]},
            {"id": "acad.math.geo", "name": "微分几何"},
            {"id": "acad.math.topo", "name": "拓扑学"},
            {"id": "acad.math.alg", "name": "抽象代数 (群/环/域)"},
        ]
    },
    {
        "id": "acad.cs", "name": "计算机科学与技术 (工学)", "children": [
            {"id": "acad.cs.intro", "name": "程序设计基础", "children": [
                {"id": "acad.cs.intro.py", "name": "Python 程序设计"},
                {"id": "acad.cs.intro.c", "name": "C / C++ 程序设计"},
                {"id": "acad.cs.intro.java", "name": "Java 程序设计"},
                {"id": "acad.cs.intro.rust", "name": "Rust / Go 程序设计"},
            ]},
            {"id": "acad.cs.ds", "name": "数据结构与算法", "children": [
                {"id": "acad.cs.ds.basic", "name": "数据结构 (链表/树/图)"},
                {"id": "acad.cs.ds.algo", "name": "算法设计 (DP/贪心)"},
                {"id": "acad.cs.ds.complex", "name": "计算复杂性"},
                {"id": "acad.cs.ds.advanced", "name": "高级算法 (研究生)"},
            ]},
            {"id": "acad.cs.arch", "name": "计算机组成与体系结构", "children": [
                {"id": "acad.cs.arch.org", "name": "计算机组成原理"},
                {"id": "acad.cs.arch.os", "name": "操作系统"},
                {"id": "acad.cs.arch.net", "name": "计算机网络"},
                {"id": "acad.cs.arch.compile", "name": "编译原理"},
                {"id": "acad.cs.arch.parallel", "name": "并行与分布式计算"},
                {"id": "acad.cs.arch.sys", "name": "计算机系统 (CSAPP)"},
            ]},
            {"id": "acad.cs.db", "name": "数据库系统", "children": [
                {"id": "acad.cs.db.sql", "name": "关系数据库 (SQL)"},
                {"id": "acad.cs.db.nosql", "name": "NoSQL 与分布式存储"},
            ]},
            {"id": "acad.cs.ai", "name": "人工智能", "children": [
                {"id": "acad.cs.ai.ml", "name": "机器学习 (ML)"},
                {"id": "acad.cs.ai.dl", "name": "深度学习 (DL)"},
                {"id": "acad.cs.ai.nlp", "name": "自然语言处理"},
                {"id": "acad.cs.ai.cv", "name": "计算机视觉"},
                {"id": "acad.cs.ai.rl", "name": "强化学习"},
                {"id": "acad.cs.ai.llm", "name": "大模型与生成式 AI"},
                {"id": "acad.cs.ai.kg", "name": "知识图谱"},
                {"id": "acad.cs.ai.multi", "name": "多模态与具身智能"},
                {"id": "acad.cs.ai.robust", "name": "可信 AI (可解释/鲁棒)"},
            ]},
            {"id": "acad.cs.sys", "name": "计算系统与工程 (MIT 特色)", "children": [
                {"id": "acad.cs.sys.design", "name": "计算机系统设计与工程"},
                {"id": "acad.cs.sys.quant", "name": "量化系统与性能工程"},
                {"id": "acad.cs.sys.cloud", "name": "云计算与边缘计算"},
                {"id": "acad.cs.sys.mobile", "name": "移动与嵌入式系统"},
            ]},
            {"id": "acad.cs.blockchain", "name": "区块链与分布式账本", "children": [
                {"id": "acad.cs.blockchain.crypto", "name": "密码学货币原理"},
                {"id": "acad.cs.blockchain.smart", "name": "智能合约"},
                {"id": "acad.cs.blockchain.consensus", "name": "共识算法"},
            ]},
            {"id": "acad.cs.quantum", "name": "量子计算 (研究生)"},
            {"id": "acad.cs.photo", "name": "计算摄影与图像计算"},
            {"id": "acad.cs.se", "name": "软件工程", "children": [
                {"id": "acad.cs.se.plan", "name": "需求与系统设计"},
                {"id": "acad.cs.se.dev", "name": "开发方法学 (Agile/DevOps)"},
                {"id": "acad.cs.se.test", "name": "软件测试"},
                {"id": "acad.cs.se.arch", "name": "软件架构"},
            ]},
            {"id": "acad.cs.theory", "name": "计算理论", "children": [
                {"id": "acad.cs.theory.auto", "name": "自动机与形式语言"},
                {"id": "acad.cs.theory.turing", "name": "可计算性理论"},
            ]},
            {"id": "acad.cs.graphics", "name": "计算机图形学与人机交互", "children": [
                {"id": "acad.cs.graphics.cg", "name": "计算机图形学"},
                {"id": "acad.cs.graphics.hci", "name": "人机交互 (HCI)"},
                {"id": "acad.cs.graphics.cad", "name": "CAD / 几何建模"},
            ]},
            {"id": "acad.cs.security", "name": "信息安全与密码学", "children": [
                {"id": "acad.cs.security.crypto", "name": "密码学"},
                {"id": "acad.cs.security.netsec", "name": "网络与系统安全"},
            ]},
            {"id": "acad.cs.pl", "name": "编程语言理论", "children": [
                {"id": "acad.cs.pl.type", "name": "类型系统"},
                {"id": "acad.cs.pl.func", "name": "函数式编程"},
            ]},
        ]
    },
    {
        "id": "acad.phys", "name": "物理学 (理学)", "children": [
            {"id": "acad.phys.classic", "name": "经典力学", "children": [
                {"id": "acad.phys.classic.newton", "name": "牛顿力学"},
                {"id": "acad.phys.classic.lag", "name": "分析力学 (拉格朗日/哈密顿)"},
            ]},
            {"id": "acad.phys.em", "name": "电磁学"},
            {"id": "acad.phys.quantum", "name": "量子力学", "children": [
                {"id": "acad.phys.quantum.intro", "name": "量子力学导论"},
                {"id": "acad.phys.quantum.field", "name": "量子场论"},
                {"id": "acad.phys.quantum.info", "name": "量子信息 (研究生)"},
            ]},
            {"id": "acad.phys.thermo", "name": "热力学与统计物理"},
            {"id": "acad.phys.astro", "name": "天文学", "children": [
                {"id": "acad.phys.astro.star", "name": "恒星物理"},
                {"id": "acad.phys.astro.cosmo", "name": "宇宙学"},
                {"id": "acad.phys.astro.galaxy", "name": "星系与银河系"},
            ]},
        ]
    },
    {
        "id": "acad.chem", "name": "化学 (理学)", "children": [
            {"id": "acad.chem.inorg", "name": "无机化学"},
            {"id": "acad.chem.org", "name": "有机化学"},
            {"id": "acad.chem.phys", "name": "物理化学"},
            {"id": "acad.chem.bio", "name": "生物化学"},
            {"id": "acad.chem.analytic", "name": "分析化学"},
            {"id": "acad.chem.poly", "name": "高分子化学"},
            {"id": "acad.chem.comp", "name": "理论与计算化学"},
        ]
    },
    {
        "id": "acad.earth", "name": "地球与空间科学 (理学)", "children": [
            {"id": "acad.earth.geo", "name": "地理学", "children": [
                {"id": "acad.earth.geo.nat", "name": "自然地理"},
                {"id": "acad.earth.geo.hum", "name": "人文地理"},
                {"id": "acad.earth.geo.gis", "name": "GIS 地理信息系统"},
            ]},
            {"id": "acad.earth.atmo", "name": "大气科学", "children": [
                {"id": "acad.earth.atmo.meteo", "name": "气象学"},
                {"id": "acad.earth.atmo.climate", "name": "气候学"},
            ]},
            {"id": "acad.earth.ocean", "name": "海洋科学"},
            {"id": "acad.earth.geophy", "name": "地球物理学"},
            {"id": "acad.earth.geol", "name": "地质学"},
            {"id": "acad.earth.eco", "name": "生态学", "children": [
                {"id": "acad.earth.eco.plant", "name": "植物生态学"},
                {"id": "acad.earth.eco.cons", "name": "保护生物学"},
            ]},
        ]
    },
    {
        "id": "acad.bio", "name": "生物与生命科学 (理学)", "children": [
            {"id": "acad.bio.cell", "name": "细胞生物学"},
            {"id": "acad.bio.gene", "name": "遗传学", "children": [
                {"id": "acad.bio.gene.mol", "name": "分子遗传学"},
                {"id": "acad.bio.gene.pop", "name": "群体遗传学"},
            ]},
            {"id": "acad.bio.mol", "name": "分子生物学"},
            {"id": "acad.bio.evo", "name": "进化生物学"},
            {"id": "acad.bio.neuro", "name": "神经科学", "children": [
                {"id": "acad.bio.neuro.sys", "name": "系统神经科学"},
                {"id": "acad.bio.neuro.cog", "name": "认知神经科学"},
                {"id": "acad.bio.neuro.comp", "name": "计算神经科学 (研究生)"},
            ]},
            {"id": "acad.bio.biochem", "name": "生物化学与分子生物学"},
            {"id": "acad.bio.micro", "name": "微生物学"},
            {"id": "acad.bio.dev", "name": "发育生物学"},
            {"id": "acad.bio.immune", "name": "免疫学"},
            {"id": "acad.bio.synth", "name": "合成生物学 (Stanford 强项)"},
            {"id": "acad.bio.sys", "name": "系统生物学 (研究生)"},
            {"id": "acad.bio.genome", "name": "基因组学与精准医学"},
            {"id": "acad.bio.bioinfo2", "name": "计算生物学 (研究生)"},
        ]
    },
    {
        "id": "acad.eng", "name": "工学 (学科群)", "children": [
            {"id": "acad.eng.ee", "name": "电子科学与技术", "children": [
                {"id": "acad.eng.ee.circuit", "name": "电路分析"},
                {"id": "acad.eng.ee.signal", "name": "信号与系统"},
                {"id": "acad.eng.ee.embed", "name": "嵌入式系统"},
                {"id": "acad.eng.ee.dsp", "name": "数字信号处理"},
                {"id": "acad.eng.ee.micro", "name": "微电子与固体电子"},
                {"id": "acad.eng.ee.ics", "name": "集成电路设计"},
            ]},
            {"id": "acad.eng.comm", "name": "信息与通信工程", "children": [
                {"id": "acad.eng.comm.theory", "name": "通信原理"},
                {"id": "acad.eng.comm.wireless", "name": "无线通信"},
                {"id": "acad.eng.comm.net", "name": "计算机网络与协议"},
                {"id": "acad.eng.comm.info", "name": "信息论"},
            ]},
            {"id": "acad.eng.control", "name": "控制科学与工程", "children": [
                {"id": "acad.eng.control.theory", "name": "控制理论"},
                {"id": "acad.eng.control.robot", "name": "机器人学"},
                {"id": "acad.eng.control.auto", "name": "自动化系统"},
                {"id": "acad.eng.control.smart", "name": "智能控制"},
            ]},
            {"id": "acad.eng.elec", "name": "电气工程", "children": [
                {"id": "acad.eng.elec.power", "name": "电力系统"},
                {"id": "acad.eng.elec.motor", "name": "电机与电器"},
                {"id": "acad.eng.elec.power_e", "name": "电力电子"},
                {"id": "acad.eng.elec.hv", "name": "高电压与绝缘"},
            ]},
            {"id": "acad.eng.mech", "name": "机械工程", "children": [
                {"id": "acad.eng.mech.thermo", "name": "工程热力学"},
                {"id": "acad.eng.mech.fluid", "name": "流体力学"},
                {"id": "acad.eng.mech.material", "name": "材料力学"},
                {"id": "acad.eng.mech.design", "name": "机械设计"},
                {"id": "acad.eng.mech.manu", "name": "制造与精密工程"},
            ]},
            {"id": "acad.eng.energy", "name": "能源动力工程", "children": [
                {"id": "acad.eng.energy.thermal", "name": "动力工程及工程热物理"},
                {"id": "acad.eng.energy.new", "name": "新能源科学与工程"},
                {"id": "acad.eng.energy.battery", "name": "储能与电池技术"},
            ]},
            {"id": "acad.eng.civil", "name": "土木与水利工程", "children": [
                {"id": "acad.eng.civil.struct", "name": "结构力学"},
                {"id": "acad.eng.civil.trans", "name": "交通工程"},
                {"id": "acad.eng.civil.hydro", "name": "水利工程"},
                {"id": "acad.eng.civil.geotech", "name": "岩土工程"},
            ]},
            {"id": "acad.eng.arch", "name": "建筑学", "children": [
                {"id": "acad.eng.arch.design", "name": "建筑设计"},
                {"id": "acad.eng.arch.hist", "name": "建筑历史与理论"},
                {"id": "acad.eng.arch.urban", "name": "城乡规划"},
            ]},
            {"id": "acad.eng.ship", "name": "船舶与海洋工程", "children": [
                {"id": "acad.eng.ship.hydro", "name": "船舶流体力学"},
                {"id": "acad.eng.ship.struct", "name": "船舶结构力学"},
                {"id": "acad.eng.ship.offshore", "name": "海洋工程"},
            ]},
            {"id": "acad.eng.aero", "name": "航空宇航科学与技术", "children": [
                {"id": "acad.eng.aero.flight", "name": "飞行器设计"},
                {"id": "acad.eng.aero.prop", "name": "航空发动机"},
                {"id": "acad.eng.aero.astro", "name": "航天工程"},
            ]},
            {"id": "acad.eng.chem", "name": "化学工程与技术", "children": [
                {"id": "acad.eng.chem.reactor", "name": "反应工程"},
                {"id": "acad.eng.chem.sep", "name": "分离工程"},
                {"id": "acad.eng.chem.cat", "name": "催化化学"},
            ]},
            {"id": "acad.eng.mat", "name": "材料科学与工程", "children": [
                {"id": "acad.eng.mat.metal", "name": "金属材料"},
                {"id": "acad.eng.mat.poly", "name": "高分子材料"},
                {"id": "acad.eng.mat.semi", "name": "半导体材料"},
                {"id": "acad.eng.mat.nano", "name": "纳米材料"},
                {"id": "acad.eng.mat.comp", "name": "复合材料"},
            ]},
            {"id": "acad.eng.instr", "name": "仪器科学与技术", "children": [
                {"id": "acad.eng.instr.sensor", "name": "传感器技术"},
                {"id": "acad.eng.instr.precise", "name": "精密测量"},
            ]},
            {"id": "acad.eng.env", "name": "环境科学与工程", "children": [
                {"id": "acad.eng.env.pollution", "name": "水/气污染控制"},
                {"id": "acad.eng.env.monitor", "name": "环境监测"},
            ]},
            {"id": "acad.eng.bme", "name": "生物医学工程 (MIT 王牌)", "children": [
                {"id": "acad.eng.bme.medical", "name": "医学影像设备"},
                {"id": "acad.eng.bme.bio", "name": "生物材料"},
                {"id": "acad.eng.bme.tissue", "name": "组织工程与再生医学"},
                {"id": "acad.eng.bme.genetic", "name": "基因与细胞工程"},
            ]},
            {"id": "acad.eng.nuclear", "name": "核科学与技术"},
            {"id": "acad.eng.software", "name": "软件工程 (学科)", "children": [
                {"id": "acad.eng.software.method", "name": "软件方法学"},
                {"id": "acad.eng.software.quality", "name": "软件质量与可靠性"},
            ]},
            {"id": "acad.eng.safety", "name": "安全科学与工程"},
            {"id": "acad.eng.remote", "name": "测绘与遥感科学与技术", "children": [
                {"id": "acad.eng.remote.rs", "name": "遥感原理"},
                {"id": "acad.eng.remote.geo", "name": "摄影测量"},
            ]},
        ]
    },
    {
        "id": "acad.med", "name": "医学 (学科群)", "children": [
            {"id": "acad.med.basic", "name": "基础医学", "children": [
                {"id": "acad.med.basic.anat", "name": "人体解剖学"},
                {"id": "acad.med.basic.physio", "name": "生理学"},
                {"id": "acad.med.basic.patho", "name": "病理学"},
                {"id": "acad.med.basic.pharm", "name": "药理学"},
            ]},
            {"id": "acad.med.clinical", "name": "临床医学", "children": [
                {"id": "acad.med.clinical.internal", "name": "内科学"},
                {"id": "acad.med.clinical.surg", "name": "外科学"},
                {"id": "acad.med.clinical.pediatric", "name": "儿科学"},
                {"id": "acad.med.clinical.obgyn", "name": "妇产科学"},
                {"id": "acad.med.clinical.neuro", "name": "神经病学"},
                {"id": "acad.med.clinical.onco", "name": "肿瘤学"},
            ]},
            {"id": "acad.med.dental", "name": "口腔医学"},
            {"id": "acad.med.pub", "name": "公共卫生与预防医学", "children": [
                {"id": "acad.med.pub.epid", "name": "流行病学"},
                {"id": "acad.med.pub.biostat", "name": "生物统计学"},
                {"id": "acad.med.pub.health", "name": "卫生政策与管理"},
            ]},
            {"id": "acad.med.pharm", "name": "药学", "children": [
                {"id": "acad.med.pharm.chem", "name": "药物化学"},
                {"id": "acad.med.pharm.clinical", "name": "临床药学"},
            ]},
            {"id": "acad.med.nurse", "name": "护理学"},
            {"id": "acad.med.img", "name": "医学技术 (影像/检验)"},
            {"id": "acad.med.tcm", "name": "中医学与中西医结合"},
        ]
    },
    {
        "id": "acad.agri", "name": "农学 (学科群)", "children": [
            {"id": "acad.agri.crop", "name": "作物学", "children": [
                {"id": "acad.agri.crop.breed", "name": "作物遗传育种"},
                {"id": "acad.agri.crop.cult", "name": "作物栽培"},
            ]},
            {"id": "acad.agri.hort", "name": "园艺学"},
            {"id": "acad.agri.protect", "name": "植物保护"},
            {"id": "acad.agri.res", "name": "农业资源与环境"},
            {"id": "acad.agri.animal", "name": "畜牧学"},
            {"id": "acad.agri.vet", "name": "兽医学"},
            {"id": "acad.agri.forest", "name": "林学"},
            {"id": "acad.agri.fish", "name": "水产"},
            {"id": "acad.agri.food", "name": "食品科学与工程"},
        ]
    },
    {
        "id": "acad.econ", "name": "经济与管理 (学科群)", "children": [
            {"id": "acad.econ.micro", "name": "微观经济学"},
            {"id": "acad.econ.macro", "name": "宏观经济学"},
            {"id": "acad.econ.econo", "name": "计量经济学"},
            {"id": "acad.econ.fin", "name": "金融学", "children": [
                {"id": "acad.econ.fin.corp", "name": "公司金融"},
                {"id": "acad.econ.fin.invest", "name": "投资学"},
                {"id": "acad.econ.fin.deriv", "name": "衍生品定价"},
                {"id": "acad.econ.fin.actuary", "name": "保险与精算"},
            ]},
            {"id": "acad.econ.acc", "name": "会计学"},
            {"id": "acad.econ.mgmt", "name": "管理学", "children": [
                {"id": "acad.econ.mgmt.strategy", "name": "战略管理"},
                {"id": "acad.econ.mgmt.org", "name": "组织行为学"},
                {"id": "acad.econ.mgmt.mkt", "name": "市场营销"},
                {"id": "acad.econ.mgmt.ops", "name": "运营管理"},
                {"id": "acad.econ.mgmt.entrep", "name": "创业管理 (Stanford GSB)"},
                {"id": "acad.econ.mgmt.leader", "name": "领导力与组织变革"},
            ]},
            {"id": "acad.econ.biz", "name": "工商管理 (MBA)"},
            {"id": "acad.econ.policy", "name": "公共管理与公共政策"},
            {"id": "acad.econ.behavior", "name": "行为经济学 (Nobel 方向)"},
            {"id": "acad.econ.decision", "name": "决策科学"},
            {"id": "acad.econ.game", "name": "博弈论"},
        ]
    },
    {
        "id": "acad.social", "name": "人文与社会科学 (学科群)", "children": [
            {"id": "acad.social.psych", "name": "心理学", "children": [
                {"id": "acad.social.psych.cog", "name": "认知心理学"},
                {"id": "acad.social.psych.social", "name": "社会心理学"},
                {"id": "acad.social.psych.clinical", "name": "临床心理学"},
                {"id": "acad.social.psych.ie", "name": "工业与组织心理学"},
            ]},
            {"id": "acad.social.phil", "name": "哲学", "children": [
                {"id": "acad.social.phil.logic", "name": "逻辑学"},
                {"id": "acad.social.phil.ethics", "name": "伦理学"},
                {"id": "acad.social.phil.mind", "name": "心灵哲学"},
                {"id": "acad.social.phil.sci", "name": "科学哲学"},
            ]},
            {"id": "acad.social.hist", "name": "历史学", "children": [
                {"id": "acad.social.hist.world", "name": "世界史"},
                {"id": "acad.social.hist.china", "name": "中国史"},
                {"id": "acad.social.hist.tech", "name": "科学技术史"},
            ]},
            {"id": "acad.social.pol", "name": "政治学与国际关系", "children": [
                {"id": "acad.social.pol.intl", "name": "国际关系"},
                {"id": "acad.social.pol.comp", "name": "比较政治"},
            ]},
            {"id": "acad.social.law", "name": "法学", "children": [
                {"id": "acad.social.law.civil", "name": "民法"},
                {"id": "acad.social.law.const", "name": "宪法"},
                {"id": "acad.social.law.intl", "name": "国际法"},
                {"id": "acad.social.law.crim", "name": "刑法"},
                {"id": "acad.social.law.biz", "name": "商法与经济法"},
            ]},
            {"id": "acad.social.soci", "name": "社会学"},
            {"id": "acad.social.ling", "name": "语言学", "children": [
                {"id": "acad.social.ling.syntax", "name": "句法学"},
                {"id": "acad.social.ling.sem", "name": "语义学"},
                {"id": "acad.social.ling.cogsci", "name": "心理语言学"},
            ]},
            {"id": "acad.social.edu", "name": "教育学", "children": [
                {"id": "acad.social.edu.psy", "name": "教育心理学"},
                {"id": "acad.social.edu.curr", "name": "课程与教学论"},
                {"id": "acad.social.edu.tech", "name": "教育技术学"},
            ]},
            {"id": "acad.social.news", "name": "新闻传播学", "children": [
                {"id": "acad.social.news.journ", "name": "新闻学"},
                {"id": "acad.social.news.comm", "name": "传播学"},
            ]},
            {"id": "acad.social.sts", "name": "科学、技术与社会 (STS, MIT 核心)", "children": [
                {"id": "acad.social.sts.history", "name": "科技史与科技哲学"},
                {"id": "acad.social.sts.policy", "name": "科技政策与治理"},
                {"id": "acad.social.sts.ethics", "name": "技术伦理与社会影响"},
            ]},
            {"id": "acad.social.dh", "name": "数字人文 (Stanford 强项)", "children": [
                {"id": "acad.social.dh.text", "name": "文本挖掘与计算语言学"},
                {"id": "acad.social.dh.geo", "name": "数字地图与空间人文"},
            ]},
            {"id": "acad.social.anthro", "name": "人类学 (文化/考古)"},
        ]
    },
    {
        "id": "acad.art", "name": "艺术学 (学科群)", "children": [
            {"id": "acad.art.visual", "name": "美术学", "children": [
                {"id": "acad.art.visual.draw", "name": "绘画"},
                {"id": "acad.art.visual.sculpt", "name": "雕塑"},
            ]},
            {"id": "acad.art.music", "name": "音乐与舞蹈学", "children": [
                {"id": "acad.art.music.harmony", "name": "和声学"},
                {"id": "acad.art.music.comp", "name": "作曲"},
            ]},
            {"id": "acad.art.design", "name": "设计学", "children": [
                {"id": "acad.art.design.graph", "name": "平面设计"},
                {"id": "acad.art.design.ux", "name": "交互设计"},
                {"id": "acad.art.design.industrial", "name": "工业设计"},
            ]},
            {"id": "acad.art.film", "name": "戏剧与影视学"},
            {"id": "acad.art.arch", "name": "艺术学理论"},
        ]
    },
    {
        "id": "acad.ge", "name": "通识与思政教育", "children": [
            {"id": "acad.ge.write", "name": "写作与表达", "children": [
                {"id": "acad.ge.write.aca", "name": "学术写作 (Academic Writing)"},
                {"id": "acad.ge.write.speech", "name": "公共演讲"},
            ]},
            {"id": "acad.ge.human", "name": "人文经典 (Great Books)"},
            {"id": "acad.ge.sci", "name": "自然科学通识"},
            {"id": "acad.ge.social", "name": "社会与公民"},
            {"id": "acad.ge.pe", "name": "体育与身心健康"},
            {"id": "acad.ge.ethics", "name": "科技伦理 (Tech & Society)"},
            {"id": "acad.ge.politics", "name": "思想政治理论课", "children": [
                {"id": "acad.ge.politics.marx", "name": "马克思主义基本原理"},
                {"id": "acad.ge.politics.modern", "name": "毛泽东思想和中国特色社会主义理论体系"},
                {"id": "acad.ge.politics.history", "name": "中国近现代史纲要"},
                {"id": "acad.ge.politics.moral", "name": "思想道德与法治"},
                {"id": "acad.ge.politics.policy", "name": "形势与政策"},
            ]},
            {"id": "acad.ge.military", "name": "军事理论与国家安全"},
            {"id": "acad.ge.innov", "name": "创新创业基础"},
            {"id": "acad.ge.comm", "name": "沟通与表达要求 (MIT Communication)", "children": [
                {"id": "acad.ge.comm.write", "name": "专业写作"},
                {"id": "acad.ge.comm.oral", "name": "口头表达与答辩"},
                {"id": "acad.ge.comm.team", "name": "团队沟通协作"},
            ]},
            {"id": "acad.ge.research", "name": "本科科研 (UROP/SURF)"},
            {"id": "acad.ge.global", "name": "全球视野与跨文化"},
            {"id": "acad.ge.design", "name": "设计思维与原型 (Maker/FabLab)"},
        ]
    },
    {
        "id": "acad.inter", "name": "交叉与前沿学科", "children": [
            {"id": "acad.inter.data", "name": "数据科学", "children": [
                {"id": "acad.inter.data.mining", "name": "数据挖掘"},
                {"id": "acad.inter.data.big", "name": "大数据系统"},
                {"id": "acad.inter.data.stats", "name": "统计学习 (研究生)"},
            ]},
            {"id": "acad.inter.cog", "name": "认知科学", "children": [
                {"id": "acad.inter.cog.ai", "name": "计算认知"},
                {"id": "acad.inter.cog.brain", "name": "脑与心智"},
            ]},
            {"id": "acad.inter.bioinfo", "name": "生物信息学"},
            {"id": "acad.inter.quant", "name": "量化金融", "children": [
                {"id": "acad.inter.quant.trading", "name": "量化交易"},
                {"id": "acad.inter.quant.risk", "name": "金融风险管理"},
            ]},
            {"id": "acad.inter.env", "name": "环境科学与可持续", "children": [
                {"id": "acad.inter.env.climate", "name": "气候科学"},
                {"id": "acad.inter.env.energy", "name": "新能源技术"},
            ]},
            {"id": "acad.inter.ic", "name": "集成电路科学与工程"},
            {"id": "acad.inter.ai", "name": "智能科学与技术"},
            {"id": "acad.inter.cyber", "name": "网络空间安全"},
            {"id": "acad.inter.region", "name": "区域国别学"},
            {"id": "acad.inter.sys", "name": "系统科学"},
            {"id": "acad.inter.nano", "name": "纳米科学与技术"},
            {"id": "acad.inter.biomed", "name": "脑科学 (类脑智能)"},
            {"id": "acad.inter.aigovern", "name": "AI 伦理与治理 (Stanford HAI)"},
            {"id": "acad.inter.compsoc", "name": "计算社会科学", "children": [
                {"id": "acad.inter.compsoc.net", "name": "社会网络分析"},
                {"id": "acad.inter.compsoc.sims", "name": "社会系统建模与仿真"},
            ]},
            {"id": "acad.inter.sustain", "name": "可持续设计与循环经济"},
            {"id": "acad.inter.fintech", "name": "金融科技 (FinTech)"},
            {"id": "acad.inter.space", "name": "空间与卫星工程 (新航天)"},
        ]
    },
    {
        "id": "acad.startup", "name": "创业与领导力 (MIT/Stanford 特色)", "children": [
            {"id": "acad.startup.venture", "name": "创业学 (Entrepreneurship)", "children": [
                {"id": "acad.startup.venture.idea", "name": "机会识别与创意"},
                {"id": "acad.startup.venture.model", "name": "商业模式画布"},
                {"id": "acad.startup.venture.scale", "name": "规模化与增长"},
            ]},
            {"id": "acad.startup.vc", "name": "风险投资与融资", "children": [
                {"id": "acad.startup.vc.angel", "name": "天使与种子轮"},
                {"id": "acad.startup.vc.term", "name": "投资条款与估值"},
            ]},
            {"id": "acad.startup.product", "name": "产品设计与管理 (PDM)", "children": [
                {"id": "acad.startup.product.pm", "name": "产品经理方法"},
                {"id": "acad.startup.product.uxr", "name": "用户体验研究 (UXR)"},
            ]},
            {"id": "acad.startup.leader", "name": "技术领导力与组织", "children": [
                {"id": "acad.startup.leader.nego", "name": "谈判与沟通"},
                {"id": "acad.startup.leader.change", "name": "变革管理"},
            ]},
            {"id": "acad.startup.ip", "name": "知识产权与专利战略"},
        ]
    },
]


# ============================================================
# 2. 派生 / 写回逻辑 (knowledge 维度)
# ============================================================
def _build_all_index(custom: dict, ext_index: dict) -> dict:
    from services.dimension_taxonomy import _index_tree
    all_index = _index_tree(KNOWLEDGE_TREE)
    for cid, info in custom.items():
        pid = info.get("parent_id")
        if pid in all_index:
            ppath = all_index[pid]["path"]
            pdepth = all_index[pid]["depth"]
            all_index[cid] = {
                "id": cid, "name": info["name"], "parent_id": pid,
                "depth": pdepth + 1, "path": ppath + [info["name"]],
            }
    for cid, rec in ext_index.items():
        pid = rec["parent_id"]
        if pid in all_index:
            ppath = all_index[pid]["path"]
            pdepth = all_index[pid]["depth"]
            all_index[cid] = {
                "id": cid, "name": rec["name"], "parent_id": pid,
                "depth": pdepth + 1, "path": ppath + [rec["name"]],
            }
    return all_index


def derive_knowledge(marks: dict, custom: dict, ext_index: dict | None = None) -> dict:
    """从知识标注派生认知路径 / 末梢 / 关键词, 并刻画「认知到达的末梢深度」。

    在 6 态框架下, 知识体系语境的语义映射:
      know=听说过(认知态, 最浅)  like=感兴趣  want=想学
      learning=在修/进行中       tried=修过/应用过  skill=精通/擅长(最深)
    depth 由树的层级表达: 域(depth0/1) → 学科 → 课程(末梢)。
    levels[state] = 该状态下所有已标节点达到的最大 depth, 反映认知末梢级别。
    """
    from services.dimension_taxonomy import _path_ids_in, compute_sibling_gaps
    all_index = _build_all_index(custom, ext_index or {})

    paths = []
    leaves = []
    keywords = set()
    skill_keywords = set()
    know_keywords = set()
    want_keywords = set()
    learning_keywords = set()
    tried_keywords = set()
    # 各状态达到的最大深度 (认知末梢级别)
    levels: dict[str, int] = {}

    for nid, m in marks.items():
        if not isinstance(m, dict):
            continue
        states = {s: bool(m.get(s)) for s in ("like", "skill", "know", "want", "learning", "tried")}
        if not any(states.values()):
            continue
        node = all_index.get(nid)
        if not node:
            continue
        depth = node["depth"]
        for s in ("like", "skill", "know", "want", "learning", "tried"):
            if states.get(s):
                levels[s] = max(levels.get(s, 0), depth)
        paths.append({
            "node_id": nid, "mark": states,
            "path": [{"id": i, "name": all_index[i]["name"]} for i in _path_ids_in(nid, all_index)],
        })
        has_marked_child = any(
            k.startswith(nid + ".") and isinstance(v, dict)
            and any(v.get(s) for s in ("like", "skill", "know", "want", "learning", "tried"))
            for k, v in marks.items()
        )
        if not has_marked_child:
            leaves.append({"id": nid, "name": node["name"], "mark": states})
        keywords.add(node["name"])
        for p in node["path"]:
            keywords.add(p)
        if states.get("skill"):
            skill_keywords.add(node["name"])
        if states.get("know"):
            know_keywords.add(node["name"])
        if states.get("want"):
            want_keywords.add(node["name"])
        if states.get("learning"):
            learning_keywords.add(node["name"])
        if states.get("tried"):
            tried_keywords.add(node["name"])

    return {
        "paths": paths,
        "leaves": leaves,
        "keywords": sorted(keywords),
        "skill_keywords": sorted(skill_keywords),
        "know_keywords": sorted(know_keywords),
        "want_keywords": sorted(want_keywords),
        "learning_keywords": sorted(learning_keywords),
        "tried_keywords": sorted(tried_keywords),
        # 认知末梢级别: 各状态达到的最大树深 (0=域级, 越大越细到具体课程)
        "levels": levels,
        "sibling_gaps": compute_sibling_gaps("knowledge", marks, custom, ext_index),
    }


def apply_knowledge(derived: dict, dim_data: dict) -> dict:
    """把派生关键词写回 knowledge.yaml。

    knowledge_topics 仅承载 like + skill (强信号);
    认知态/弱信号 (know/want/learning/tried) 独立字段, 供引擎差异化加权。
    """
    like_or_skill_keywords = set(derived["keywords"]) - set(derived["know_keywords"]) \
        - set(derived["want_keywords"]) - set(derived["learning_keywords"]) \
        - set(derived["tried_keywords"])
    existing = dim_data.get("knowledge_topics", [])
    existing = [t for t in existing if not (isinstance(t, dict) and t.get("_derived"))]
    derived_topics = [
        {"keyword": kw, "weight": 0.8, "_derived": True}
        for kw in sorted(like_or_skill_keywords)
    ]
    dim_data["knowledge_topics"] = existing + derived_topics

    existing_skills = dim_data.get("knowledge_skills", [])
    existing_skills = [s for s in existing_skills if not (isinstance(s, dict) and s.get("_derived"))]
    derived_skills = [
        {"name": kw, "level": 4, "category": "derived", "_derived": True}
        for kw in derived["skill_keywords"]
    ]
    dim_data["knowledge_skills"] = existing_skills + derived_skills

    for field, key, w in (
        ("knowledge_know", "know_keywords", 0.3),
        ("knowledge_want", "want_keywords", 0.45),
        ("knowledge_learning", "learning_keywords", 0.6),
        ("knowledge_tried", "tried_keywords", 0.7),
    ):
        existing_f = dim_data.get(field, [])
        existing_f = [x for x in existing_f if not (isinstance(x, dict) and x.get("_derived"))]
        dim_data[field] = existing_f + [
            {"keyword": kw, "weight": w, "_derived": True} for kw in derived.get(key, [])
        ]
    return dim_data


from services.dimension_taxonomy import register_dimension  # noqa: E402

register_dimension("knowledge", {
    "name": "知识体系",
    "tree": KNOWLEDGE_TREE,
    "mark_file": "knowledge_map.yaml",
    "target_dim": "knowledge",
    "provider": None,
    "derive": derive_knowledge,
    "apply": apply_knowledge,
})
