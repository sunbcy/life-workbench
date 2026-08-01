"""
客观世界行业/领域分类树 (World Taxonomy)

参考 BOSS 直聘「行业 → 职业方向 → 技能」的多级结构，内置一份可下钻的种子树。
用户在前端沿树不断细分、在节点上打标 (感兴趣 / 擅长)，
引擎据此反推兴趣路径与兴趣末梢，并派生出 interests 的 tracking_topics / skills。

节点结构:
    { "id": "it.softeng.frontend", "name": "前端开发", "children": [...] }
标注结构 (存于 interest_map.yaml):
    { "<node_id>": "like" | "skill" }   # like=感兴趣, skill=擅长

扩展能力
--------
1. 内置 WORLD_TREE 已覆盖 BOSS 直聘主要行业及其细分层级 / 职业方向 / 技能叶子。
2. 若内置树仍不够细，可接入「外部职业分类 API」:
   - 实现 `ExternalTaxonomyProvider` 子类 (见文件底部示例 `BossLikeProvider`)
   - 调用 `register_external_provider(provider)` 注册
   - 当内置树某节点没有 `children` 时, 自动回退到外部 provider 拉取更细的叶子
   这样既不破坏现有引擎, 又能按需把客观世界细分到任意深度。
"""

# ============================================================
# 1. 内置种子树 (覆盖 BOSS 直聘主要行业, 多层细分)
# ============================================================
WORLD_TREE = [
    {
        "id": "it", "name": "互联网/IT", "children": [
            {
                "id": "it.softeng", "name": "软件开发", "children": [
                    {"id": "it.softeng.frontend", "name": "前端开发", "children": [
                        {"id": "it.softeng.frontend.web", "name": "Web 前端", "children": [
                            {"id": "it.softeng.frontend.web.vue", "name": "Vue"},
                            {"id": "it.softeng.frontend.web.react", "name": "React"},
                            {"id": "it.softeng.frontend.web.ng", "name": "Angular"},
                            {"id": "it.softeng.frontend.web.svelte", "name": "Svelte"},
                            {"id": "it.softeng.frontend.web.mini", "name": "小程序"},
                        ]},
                        {"id": "it.softeng.frontend.mobile", "name": "移动端", "children": [
                            {"id": "it.softeng.frontend.mobile.rn", "name": "React Native"},
                            {"id": "it.softeng.frontend.mobile.flutter", "name": "Flutter"},
                            {"id": "it.softeng.frontend.mobile.ios", "name": "iOS 原生"},
                            {"id": "it.softeng.frontend.mobile.android", "name": "Android 原生"},
                        ]},
                    ]},
                    {"id": "it.softeng.backend", "name": "后端开发", "children": [
                        {"id": "it.softeng.backend.lang", "name": "语言", "children": [
                            {"id": "it.softeng.backend.lang.go", "name": "Go"},
                            {"id": "it.softeng.backend.lang.java", "name": "Java"},
                            {"id": "it.softeng.backend.lang.py", "name": "Python"},
                            {"id": "it.softeng.backend.lang.rust", "name": "Rust"},
                            {"id": "it.softeng.backend.lang.cpp", "name": "C++"},
                            {"id": "it.softeng.backend.lang.node", "name": "Node.js"},
                            {"id": "it.softeng.backend.lang.php", "name": "PHP"},
                        ]},
                        {"id": "it.softeng.backend.arch", "name": "架构", "children": [
                            {"id": "it.softeng.backend.arch.micro", "name": "微服务"},
                            {"id": "it.softeng.backend.arch.cloud", "name": "云原生"},
                            {"id": "it.softeng.backend.arch.serverless", "name": "Serverless"},
                            {"id": "it.softeng.backend.arch.distributed", "name": "分布式系统"},
                        ]},
                        {"id": "it.softeng.backend.db", "name": "数据库", "children": [
                            {"id": "it.softeng.backend.db.mysql", "name": "MySQL"},
                            {"id": "it.softeng.backend.db.pg", "name": "PostgreSQL"},
                            {"id": "it.softeng.backend.db.redis", "name": "Redis"},
                            {"id": "it.softeng.backend.db.mongo", "name": "MongoDB"},
                            {"id": "it.softeng.backend.db.click", "name": "ClickHouse"},
                        ]},
                    ]},
                    {"id": "it.softeng.data", "name": "数据/算法", "children": [
                        {"id": "it.softeng.data.algo", "name": "算法工程师"},
                        {"id": "it.softeng.data.ml", "name": "机器学习"},
                        {"id": "it.softeng.data.dl", "name": "深度学习"},
                        {"id": "it.softeng.data.bi", "name": "数据分析/BI"},
                        {"id": "it.softeng.data.etl", "name": "数据开发/ETL"},
                        {"id": "it.softeng.data.bigdata", "name": "大数据"},
                    ]},
                    {"id": "it.softeng.test", "name": "测试开发", "children": [
                        {"id": "it.softeng.test.auto", "name": "自动化测试", "children": [
                            {"id": "it.softeng.test.auto.ui", "name": "UI 自动化"},
                            {"id": "it.softeng.test.auto.api", "name": "接口自动化"},
                            {"id": "it.softeng.test.auto.e2e", "name": "端到端测试"},
                            {"id": "it.softeng.test.auto.unit", "name": "单元测试"},
                        ]},
                        {"id": "it.softeng.test.perf", "name": "性能测试", "children": [
                            {"id": "it.softeng.test.perf.load", "name": "负载测试"},
                            {"id": "it.softeng.test.perf.stress", "name": "压力测试"},
                            {"id": "it.softeng.test.perf.bench", "name": "基准测试"},
                        ]},
                        {"id": "it.softeng.test.sec", "name": "安全测试", "children": [
                            {"id": "it.softeng.test.sec.pentest", "name": "渗透测试"},
                            {"id": "it.softeng.test.sec.sast", "name": "静态代码扫描"},
                        ]},
                        {"id": "it.softeng.test.compat", "name": "兼容性测试"},
                        {"id": "it.softeng.test.tool", "name": "测试工具/框架", "children": [
                            {"id": "it.softeng.test.tool.jmeter", "name": "JMeter"},
                            {"id": "it.softeng.test.tool.selenium", "name": "Selenium"},
                            {"id": "it.softeng.test.tool.cypress", "name": "Cypress"},
                            {"id": "it.softeng.test.tool.pytest", "name": "Pytest"},
                        ]},
                    ]},
                    {"id": "it.softeng.devops", "name": "运维/DevOps", "children": [
                        {"id": "it.softeng.devops.sre", "name": "SRE", "children": [
                            {"id": "it.softeng.devops.sre.monitor", "name": "监控告警"},
                            {"id": "it.softeng.devops.sre.oncall", "name": "On-Call 值班"},
                            {"id": "it.softeng.devops.sre.slo", "name": "SLO/稳定性"},
                        ]},
                        {"id": "it.softeng.devops.sec", "name": "安全运维", "children": [
                            {"id": "it.softeng.devops.sec.cicd", "name": "DevSecOps"},
                            {"id": "it.softeng.devops.sec.vuln", "name": "漏洞管理"},
                        ]},
                        {"id": "it.softeng.devops.k8s", "name": "Kubernetes", "children": [
                            {"id": "it.softeng.devops.k8s.helm", "name": "Helm"},
                            {"id": "it.softeng.devops.k8s.istio", "name": "服务网格/Istio"},
                            {"id": "it.softeng.devops.k8s.operator", "name": "Operator 开发"},
                        ]},
                        {"id": "it.softeng.devops.ci", "name": "CI/CD", "children": [
                            {"id": "it.softeng.devops.ci.jenkins", "name": "Jenkins"},
                            {"id": "it.softeng.devops.ci.gitlab", "name": "GitLab CI"},
                            {"id": "it.softeng.devops.ci.gha", "name": "GitHub Actions"},
                        ]},
                        {"id": "it.softeng.devops.iac", "name": "基础设施即代码", "children": [
                            {"id": "it.softeng.devops.iac.terraform", "name": "Terraform"},
                            {"id": "it.softeng.devops.iac.ansible", "name": "Ansible"},
                        ]},
                        {"id": "it.softeng.devops.cloud", "name": "云平台", "children": [
                            {"id": "it.softeng.devops.cloud.aws", "name": "AWS"},
                            {"id": "it.softeng.devops.cloud.ali", "name": "阿里云"},
                            {"id": "it.softeng.devops.cloud.tc", "name": "腾讯云"},
                        ]},
                        {"id": "it.softeng.devops.observe", "name": "可观测性", "children": [
                            {"id": "it.softeng.devops.observe.prom", "name": "Prometheus"},
                            {"id": "it.softeng.devops.observe.grafana", "name": "Grafana"},
                            {"id": "it.softeng.devops.observe.elk", "name": "ELK 日志"},
                        ]},
                    ]},
                    {"id": "it.softeng.embed", "name": "嵌入式开发", "children": [
                        {"id": "it.softeng.embed.mcu", "name": "单片机/MCU", "children": [
                            {"id": "it.softeng.embed.mcu.stm32", "name": "STM32"},
                            {"id": "it.softeng.embed.mcu.avr", "name": "AVR/Arduino"},
                            {"id": "it.softeng.embed.mcu.esp", "name": "ESP32/ESP8266"},
                            {"id": "it.softeng.embed.mcu.riscv", "name": "RISC-V MCU"},
                        ]},
                        {"id": "it.softeng.embed.rtos", "name": "RTOS", "children": [
                            {"id": "it.softeng.embed.rtos.freertos", "name": "FreeRTOS"},
                            {"id": "it.softeng.embed.rtos.rtthread", "name": "RT-Thread"},
                            {"id": "it.softeng.embed.rtos.zephyr", "name": "Zephyr"},
                        ]},
                        {"id": "it.softeng.embed.driver", "name": "驱动开发", "children": [
                            {"id": "it.softeng.embed.driver.linux", "name": "Linux 驱动"},
                            {"id": "it.softeng.embed.driver.bare", "name": "裸机驱动"},
                            {"id": "it.softeng.embed.driver.bsp", "name": "BSP 移植"},
                        ]},
                        {"id": "it.softeng.embed.arm", "name": "ARM 架构", "children": [
                            {"id": "it.softeng.embed.arm.cortexm", "name": "Cortex-M"},
                            {"id": "it.softeng.embed.arm.cortexa", "name": "Cortex-A"},
                            {"id": "it.softeng.embed.arm.neon", "name": "NEON 指令优化"},
                        ]},
                        {"id": "it.softeng.embed.fpga", "name": "FPGA 嵌入式", "children": [
                            {"id": "it.softeng.embed.fpga.verilog", "name": "Verilog/VHDL"},
                            {"id": "it.softeng.embed.fpga.soc", "name": "SoC 设计"},
                        ]},
                        {"id": "it.softeng.embed.iot", "name": "IoT 固件", "children": [
                            {"id": "it.softeng.embed.iot.mqtt", "name": "MQTT 协议"},
                            {"id": "it.softeng.embed.iot.ble", "name": "蓝牙/BLE"},
                            {"id": "it.softeng.embed.iot.zigbee", "name": "Zigbee"},
                            {"id": "it.softeng.embed.iot.ota", "name": "OTA 升级"},
                        ]},
                        {"id": "it.softeng.embed.comm", "name": "通信协议", "children": [
                            {"id": "it.softeng.embed.comm.can", "name": "CAN 总线"},
                            {"id": "it.softeng.embed.comm.i2c", "name": "I2C/SPI"},
                            {"id": "it.softeng.embed.comm.uart", "name": "UART"},
                        ]},
                        {"id": "it.softeng.embed.tools", "name": "嵌入式工具链", "children": [
                            {"id": "it.softeng.embed.tools.cmake", "name": "CMake"},
                            {"id": "it.softeng.embed.tools.gdb", "name": "GDB/调试"},
                            {"id": "it.softeng.embed.tools.jlink", "name": "J-Link"},
                        ]},
                    ]},
                ]
            },
            {
                "id": "it.product", "name": "产品/设计", "children": [
                    {"id": "it.product.pm", "name": "产品经理", "children": [
                        {"id": "it.product.pm.c", "name": "C 端产品"},
                        {"id": "it.product.pm.b", "name": "B 端产品"},
                        {"id": "it.product.pm.data", "name": "数据产品"},
                    ]},
                    {"id": "it.product.ux", "name": "UI/UX 设计", "children": [
                        {"id": "it.product.ux.visual", "name": "视觉设计"},
                        {"id": "it.product.ux.interact", "name": "交互设计"},
                        {"id": "it.product.ux.ue", "name": "用户体验"},
                    ]},
                    {"id": "it.product.op", "name": "运营", "children": [
                        {"id": "it.product.op.content", "name": "内容运营"},
                        {"id": "it.product.op.user", "name": "用户运营"},
                        {"id": "it.product.op.activity", "name": "活动运营"},
                        {"id": "it.product.op.brand", "name": "品牌运营"},
                    ]},
                    {"id": "it.product.market", "name": "市场营销", "children": [
                        {"id": "it.product.market.brand", "name": "品牌营销"},
                        {"id": "it.product.market.growth", "name": "增长黑客"},
                        {"id": "it.product.market.ads", "name": "广告投放"},
                        {"id": "it.product.market.event", "name": "活动营销"},
                        {"id": "it.product.market.content", "name": "内容营销"},
                        {"id": "it.product.market.seo", "name": "SEO/SEM"},
                    ]},
                ]
            },
            {"id": "it.game", "name": "游戏开发", "children": [
                {"id": "it.game.client", "name": "游戏客户端", "children": [
                    {"id": "it.game.client.unity", "name": "Unity"},
                    {"id": "it.game.client.ue", "name": "Unreal Engine"},
                    {"id": "it.game.client.cocos", "name": "Cocos"},
                    {"id": "it.game.client.godot", "name": "Godot"},
                    {"id": "it.game.client.render", "name": "渲染管线"},
                    {"id": "it.game.client.shader", "name": "Shader 开发"},
                ]},
                {"id": "it.game.server", "name": "游戏服务端", "children": [
                    {"id": "it.game.server.arch", "name": "服务端架构"},
                    {"id": "it.game.server.net", "name": "网络同步"},
                    {"id": "it.game.server.match", "name": "匹配/战斗"},
                    {"id": "it.game.server.gs", "name": "GS/逻辑服"},
                ]},
                {"id": "it.game.plan", "name": "游戏策划", "children": [
                    {"id": "it.game.plan.sys", "name": "系统策划"},
                    {"id": "it.game.plan.level", "name": "关卡策划"},
                    {"id": "it.game.plan.num", "name": "数值策划"},
                    {"id": "it.game.plan.story", "name": "剧情策划"},
                ]},
                {"id": "it.game.art", "name": "游戏美术", "children": [
                    {"id": "it.game.art.model", "name": "3D 建模"},
                    {"id": "it.game.art.anim", "name": "动画"},
                    {"id": "it.game.art.fx", "name": "特效"},
                    {"id": "it.game.art.ui", "name": "游戏 UI"},
                ]},
                {"id": "it.game.engine", "name": "游戏引擎技术", "children": [
                    {"id": "it.game.engine.phys", "name": "物理引擎"},
                    {"id": "it.game.engine.audio", "name": "音频引擎"},
                    {"id": "it.game.engine.tools", "name": "编辑器/工具链"},
                ]},
            ]},
            {"id": "it.ai", "name": "人工智能", "children": [
                {"id": "it.ai.llm", "name": "大模型/LLM", "children": [
                    {"id": "it.ai.llm.pretrain", "name": "预训练"},
                    {"id": "it.ai.llm.rlhf", "name": "对齐/RLHF"},
                    {"id": "it.ai.llm.agent", "name": "智能体/Agent"},
                ]},
                {"id": "it.ai.cv", "name": "计算机视觉", "children": [
                    {"id": "it.ai.cv.detect", "name": "目标检测"},
                    {"id": "it.ai.cv.seg", "name": "图像分割"},
                    {"id": "it.ai.cv.ocr", "name": "OCR"},
                    {"id": "it.ai.cv.face", "name": "人脸识别"},
                    {"id": "it.ai.cv.video", "name": "视频理解"},
                ]},
                {"id": "it.ai.nlp", "name": "自然语言处理", "children": [
                    {"id": "it.ai.nlp.textcls", "name": "文本分类"},
                    {"id": "it.ai.nlp.ner", "name": "命名实体识别"},
                    {"id": "it.ai.nlp.qa", "name": "问答系统"},
                    {"id": "it.ai.nlp.mt", "name": "机器翻译"},
                    {"id": "it.ai.nlp.sum", "name": "文本摘要"},
                ]},
                {"id": "it.ai.speech", "name": "语音识别", "children": [
                    {"id": "it.ai.speech.asr", "name": "ASR 语音转写"},
                    {"id": "it.ai.speech.tts", "name": "TTS 语音合成"},
                    {"id": "it.ai.speech.spk", "name": "声纹识别"},
                ]},
                {"id": "it.ai.robot", "name": "机器人学习", "children": [
                    {"id": "it.ai.robot.rl", "name": "强化学习"},
                    {"id": "it.ai.robot.control", "name": "运动控制"},
                    {"id": "it.ai.robot.nav", "name": "SLAM/导航"},
                    {"id": "it.ai.robot.manip", "name": "机械臂抓取"},
                ]},
            ]},
        ]
    },
    {
        "id": "finance", "name": "金融/经济", "children": [
            {"id": "finance.bank", "name": "银行", "children": [
                {"id": "finance.bank.branch", "name": "支行网点"},
                {"id": "finance.bank.risk", "name": "风控"},
                {"id": "finance.bank.corp", "name": "对公业务"},
            ]},
            {"id": "finance.invest", "name": "投资/基金", "children": [
                {"id": "finance.invest.stock", "name": "股票"},
                {"id": "finance.invest.fund", "name": "基金"},
                {"id": "finance.invest.crypto", "name": "数字货币"},
                {"id": "finance.invest.pe", "name": "私募/PE"},
                {"id": "finance.invest.quant", "name": "量化交易"},
            ]},
            {"id": "finance.insurance", "name": "保险", "children": [
                {"id": "finance.insurance.actuary", "name": "精算"},
                {"id": "finance.insurance.sales", "name": "保险销售"},
            ]},
            {"id": "finance.accounting", "name": "会计/审计", "children": [
                {"id": "finance.accounting.audit", "name": "审计"},
                {"id": "finance.accounting.tax", "name": "税务"},
            ]},
            {"id": "finance.econ", "name": "宏观经济"},
            {"id": "finance.fintech", "name": "金融科技"},
        ]
    },
    {
        "id": "medical", "name": "医疗/健康", "children": [
            {"id": "medical.clinical", "name": "临床医学", "children": [
                {"id": "medical.clinical.internal", "name": "内科"},
                {"id": "medical.clinical.surgery", "name": "外科"},
                {"id": "medical.clinical.pediatrics", "name": "儿科"},
                {"id": "medical.clinical.tcm", "name": "中医"},
            ]},
            {"id": "medical.pharma", "name": "医药研发", "children": [
                {"id": "medical.pharma.chem", "name": "化学药"},
                {"id": "medical.pharma.bio", "name": "生物药"},
                {"id": "medical.pharma.clinical", "name": "临床试验"},
            ]},
            {"id": "medical.bio", "name": "生物医学"},
            {"id": "medical.nutri", "name": "营养学"},
            {"id": "medical.psy", "name": "心理学", "children": [
                {"id": "medical.psy.counsel", "name": "心理咨询"},
                {"id": "medical.psy.clinical", "name": "临床心理"},
            ]},
            {"id": "medical.nursing", "name": "护理"},
        ]
    },
    {
        "id": "edu", "name": "教育/科研", "children": [
            {"id": "edu.teach", "name": "教师/培训", "children": [
                {"id": "edu.teach.k12", "name": "K12"},
                {"id": "edu.teach.langtrain", "name": "语言培训"},
                {"id": "edu.teach.skill", "name": "职业技能培训"},
            ]},
            {"id": "edu.lang", "name": "语言学习", "children": [
                {"id": "edu.lang.en", "name": "英语"},
                {"id": "edu.lang.jp", "name": "日语"},
                {"id": "edu.lang.kr", "name": "韩语"},
                {"id": "edu.lang.de", "name": "德语"},
            ]},
            {"id": "edu.sci", "name": "科研", "children": [
                {"id": "edu.sci.physics", "name": "物理学"},
                {"id": "edu.sci.chem", "name": "化学"},
                {"id": "edu.sci.bio", "name": "生物学"},
            ]},
            {"id": "edu.edu-tech", "name": "教育科技"},
        ]
    },
    {
        "id": "life", "name": "生活/兴趣", "children": [
            {"id": "life.sport", "name": "运动健身", "children": [
                {"id": "life.sport.run", "name": "跑步"},
                {"id": "life.sport.gym", "name": "健身"},
                {"id": "life.sport.ball", "name": "球类", "children": [
                    {"id": "life.sport.ball.basket", "name": "篮球"},
                    {"id": "life.sport.ball.foot", "name": "足球"},
                    {"id": "life.sport.ball.tennis", "name": "网球"},
                    {"id": "life.sport.ball.badminton", "name": "羽毛球"},
                ]},
                {"id": "life.sport.yoga", "name": "瑜伽"},
                {"id": "life.sport.swim", "name": "游泳"},
                {"id": "life.sport.cycling", "name": "骑行"},
            ]},
            {"id": "life.art", "name": "艺术文化", "children": [
                {"id": "life.art.music", "name": "音乐", "children": [
                    {"id": "life.art.music.play", "name": "乐器演奏"},
                    {"id": "life.art.music.sing", "name": "声乐"},
                ]},
                {"id": "life.art.film", "name": "电影"},
                {"id": "life.art.read", "name": "阅读"},
                {"id": "life.art.photo", "name": "摄影"},
                {"id": "life.art.paint", "name": "绘画"},
                {"id": "life.art.handcraft", "name": "手工"},
            ]},
            {"id": "life.food", "name": "美食", "children": [
                {"id": "life.food.cook", "name": "烹饪"},
                {"id": "life.food.bake", "name": "烘焙"},
                {"id": "life.food.taste", "name": "探店"},
                {"id": "life.food.wine", "name": "品酒"},
            ]},
            {"id": "life.travel", "name": "旅行", "children": [
                {"id": "life.travel.domestic", "name": "国内游"},
                {"id": "life.travel.abroad", "name": "出境游"},
                {"id": "life.travel.outdoor", "name": "户外/徒步"},
                {"id": "life.travel.photo", "name": "旅拍"},
            ]},
            {"id": "life.pet", "name": "宠物", "children": [
                {"id": "life.pet.dog", "name": "养狗"},
                {"id": "life.pet.cat", "name": "养猫"},
            ]},
            {"id": "life.game", "name": "游戏", "children": [
                {"id": "life.game.board", "name": "桌游"},
                {"id": "life.game.video", "name": "电子游戏"},
                {"id": "life.game.puzzle", "name": "解谜"},
            ]},
            {"id": "life.collect", "name": "收藏"},
        ]
    },
    {
        "id": "maker", "name": "制造/硬件", "children": [
            {"id": "maker.hardware", "name": "硬件工程师", "children": [
                {"id": "maker.hardware.pcb", "name": "PCB 设计"},
                {"id": "maker.hardware.fpga", "name": "FPGA"},
            ]},
            {"id": "maker.iot", "name": "物联网"},
            {"id": "maker.embed", "name": "嵌入式"},
            {"id": "maker.robot", "name": "机器人", "children": [
                {"id": "maker.robot.industrial", "name": "工业机器人"},
                {"id": "maker.robot.service", "name": "服务机器人"},
            ]},
            {"id": "maker.auto", "name": "汽车制造", "children": [
                {"id": "maker.auto.three", "name": "三电系统"},
                {"id": "maker.auto.ad", "name": "自动驾驶"},
            ]},
            {"id": "maker.semiconductor", "name": "半导体"},
        ]
    },
    {
        "id": "legal", "name": "法律/咨询", "children": [
            {"id": "legal.lawyer", "name": "律师", "children": [
                {"id": "legal.lawyer.civil", "name": "民事"},
                {"id": "legal.lawyer.criminal", "name": "刑事"},
                {"id": "legal.lawyer.corp", "name": "公司法务"},
            ]},
            {"id": "legal.consult", "name": "管理咨询", "children": [
                {"id": "legal.consult.strategy", "name": "战略咨询"},
                {"id": "legal.consult.it", "name": "IT 咨询"},
            ]},
            {"id": "legal.hr", "name": "人力资源", "children": [
                {"id": "legal.hr.recruit", "name": "招聘"},
                {"id": "legal.hr.train", "name": "培训发展"},
            ]},
        ]
    },
    {
        "id": "media", "name": "传媒/内容", "children": [
            {"id": "media.write", "name": "写作/编辑"},
            {"id": "media.video", "name": "视频制作", "children": [
                {"id": "media.video.cut", "name": "剪辑"},
                {"id": "media.video.live", "name": "直播"},
            ]},
            {"id": "media.ad", "name": "广告", "children": [
                {"id": "media.ad.copy", "name": "文案"},
                {"id": "media.ad.plan", "name": "策划"},
            ]},
            {"id": "media.pr", "name": "公关"},
        ]
    },
    {
        "id": "sales", "name": "销售/商务", "children": [
            {"id": "sales.b2b", "name": "B2B 销售"},
            {"id": "sales.b2c", "name": "零售销售"},
            {"id": "sales.bd", "name": "商务拓展"},
            {"id": "sales.ecom", "name": "电商", "children": [
                {"id": "sales.ecom.ops", "name": "电商运营"},
                {"id": "sales.ecom.live", "name": "直播带货"},
            ]},
        ]
    },
    {
        "id": "gov", "name": "公务员/事业单位", "children": [
            {"id": "gov.civil", "name": "公务员"},
            {"id": "gov.institution", "name": "事业单位"},
            {"id": "gov.army", "name": "军队文职"},
        ]
    },
    {
        "id": "agri", "name": "农业/环保", "children": [
            {"id": "agri.plant", "name": "种植"},
            {"id": "agri.breed", "name": "养殖"},
            {"id": "agri.env", "name": "环保/新能源", "children": [
                {"id": "agri.env.solar", "name": "光伏"},
                {"id": "agri.env.storage", "name": "储能"},
            ]},
        ]
    },
    {
        "id": "service", "name": "生活服务", "children": [
            {"id": "service.cater", "name": "餐饮", "children": [
                {"id": "service.cater.cook", "name": "厨师"},
                {"id": "service.cater.mgmt", "name": "餐饮管理"},
            ]},
            {"id": "service.beauty", "name": "美容/美发"},
            {"id": "service.logis", "name": "物流/仓储"},
            {"id": "service.realestate", "name": "房产/物业", "children": [
                {"id": "service.realestate.agent", "name": "房产经纪"},
                {"id": "service.realestate.prop", "name": "物业管理"},
            ]},
        ]
    },
]


