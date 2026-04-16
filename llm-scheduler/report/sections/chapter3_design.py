"""Chapter 3: System Design section for Chinese academic mid-term report."""

from report.styles import (
    add_heading1, add_heading2, add_heading3, add_body_text,
    add_table, add_figure_placeholder, add_page_break,
)


def add_chapter3(doc):
    """Add Chapter 3 - System Overall Design to the document."""

    add_heading1(doc, "第三章 系统总体设计")

    # ── 3.1 系统需求分析 ────────────────────────────────────────────────────────
    add_heading2(doc, "3.1 系统需求分析")

    add_heading3(doc, "3.1.1 功能需求")
    add_body_text(doc,
        "通过对大语言模型分布式推理场景的深入分析，本系统需要满足以下功能需求："
    )
    add_body_text(doc,
        "（1）多用户认证与权限管理。系统需提供用户注册与登录功能，采用JWT令牌机制实现"
        "无状态身份认证，密码存储使用bcrypt哈希算法保障安全。系统支持admin和user两级角色"
        "权限体系，管理员可执行用户管理、策略配置等特权操作，普通用户仅能使用推理服务和"
        "查看个人请求历史。"
    )
    add_body_text(doc,
        "（2）LLM推理请求代理。系统需提供与OpenAI兼容的标准化推理接口（/v1/chat/completions），"
        "支持对话补全请求的接收、转发与响应。推理节点通过代理模式对接后端vLLM推理引擎，"
        "实现对不同规模大语言模型的统一调用。"
    )
    add_body_text(doc,
        "（3）推理节点管理。系统需支持推理节点的动态注册与注销，节点启动后自动向调度器"
        "注册其地址、端口和权重信息。运行过程中，节点以固定间隔发送心跳包上报活跃连接数、"
        "GPU利用率等状态信息，调度器据此维护实时节点状态表。"
    )
    add_body_text(doc,
        "（4）负载均衡调度。系统需提供多种可切换的负载均衡策略，包括轮询（Round Robin）、"
        "最少连接（Least Connections）和加权轮询（Weighted Round Robin），支持运行时"
        "策略热切换，满足不同负载场景下的调度需求。"
    )
    add_body_text(doc,
        "（5）监控与告警。系统需实时采集推理延迟、请求吞吐量、错误率、GPU利用率等关键"
        "性能指标，以15秒为间隔进行周期性采集，并提供可视化展示界面。同时构建可配置的"
        "告警规则引擎，支持基于阈值的告警触发与事件记录。"
    )

    add_heading3(doc, "3.1.2 非功能需求")
    add_body_text(doc,
        "除功能需求外，系统还需满足以下非功能需求：高可用性方面，系统需具备节点故障自动"
        "检测与请求转移能力，当某个推理节点异常时，调度器能自动将其排除并重新分配请求；"
        "低延迟方面，调度决策应在毫秒级内完成，避免引入显著的额外延迟开销；可扩展性方面，"
        "系统应支持推理节点的动态增删，无需重启即可将新节点纳入调度；容错性方面，API网关"
        "需实现请求重试机制与指数退避策略，在推理节点短暂不可用时自动重试，保障请求的"
        "最终成功。"
    )

    # ── 3.2 总体架构设计 ────────────────────────────────────────────────────────
    add_heading2(doc, "3.2 总体架构设计")

    add_body_text(doc,
        "本系统采用微服务架构进行设计，将整体功能拆分为四个核心服务和一组共享模块，各服务"
        "独立部署、独立运行，通过RESTful HTTP协议进行通信，服务间使用内部Token进行身份验证。"
        "总体架构由以下组件构成："
    )
    add_body_text(doc,
        "（1）Gateway服务（端口8080）：作为系统的API网关和统一入口，负责接收外部客户端请求，"
        "执行JWT身份认证与权限校验，并根据请求路径将请求路由至对应的后端服务。同时，网关"
        "实现了请求重试机制与指数退避策略，保障请求的可靠转发。"
    )
    add_body_text(doc,
        "（2）Scheduler服务（端口8001）：作为集中式调度中心，维护推理节点的注册表与实时"
        "状态信息，管理多种负载均衡策略的执行与热切换。调度器接收来自网关的调度请求，"
        "根据当前策略和节点状态选出最优节点返回给网关。"
    )
    add_body_text(doc,
        "（3）Inference Node服务（端口8003/8004/8007）：作为推理代理节点，以代理模式对接"
        "后端vLLM推理引擎。每个节点负责将收到的推理请求转发至本地或远程的vLLM实例，"
        "并将推理结果返回给调用方。节点定期向调度器发送心跳包上报状态信息。"
    )
    add_body_text(doc,
        "（4）Monitoring服务（端口8002）：负责系统运行状态的实时监控，以15秒为间隔周期性"
        "采集各节点和服务的性能指标，构建告警规则引擎，当指标超过预设阈值时触发告警事件。"
    )
    add_body_text(doc,
        "（5）Shared共享模块：包含20余个Pydantic数据模型定义，作为各服务间数据交换的统一"
        "规范，涵盖认证、推理、调度、监控和健康检查等领域的完整数据结构。"
    )

    add_figure_placeholder(doc, "图3-1 系统总体架构图",
        "系统总体架构图：展示Gateway、Scheduler、Inference Node、Monitoring四个核心服务"
        "及Shared共享模块的组件关系与交互方式")

    add_body_text(doc,
        "系统数据流遵循以下路径：客户端发起请求至Gateway，Gateway完成JWT认证后向Scheduler"
        "发送调度请求，Scheduler根据当前策略选择最优推理节点并返回节点地址，Gateway将推理"
        "请求转发至选定的Inference Node，Inference Node代理请求至后端vLLM引擎完成推理，"
        "推理结果沿原路返回至客户端。Monitoring服务独立采集各节点指标并执行告警检测。"
    )

    add_figure_placeholder(doc, "图3-2 系统数据流图",
        "系统数据流图：展示请求从客户端经Gateway认证、Scheduler调度、Inference Node代理"
        "至vLLM推理引擎的完整数据流转过程")

    # ── 3.3 数据模型设计 ────────────────────────────────────────────────────────
    add_heading2(doc, "3.3 数据模型设计")

    add_body_text(doc,
        "本系统的数据模型基于Pydantic BaseModel定义，集中存放于shared/models.py模块中，"
        "共包含20余个数据模型，按功能域划分为以下五类："
    )
    add_body_text(doc,
        "（1）认证域（Auth）：包含LoginRequest（登录请求）、RegisterRequest（注册请求）、"
        "TokenResponse（令牌响应，含access_token、token_type、role字段）和UserInfo"
        "（用户信息，含id、username、role、is_active、created_at、last_login字段）四个"
        "数据模型，用于用户身份认证与信息管理。"
    )
    add_body_text(doc,
        "（2）推理域（Inference）：包含ChatCompletionRequest（对话补全请求，含model、"
        "messages、temperature、max_tokens、stream等字段）、ChatCompletionResponse"
        "（对话补全响应，含choices和usage字段）以及Usage（令牌使用量统计）等模型，"
        "定义了与OpenAI兼容的推理接口数据格式。"
    )
    add_body_text(doc,
        "（3）调度域（Scheduler）：包含NodeInfo（节点信息，含node_id、host、port、weight、"
        "status、active_connections等字段）、ScheduleRequest/Response（调度请求与响应，"
        "响应含selected_node、algorithm_used、decision_latency_ms字段）、StrategyInfo"
        "（策略信息）和SchedulingLogEntry（调度日志条目）等模型。"
    )
    add_body_text(doc,
        "（4）监控域（Monitoring）：包含MetricsSummary（指标摘要，含qps、avg_latency_ms、"
        "p95_latency_ms、success_rate等字段）、NodeStats（节点统计）、AlertRule（告警规则，"
        "含metric、operator、threshold、window_s等字段）和AlertEvent（告警事件，含"
        "triggered_value、message、resolved、fired_at等字段）等模型。"
    )
    add_body_text(doc,
        "（5）健康检查域（Health）：包含HealthResponse（健康响应，含status和version字段）、"
        "NodeHealthResponse（节点健康响应，含vllm_reachable、model_id等字段）和MetricsJson"
        "（指标JSON格式，供监控服务采集）等模型。"
    )

    add_figure_placeholder(doc, "图3-3 数据模型ER图",
        "数据模型ER图：展示认证域、推理域、调度域、监控域和健康检查域共20余个Pydantic"
        "数据模型之间的关联关系")

    add_body_text(doc,
        "在持久化存储方面，各服务使用独立的SQLite数据库，通过命名卷实现数据持久化。"
        "Gateway服务维护users表（用户信息）和request_log表（请求日志）；Scheduler服务"
        "维护nodes表（节点注册信息）、scheduling_log表（调度日志）和strategy_config表"
        "（策略配置）；Monitoring服务维护metrics_snapshot表（指标快照）、alert_rules表"
        "（告警规则）和alert_history表（告警历史）；各Inference Node维护request_log表"
        "（推理请求日志）和metrics_1m表（一分钟粒度指标数据）。"
    )

    # ── 3.4 部署架构设计 ────────────────────────────────────────────────────────
    add_heading2(doc, "3.4 部署架构设计")

    add_body_text(doc,
        "本系统采用Docker Compose进行容器编排，通过docker-compose.yml配置文件统一管理"
        "五个服务容器的构建、网络、存储和依赖关系。部署架构的核心设计包括以下方面："
    )
    add_body_text(doc,
        "（1）网络设计：创建桥接网络llm-net，所有服务容器均接入该网络，通过容器名进行"
        "服务发现与通信。推理节点通过host.docker.internal特殊域名访问宿主机上运行的vLLM"
        "推理引擎，实现容器与宿主机的网络互通。"
    )
    add_body_text(doc,
        "（2）数据持久化：为每个服务创建独立的命名卷（gateway-data、scheduler-data、"
        "monitoring-data、node1-data、node2-data），将SQLite数据库文件存储在命名卷中，"
        "确保容器重建后数据不丢失。"
    )
    add_body_text(doc,
        "（3）健康检查：各服务配置了健康检查机制，检查间隔为10秒，超时时间为5秒，连续"
        "失败5次后标记为不健康。服务间通过depends_on和condition: service_healthy声明"
        "启动依赖关系，确保Scheduler先于Gateway启动，Gateway先于Monitoring启动，保证"
        "服务的正确初始化顺序。"
    )
    add_body_text(doc,
        "（4）多阶段构建：各服务采用多阶段Dockerfile进行镜像构建。第一阶段基于Node.js 20"
        "Alpine镜像构建Vue.js前端资源；第二阶段基于Python 3.11 Slim镜像运行FastAPI后端"
        "服务，将前端构建产物复制到后端镜像中，实现前后端一体化部署。"
    )
    add_body_text(doc,
        "（5）本地开发模式：提供start_local.py一键启动脚本，以子进程方式依次启动6个服务"
        "（Scheduler、Inference Node x3、Gateway、Monitoring），设置PYTHONPATH共享"
        "模块路径，支持带热重载的开发调试。脚本还包含端口冲突检测功能，启动前自动检查"
        "所需端口是否已被占用。"
    )

    add_figure_placeholder(doc, "图3-4 Docker部署架构图",
        "Docker部署架构图：展示五个服务容器、桥接网络llm-net、命名卷持久化存储、"
        "健康检查依赖关系及宿主机vLLM引擎的连接方式")

    add_table(
        doc,
        headers=["服务", "端口", "功能"],
        rows=[
            ["Gateway", "8080", "API网关，用户认证，请求路由"],
            ["Scheduler", "8001", "节点调度，策略管理"],
            ["Monitoring", "8002", "指标采集，告警管理"],
            ["Inference Node 1", "8003", "推理代理（Qwen3-0.6B）"],
            ["Inference Node 2", "8004", "推理代理（TinyLlama-1.1B）"],
            ["Inference Node 3", "8007", "推理代理（Qwen2.5-7B Remote）"],
        ],
        caption="表3-1 服务端口与功能对照表",
    )

    add_page_break(doc)
