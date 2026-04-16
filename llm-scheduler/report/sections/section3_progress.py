"""（三）项目进展情况（重点）"""
from report.styles import (
    add_section_heading, add_subheading, add_body, add_body_with_cite,
    add_table, add_figure,
)


def add_section3(doc):
    add_section_heading(doc, "（三）项目进展情况")

    # ── 1. 已完成的工作 ────────────────────────────────────────────────────────
    add_subheading(doc, "1. 已完成的工作")

    add_body(doc,
        "目前已完成系统的整体设计与核心功能开发，包括后端服务、前端界面、容器化部署和"
        "监控体系四个层面的工作。系统采用微服务架构，包含Gateway（8080端口）、Scheduler"
        "（8001端口）、Inference Node（8003/8004/8007端口）和Monitoring（8002端口）"
        "四个核心服务。各服务独立部署，通过RESTful API通信，使用内部Token进行服务间认证。"
        "系统数据流为：用户请求→Gateway认证→Scheduler选节点→Inference Node代理vLLM推理"
        "→返回响应。"
    )

    # 调度策略引擎
    add_body(doc,
        "实现了基于策略模式（Strategy Pattern）的调度引擎，设计了抽象基类"
        "SchedulingStrategy，并实现了三种具体策略：（1）RoundRobinStrategy使用"
        "itertools.count()原子计数器实现轮询分配，时间复杂度O(1)；（2）"
        "LeastConnectionsStrategy通过min(nodes, key=active_connections)选择负载最轻"
        "的节点；（3）WeightedRoundRobinStrategy采用random.choices()进行加权随机选择，"
        "设置最小权重阈值0.001避免除零错误。策略管理器（manager.py）维护全局策略实例，"
        "通过set_strategy()函数实现运行时热切换，当前策略配置持久化至SQLite数据库，"
        "服务重启后自动恢复。"
    )

    add_figure(doc, caption="图2 调度策略引擎UML类图", desc="策略模式类图")

    # API网关
    add_body(doc,
        "网关服务实现了完整的认证与请求路由体系。认证方面，采用JWT+bcrypt方案，"
        "HS256算法签名，Token有效期60分钟，支持admin/user两级RBAC角色权限控制，"
        "并通过RoleChecker依赖注入实现接口级鉴权。用户管理方面，实现了用户注册、登录、"
        "激活/停用、密码修改等完整CRUD功能，管理员可查看和管理所有用户。请求转发方面，"
        "实现了智能重试机制：最大重试3次，仅对502/503/504状态码触发重试，采用指数退避"
        "策略（等待时间0.1×2^attempt秒），维护节点排除列表避免重复转发到故障节点。"
        "此外，实现了\"auto\"模型名自动解析，网关在转发请求前从目标节点/v1/models端点"
        "获取实际可用模型名，对用户屏蔽底层差异。"
    )

    # 推理节点
    add_body(doc,
        "推理节点服务实现了vLLM HTTP反向代理，支持模型名首次查询后缓存、180秒推理超时、"
        "异步安全的活跃连接计数器。节点启动时自动向Scheduler发送POST /api/nodes/register"
        "完成自注册，注册过程采用指数退避重试（最多10次，最大等待30秒）。注册成功后以"
        "10秒间隔发送心跳，上报active_connections、status、gpu_util、memory_used_gb等"
        "状态信息。Scheduler端维护异步安全的NodeRegistry，后台任务每5秒扫描，30秒无心跳"
        "则标记为unhealthy，支持healthy/unhealthy/draining三种节点状态。"
    )

    add_table(doc,
        caption="表1 核心服务功能一览表",
        headers=["服务", "端口", "核心功能"],
        rows=[
            ["Gateway", "8080", "JWT认证、请求路由、重试转发、用户管理"],
            ["Scheduler", "8001", "节点注册、策略调度、心跳监测"],
            ["Inference Node", "8003/8004/8007", "vLLM代理、心跳上报、连接计数"],
            ["Monitoring", "8002", "指标采集(15s)、告警引擎、时序聚合"],
        ],
    )

    # 监控告警
    add_body(doc,
        "监控服务实现了完整的指标采集与告警体系。指标采集器以15秒间隔从各服务/metrics/json"
        "端点拉取QPS、延迟（p50/p95）、成功率、活跃连接数、GPU利用率等关键指标，支持从"
        "Scheduler动态发现新增节点。告警引擎支持基于规则的告警配置，每条规则包含metric、"
        "operator（gt/lt/eq）、threshold和window_s四个维度，采用滑动窗口聚合和去重触发"
        "机制避免重复告警。时序数据按分钟分桶聚合存储，提供15m/1h/6h/24h/7d五种查询范围。"
        "此外，在deploy/目录中配置了Prometheus+Grafana监控栈，包含预配置的数据源和仪表盘，"
        "可通过docker compose一键启动，为系统提供更专业的可视化监控能力。"
    )

    # 容器化部署
    add_body(doc,
        "完成了完整的容器化部署方案。Docker Compose编排包含5个服务定义，使用桥接网络"
        "llm-net实现服务间通信，命名卷持久化数据。每个服务配置了健康检查（10秒间隔、"
        "5秒超时、5次重试）和依赖关系，确保启动顺序正确。推理节点通过host.docker.internal"
        "访问宿主机vLLM实例。采用多阶段Dockerfile：第一阶段使用Node.js 20 Alpine构建"
        "Vue.js前端，第二阶段使用Python 3.11 Slim运行FastAPI服务，构建产物嵌入静态目录。"
        "开发了start_local.py本地启动脚本，支持端口冲突检测、Windows GBK编码兼容和一键"
        "启动6个服务进程（含3个推理节点，分别部署Qwen3-0.6B、TinyLlama-1.1B和远程"
        "Qwen2.5-7B模型）。"
    )

    # 前端界面
    add_body(doc,
        "完成了4套独立的Vue.js 3 + Element Plus管理界面，采用暗色主题和SPA架构，"
        "构建产物嵌入各服务的FastAPI静态目录，通过SPA fallback路由实现前端路由。"
        "Gateway前端包含Chat交互界面（支持温度、最大token、top-p参数调节）、请求历史"
        "查看、管理员用户管理；Scheduler前端包含节点注册/注销管理、策略热切换配置、"
        "调度日志查看；Monitoring前端包含实时仪表盘（QPS/延迟/成功率KPI）、历史趋势图、"
        "节点性能对比、告警规则管理；Inference Node前端包含本地模型测试、模型信息查看、"
        "请求日志与统计。"
    )

    # 测试工具
    add_body(doc,
        "开发了完善的测试与基准测试工具。端到端测试脚本（test_e2e.py）覆盖8项功能测试，"
        "包括健康检查、用户注册登录、推理请求、历史隔离、管理员权限、授权校验和节点列表"
        "查询。基准测试脚本（benchmark.py）支持并发负载测试和策略对比实验，可配置请求"
        "数量和并发批次，采集延迟统计（平均/最大/最小）、token吞吐量、成功率、节点分配"
        "分布等关键指标，并输出彩色统计报告。"
    )

    # ── 2. 遇到的困难与解决方案 ────────────────────────────────────────────────
    add_subheading(doc, "2. 遇到的困难与解决方案")

    add_body(doc,
        "（1）vLLM模型名不一致问题：不同推理节点部署的模型不同（Qwen3-0.6B、"
        "TinyLlama-1.1B、Qwen2.5-7B），用户无法预先知道目标节点支持哪个模型。"
        "解决方案：在Gateway的retry.py中实现\\\"auto\\\"模型自动解析，网关在转发请求前"
        "从目标节点GET /api/model获取实际模型名并替换payload中的model字段，"
        "对用户完全屏蔽底层差异。"
    )

    add_body(doc,
        "（2）节点故障检测的灵敏度与误判矛盾：初始方案使用固定频率心跳检测，"
        "在网络短暂波动时容易产生误判将健康节点标记为不可用。解决方案：引入TTL机制"
        "（30秒超时阈值），将检测间隔（5秒扫描）与判定阈值解耦；同时推理节点自注册"
        "采用指数退避重试（最多10次），网络恢复后可自动重新注册，平衡了检测灵敏度"
        "和容错能力。"
    )

    add_body(doc,
        "（3）策略切换导致服务中断：早期设计中切换调度策略需要重启Scheduler服务。"
        "解决方案：采用策略模式（Strategy Pattern）重构调度引擎，通过全局变量和"
        "set_strategy()函数实现运行时热切换，策略选择通过管理员API即时生效，"
        "同时将策略配置持久化到SQLite数据库，服务重启后自动恢复上次选择的策略。"
    )

    add_body(doc,
        "（4）前端与后端的集成部署：各服务前端独立构建，需要与FastAPI后端无缝集成。"
        "解决方案：采用多阶段Dockerfile，第一阶段在Node.js环境构建Vue.js前端产物，"
        "第二阶段将构建结果复制到Python运行时镜像的/static目录，FastAPI通过StaticFiles"
        "中间件和SPA fallback路由提供前端服务，实现了前后端的一体化部署。"
    )

    # ── 3. 下一步工作计划 ──────────────────────────────────────────────────────
    add_subheading(doc, "3. 下一步工作计划")

    add_body(doc,
        "（1）实现SSE（Server-Sent Events）流式推理支持，使模型能够逐token输出中间"
        "结果，提升用户交互体验，降低首token响应时间。"
    )

    add_body(doc,
        "（2）开发GPU感知调度策略，基于GPU利用率、显存使用率和KV Cache占用率进行"
        "智能调度决策，避免将请求分配到资源紧张的节点。"
    )

    add_body(doc,
        "（3）集成OpenTelemetry分布式追踪，实现从Gateway到Inference Node的全链路"
        "请求追踪和性能瓶颈分析。"
    )

    add_body(doc,
        "（4）实现基于负载指标的弹性伸缩机制，当GPU利用率超过阈值时自动扩容推理节点，"
        "低负载时自动缩容以节约资源。"
    )

    add_body(doc,
        "（5）完善性能测试与压力测试，使用benchmark.py采集三种策略在不同并发度下的"
        "真实实验数据，撰写完整的实验分析章节。"
    )