# ============================================================
# 2. 外部职业分类 API 适配器 (可选, 供框架使用)
# ============================================================
# ExternalTaxonomyProvider 基类已迁移到 services/dimension_taxonomy,
# 此处仅保留 BOSS 风格的示例 provider (继承自框架基类)。

from services.dimension_taxonomy import ExternalTaxonomyProvider  # noqa: E402


# ---- 示例: BOSS 风格静态 provider (离线可用, 演示外部拉取) ----
class BossLikeProvider(ExternalTaxonomyProvider):
    """BOSS 直聘风格行业分类的离线示例。

    内置树未下沉到「岗位/技能」这一层的节点, 从这里继续细分。
    真实接入时, 可将此类的 fetch_children 改为请求 BOSS 开放接口
    (或任意职业分类 API), 返回相同结构的 list[dict] 即可。

    注意: 外部节点的 id 需带 `ext.` 前缀, 以与内置树区分,
    且 provider 需自行保证 id 在层级上可拼接 (parent_id 由引擎补全)。
    """

    # 末级职业方向 / 技能细分 (key=内置末级节点 id, value=更细叶子)
    _LEAVES = {
        "it.softeng.frontend.web.vue": [
            {"id": "ext.vue.vue3", "name": "Vue3 组合式 API"},
            {"id": "ext.vue.pinia", "name": "Pinia 状态管理"},
            {"id": "ext.vue.nuxt", "name": "Nuxt SSR"},
        ],
        "it.softeng.backend.lang.go": [
            {"id": "ext.go.gin", "name": "Gin 框架"},
            {"id": "ext.go.grpc", "name": "gRPC"},
            {"id": "ext.go.k8sop", "name": "Operator 开发"},
        ],
        "it.ai.llm": [
            {"id": "ext.llm.finetune", "name": "微调 (SFT)"},
            {"id": "ext.llm.rag", "name": "RAG 检索增强"},
            {"id": "ext.llm.eval", "name": "模型评测"},
        ],
        "finance.invest.quant": [
            {"id": "ext.quant.cta", "name": "CTA 策略"},
            {"id": "ext.quant.alpha", "name": "Alpha 因子"},
        ],
        "maker.robot": [
            {"id": "ext.robot.slam", "name": "SLAM 建图"},
            {"id": "ext.robot.control", "name": "运动控制"},
        ],
    }

    def reachable(self) -> bool:
        return True

    def fetch_children(self, node_id: str) -> list[dict]:
        leaves = self._LEAVES.get(node_id)
        if not leaves:
            return []
        return [{"id": d["id"], "name": d["name"], "has_children": False} for d in leaves]


# 环境变量 LIFEWB_EXTERNAL_TAXONOMY=1 时自动启用示例 provider:
import os  # noqa: E402
from services.dimension_taxonomy import register_external_provider  # noqa: E402
if os.getenv("LIFEWB_EXTERNAL_TAXONOMY") == "1":
    register_external_provider(BossLikeProvider())


# ============================================================
# 3. 派生 / 写回逻辑 (interests 维度)
# ============================================================
# 以下函数被注册进 dimension_taxonomy 框架, 作为 interests 维度的
# derive / apply 回调。保留在此模块以便与树定义同处。

def _build_all_index(custom: dict, ext_index: dict) -> dict:
    """合并内置树 + 自定义节点 + 外部节点, 返回 {id: {name,parent_id,path,depth}}"""
    from services.dimension_taxonomy import _index_tree
    all_index = _index_tree(WORLD_TREE)
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


def derive_interests(marks: dict, custom: dict, ext_index: dict | None = None) -> dict:
    """从标注节点派生兴趣路径 / 末梢 / 关键词

    每个节点可同时持有多种认知/关系状态 (6 态, 可叠加):
      like=关注/感兴趣  skill=擅长/有经验  know=知道/听说过(未参与)
      want=想了解  learning=在学/进行中  tried=已体验/经历过
      keywords:          所有已标节点的名字与路径词 (供引擎命中)
      skill_keywords:    仅 skill 节点的名字
      know_keywords:     仅 know 节点的名字
      want_keywords:     仅 want 节点的名字
      learning_keywords:仅 learning 节点的名字
      tried_keywords:    仅 tried 节点的名字
      leaves/paths:      每个节点的 mark 表示为 {state: bool, ...}
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

    for nid, m in marks.items():
        if not isinstance(m, dict):
            continue
        states = {s: bool(m.get(s)) for s in ("like", "skill", "know", "want", "learning", "tried")}
        if not any(states.values()):
            continue
        node = all_index.get(nid)
        if not node:
            continue
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

    # 同层负向推断: 大部分兄弟已标却漏标的节点 => 高置信度「不熟悉」
    sibling_gaps = compute_sibling_gaps("interests", marks, custom, ext_index)

    return {
        "paths": paths,
        "leaves": leaves,
        "keywords": sorted(keywords),
        "skill_keywords": sorted(skill_keywords),
        "know_keywords": sorted(know_keywords),
        "want_keywords": sorted(want_keywords),
        "learning_keywords": sorted(learning_keywords),
        "tried_keywords": sorted(tried_keywords),
        "sibling_gaps": sibling_gaps,
    }


def interest_ancestors(marks: dict, custom: dict, ext_index: dict | None = None) -> dict:
    """构建「已标节点 → 其祖先路径词」映射, 供推荐引擎做层级泛化匹配。

    返回: { "<节点名 lower>": ["父", "祖父", ...] }   # 祖先词, 不含自身
    """
    all_index = _build_all_index(custom, ext_index or {})
    result: dict[str, list[str]] = {}
    for nid, m in marks.items():
        if not isinstance(m, dict):
            continue
        if not any(m.get(s) for s in ("like", "skill", "know", "want", "learning", "tried")):
            continue
        node = all_index.get(nid)
        if not node:
            continue
        ancestors = [p.lower() for p in node["path"][:-1]]
        if ancestors:
            result[node["name"].lower()] = ancestors
    return result


def apply_interests(derived: dict, dim_data: dict) -> dict:
    """把派生关键词写回 interests.yaml 的 tracking_topics / skills / 认知状态字段。

    保留用户原有手填的其它字段; 此前派生项以 _derived 标记区分。
    """
    # tracking_topics 仅承载 like + skill (强信号),
    # 不再把 know/want/learning/tried 混入, 以免与强信号等权。
    like_or_skill_keywords = set(derived["keywords"]) - set(derived["know_keywords"]) \
        - set(derived["want_keywords"]) - set(derived["learning_keywords"]) \
        - set(derived["tried_keywords"])
    existing = dim_data.get("tracking_topics", [])
    existing = [t for t in existing if not (isinstance(t, dict) and t.get("_derived"))]
    derived_topics = [
        {"keyword": kw, "weight": 0.8, "_derived": True}
        for kw in sorted(like_or_skill_keywords)
    ]
    dim_data["tracking_topics"] = existing + derived_topics

    existing_skills = dim_data.get("skills", [])
    existing_skills = [s for s in existing_skills if not (isinstance(s, dict) and s.get("_derived"))]
    derived_skills = [
        {"name": kw, "level": 4, "category": "derived", "_derived": True}
        for kw in derived["skill_keywords"]
    ]
    dim_data["skills"] = existing_skills + derived_skills

    # 认知/关系状态 (弱信号): 各状态独立字段, 供引擎差异化加权。
    # know=知道(最低) want=想了解(较低) learning=在学(中低) tried=已体验(中)
    for field, key, w in (
        ("know_of", "know_keywords", 0.3),
        ("want_to_learn", "want_keywords", 0.45),
        ("learning", "learning_keywords", 0.6),
        ("tried", "tried_keywords", 0.7),
    ):
        existing_f = dim_data.get(field, [])
        existing_f = [x for x in existing_f if not (isinstance(x, dict) and x.get("_derived"))]
        dim_data[field] = existing_f + [
            {"keyword": kw, "weight": w, "_derived": True} for kw in derived.get(key, [])
        ]
    return dim_data


# ============================================================
# 4. 注册 interests 维度到通用框架
# ============================================================
from services.dimension_taxonomy import register_dimension  # noqa: E402

register_dimension("interests", {
    "name": "兴趣与技能",
    "tree": WORLD_TREE,
    "mark_file": "interest_map.yaml",
    "target_dim": "interests",
    "provider": BossLikeProvider() if os.getenv("LIFEWB_EXTERNAL_TAXONOMY") == "1" else None,
    "derive": derive_interests,
    "apply": apply_interests,
})

