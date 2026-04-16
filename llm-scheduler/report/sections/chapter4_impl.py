"""Chapter 4 — Key Technical Implementation (关键技术实现)."""

from report.styles import (
    add_heading1,
    add_heading2,
    add_heading3,
    add_body_text,
    add_figure_placeholder,
    add_page_break,
)


def add_chapter4(doc):
    """Add Chapter 4: Key Technical Implementation."""

    # ═══════════════════════════════════════════════════════════════════════════
    add_heading1(doc, "第四章 关键技术实现")

    add_body_text(doc,
        "本章基于第三章所述的系统总体设计方案，详细阐述LLM云原生分布式推理调度引擎"
        "各核心模块的具体技术实现。系统采用Python语言开发，基于FastAPI框架构建RESTful"
        "微服务，各服务间通过HTTP协议通信，使用SQLite作为轻量级嵌入式数据库实现数据"
        "持久化。以下从API网关层、调度策略引擎、推理节点代理、节点注册与心跳机制、"
        "监控告警系统以及前端可视化六个方面展开论述。"
    )

    # ── 4.1 API Gateway ─────────────────────────────────────────────────────
    add_heading2(doc, "4.1 API网关层实现")

    add_body_text(doc,
        "API网关作为系统的统一请求入口，承担身份认证、请求路由、负载代理与容错重试等"
        "核心职责。本节从JWT认证体系、请求路由转发、重试容错机制以及RBAC权限控制四个"
        "方面阐述其具体实现。"
    )

    # 4.1.1 JWT Authentication
    add_heading3(doc, "4.1.1 JWT认证体系")

    add_body_text(doc,
        "系统采用基于JSON Web Token（JWT）的无状态认证方案，使用HS256（HMAC-SHA256）"
        "对称加密算法签发令牌，Token有效期为60分钟。认证模块（gateway/app/auth.py，82行）"
        "基于python-jose库实现JWT的编码与解码，利用passlib库的CryptContext组件集成bcrypt"
        "自适应哈希算法对用户密码进行安全存储。bcrypt算法内置盐值（salt）生成机制，"
        "其计算成本因子可调节，有效抵御暴力破解与彩虹表攻击。"
    )

    add_body_text(doc,
        "认证流程如下：用户通过POST /auth/login接口提交用户名与密码，系统验证凭据后"
        "调用create_access_token()函数签发JWT令牌，载荷（payload）中包含用户标识（sub字段）"
        "与过期时间（exp字段）。后续请求通过OAuth2PasswordBearer依赖注入自动提取Bearer"
        "令牌，经decode_token()函数验证签名与有效期后，从数据库查询用户完整信息并注入"
        "请求上下文。该设计将认证逻辑与业务逻辑彻底解耦，通过FastAPI的Depends依赖注入"
        "机制实现声明式的权限校验。"
    )

    add_figure_placeholder(doc,
        "图4-1 JWT认证流程图",
        "JWT认证时序图：用户登录 -> 密码验证 -> Token签发 -> 请求携带Token -> 网关验证签名与有效期 -> 转发至后端服务"
    )

    # 4.1.2 Request Routing
    add_heading3(doc, "4.1.2 请求路由与转发")

    add_body_text(doc,
        "网关的核心路由端点为POST /v1/chat/completions（gateway/app/routers/inference.py，"
        "88行），兼容OpenAI API标准接口规范。该端点的处理流程分为三个阶段：首先，接收"
        "请求后为每个请求分配UUID标识符，将请求元数据（用户信息、模型名称、消息内容）"
        "以'pending'状态写入request_log数据表，实现请求的全生命周期追踪；其次，调用"
        "retry模块的forward_with_retry()函数，由调度器选择目标推理节点并转发请求；"
        "最后，在finally块中更新请求日志的状态、响应内容、延迟时间、Token用量等字段，"
        "确保无论请求成功或失败均能记录完整的执行信息。"
    )

    add_body_text(doc,
        "系统采用共享上下文计时器（shared.utils.timer）精确测量每次推理请求的端到端延迟，"
        "该计时器基于上下文管理器协议实现，以毫秒级精度记录从请求转发到响应返回的时间"
        "跨度，为后续性能分析与监控告警提供数据支撑。"
    )

    # 4.1.3 Retry Mechanism
    add_heading3(doc, "4.1.3 指数退避重试机制")

    add_body_text(doc,
        "重试容错模块（gateway/app/retry.py，84行）实现了带节点排除的指数退避重试策略，"
        "是保障系统高可用性的关键机制。该模块定义了两个核心常量：MAX_RETRIES = 3设定最大"
        "重试次数为3次，RETRY_STATUS = {502, 503, 504}限定仅对网关错误、服务不可用及"
        "网关超时三类状态码触发重试，避免对客户端错误（4xx）进行无意义重试。"
    )

    add_body_text(doc,
        "重试流程的具体实现如下：维护一个tried列表累积已失败的节点标识，每次重试前通过"
        "调用调度器的POST /api/schedule接口，将tried列表作为exclude_nodes参数传入，使调度器"
        "在候选节点中排除已失败节点，从而实现故障转移。退避等待时间采用指数增长策略，"
        "计算公式为wait = 0.1 * (2 ** attempt)，即三次重试的等待时间分别为0.1秒、0.2秒和"
        "0.4秒，在快速重试与避免请求风暴之间取得平衡。"
    )

    add_body_text(doc,
        "此外，该模块还实现了'auto'模型的自动解析功能。当用户请求中模型名称指定为'auto'、"
        "空字符串或None时，系统自动向目标推理节点发送GET /api/model请求，从vLLM实例获取"
        "当前加载的可用模型列表，并使用首个可用模型的标识符替换原始请求中的模型名称。"
        "这一设计使用户无需关心底层模型部署细节，极大地简化了客户端接入流程。"
    )

    add_figure_placeholder(doc,
        "图4-2 指数退避重试与故障转移流程图",
        "重试流程图：请求到达网关 -> 调度器选节点(exclude tried) -> 转发至推理节点 -> 成功则返回 / 失败则加入tried列表 -> 指数退避等待 -> 重试(MAX 3次) -> 全部失败则抛出异常"
    )

    # 4.1.4 RBAC
    add_heading3(doc, "4.1.4 基于角色的访问控制")

    add_body_text(doc,
        "系统实现了admin与user两级角色的基于角色访问控制（RBAC）机制。RoleChecker类"
        "（gateway/app/auth.py，65-77行）采用FastAPI的Depends依赖注入模式，作为可调用"
        "对象（Callable）注入路由处理函数。该类在初始化时接收允许的角色列表，在请求"
        "处理时自动校验当前用户角色是否在允许范围内，若权限不足则返回HTTP 403状态码。"
        "系统预定义了两个权限守卫：require_admin仅允许管理员角色访问，用于用户管理等"
        "敏感操作；require_any允许所有已认证用户访问，用于常规推理请求。该设计遵循"
        "最小权限原则，确保不同角色只能访问其权限范围内的功能。"
    )

    # ── 4.2 Scheduling Strategy Engine ──────────────────────────────────────
    add_heading2(doc, "4.2 调度策略引擎实现")

    add_body_text(doc,
        "调度策略引擎是系统负载均衡能力的核心实现，采用经典策略模式（Strategy Pattern）"
        "架构，通过抽象基类定义统一接口，多种调度策略以独立子类形式实现，管理器负责"
        "策略的注册与热切换。该设计遵循开闭原则（Open/Closed Principle），新增调度策略"
        "仅需添加新的策略子类并在管理器中注册，无需修改已有代码。"
    )

    add_heading3(doc, "4.2.1 策略抽象基类")

    add_body_text(doc,
        "抽象基类SchedulingStrategy（scheduler/app/strategies/base.py，14行）继承自"
        "Python标准库的ABC（Abstract Base Class），定义了所有调度策略必须实现的pick()"
        "异步方法接口。该方法接收健康的候选节点列表作为参数，返回被选中的单个节点。"
        "基类还声明了name类属性，用于策略的标识与注册。该抽象化设计确保了上层调度逻辑"
        "与具体策略实现的解耦，调度器无需感知策略的内部实现细节。"
    )

    add_heading3(doc, "4.2.2 轮询策略")

    add_body_text(doc,
        "轮询策略RoundRobinStrategy（scheduler/app/strategies/round_robin.py，17行）采用"
        "经典的轮询算法实现请求的均匀分配。该策略利用Python标准库itertools.count()创建"
        "一个原子递增计数器，每次调用pick()方法时，对计数器值取模节点列表长度，依次选择"
        "节点。itertools.count()返回的计数器对象在CPython实现中为不可变对象，天然具有"
        "线程安全性，适用于并发请求场景下的无锁轮询选择。该策略假设所有节点的处理能力"
        "均等，适用于节点硬件配置一致的同构集群环境。"
    )

    add_heading3(doc, "4.2.3 最少连接策略")

    add_body_text(doc,
        "最少连接策略LeastConnectionsStrategy（scheduler/app/strategies/least_connections.py，"
        "13行）基于当前活跃连接数动态选择负载最轻的节点。该策略在pick()方法中调用Python"
        "内置的min()函数，以每个节点的active_connections属性作为排序键，选择当前活跃连接"
        "数最少的节点。相较于轮询策略，最少连接策略能够感知节点的实时负载差异，在请求"
        "处理时间不均匀或节点性能异构的场景下实现更优的负载分配效果。"
    )

    add_heading3(doc, "4.2.4 加权轮询策略")

    add_body_text(doc,
        "加权轮询策略WeightedRoundRobinStrategy（scheduler/app/strategies/weighted.py，15行）"
        "引入节点权重概念，支持按权重比例进行概率性选择。该策略使用Python标准库"
        "random.choices()函数实现加权随机采样，权重值源自节点注册时设定的weight属性。"
        "为避免权重为零导致的选择异常，对权重值施加最小下限约束max(weight, 0.001)。"
        "该策略适用于节点硬件配置差异较大的异构集群，管理员可根据各节点的GPU算力与显存"
        "容量动态调整权重，使高性能节点承担更多推理请求。"
    )

    add_heading3(doc, "4.2.5 策略管理器与热切换")

    add_body_text(doc,
        "策略管理器（scheduler/app/strategies/manager.py，25行）以STRATEGIES字典维护"
        "策略名称到策略类的映射关系，支持round_robin、least_connections、weighted三种"
        "策略的动态注册。管理器维护一个模块级全局变量_active持有当前激活的策略实例，"
        "通过set_strategy()函数实现策略的运行时热切换。当管理员通过Web界面更改调度策略时，"
        "set_strategy()函数根据策略名称实例化对应的策略对象并替换_active引用，后续的"
        "调度请求立即使用新策略，无需重启服务。"
    )

    add_body_text(doc,
        "此外，调度器启动时从SQLite数据库的strategy_config数据表中恢复上次的策略选择"
        "（scheduler/app/main.py，25-31行），实现策略配置的持久化与断电恢复。该机制确保"
        "服务重启后能够自动恢复管理员设定的调度策略，避免配置丢失。"
    )

    add_figure_placeholder(doc,
        "图4-3 调度策略引擎UML类图",
        "策略模式类图：SchedulingStrategy(ABC) <- RoundRobinStrategy / LeastConnectionsStrategy / WeightedRoundRobinStrategy；Manager通过STRATEGIES字典管理策略实例，get_strategy()返回当前策略，set_strategy()热切换"
    )

    # ── 4.3 Inference Node Proxy ────────────────────────────────────────────
    add_heading2(doc, "4.3 推理节点代理实现")

    add_body_text(doc,
        "推理节点代理服务作为本地vLLM推理引擎的薄封装层，负责请求转发、连接计数与模型"
        "信息管理。代理服务通过httpx异步HTTP客户端与本地运行的vLLM实例通信，将外部推理"
        "请求透传至vLLM的OpenAI兼容接口，并补充连接跟踪与健康检查等运维能力。"
    )

    add_heading3(doc, "4.3.1 vLLM HTTP代理与模型缓存")

    add_body_text(doc,
        "vLLM客户端模块（inference-node/app/vllm_client.py，59行）实现了对本地vLLM实例"
        "的HTTP代理封装。核心函数forward_chat_completion()将聊天补全请求转发至vLLM的"
        "/v1/chat/completions端点，设置180秒的推理超时时间，适配大语言模型长文本生成"
        "场景下的延迟特征。"
    )

    add_body_text(doc,
        "为避免高并发场景下反复查询vLLM模型列表带来的性能开销，该模块实现了模型名称"
        "缓存机制。首次调用_get_actual_model()时，通过GET /v1/models获取vLLM当前加载的"
        "模型列表并缓存首个模型标识符至模块级变量_cached_model，后续调用直接返回缓存值，"
        "省去HTTP请求开销。该缓存策略基于vLLM实例运行期间模型配置不变的假设，在模型热"
        "更新场景下需重启推理节点以刷新缓存。"
    )

    add_heading3(doc, "4.3.2 异步连接计数器")

    add_body_text(doc,
        "推理节点实现了基于asyncio.Lock的异步安全连接计数器_Counter类"
        "（inference-node/app/__init__.py，23行），实时追踪当前节点的活跃推理连接数。"
        "该计数器提供increment()与decrement()两个异步方法，分别用于请求处理开始时递增"
        "和请求完成时递减，并通过asyncio.Lock确保并发场景下的计数准确性。计数器的value"
        "属性作为节点负载的量化指标，通过心跳机制上报至调度器，为最少连接策略和监控"
        "系统提供实时负载数据。"
    )

    # ── 4.4 Node Registration & Heartbeat ───────────────────────────────────
    add_heading2(doc, "4.4 节点注册与心跳机制")

    add_body_text(doc,
        "节点注册与心跳机制是系统实现自动化节点管理与故障感知的基础。推理节点启动后"
        "自动向调度器注册并持续发送心跳信号，调度器据此维护节点注册表并检测节点健康状态。"
    )

    add_heading3(doc, "4.4.1 自注册机制")

    add_body_text(doc,
        "推理节点在服务启动时通过register_self()异步函数（inference-node/app/heartbeat.py，"
        "11-34行）向调度器的POST /api/nodes/register端点发送注册请求，携带节点标识符"
        "（node_id）、主机地址（host）、服务端口（port）与权重值（weight）等信息。注册"
        "过程采用指数退避重试策略，最多尝试10次，退避时间按2的幂次递增（上限30秒），"
        "确保在调度器尚未就绪或网络暂时不可达的场景下仍能完成注册。若10次尝试均失败，"
        "节点将记录错误日志并以未注册状态继续运行，待后续心跳周期重新建立连接。"
    )

    add_heading3(doc, "4.4.2 心跳上报")

    add_body_text(doc,
        "注册完成后，推理节点启动心跳循环任务heartbeat_loop()（inference-node/app/"
        "heartbeat.py，37-54行），以10秒为固定间隔（由HEARTBEAT_INTERVAL_S配置）向调度器"
        "发送心跳信号。每次心跳请求通过POST /api/nodes/{node_id}/heartbeat端点上报当前"
        "节点的活跃连接数（active_connections）与运行状态（status），供调度器实时感知"
        "各节点的负载与健康情况。心跳循环在服务启动3秒后开始运行，留出必要的初始化时间。"
    )

    add_heading3(doc, "4.4.3 TTL驱逐与节点生命周期")

    add_body_text(doc,
        "调度器的节点注册表（scheduler/app/registry.py，93行）采用基于TTL（Time-To-Live）"
        "的驱逐机制检测故障节点。后台任务evict_stale()以5秒为扫描周期，计算每个节点的"
        "最后心跳时间与当前时间的差值，若超过配置的心跳超时阈值（HEARTBEAT_TIMEOUT_S，"
        "默认30秒），则将该节点状态标记为'unhealthy'。节点生命周期包含四个阶段："
        "register（注册上线） -> heartbeat（持续心跳） -> healthy/unhealthy/draining"
        "（状态流转） -> deregister（下线注销），形成完整的节点管理闭环。"
    )

    add_body_text(doc,
        "节点注册表NodeRegistry使用asyncio.Lock保护所有对内部节点字典的读写操作，"
        "确保多个并发请求（注册、心跳、查询、驱逐）下的数据一致性。健康节点筛选方法"
        "healthy_nodes()支持排除列表参数，与网关重试模块配合实现故障转移时的节点过滤。"
    )

    add_figure_placeholder(doc,
        "图4-4 节点生命周期状态机图",
        "节点状态机：register -> healthy <-> unhealthy -> draining -> deregister；healthy状态通过心跳维持，超时转为unhealthy，unhealthy节点收到心跳可恢复为healthy"
    )

    # ── 4.5 Monitoring & Alerting ───────────────────────────────────────────
    add_heading2(doc, "4.5 监控与告警系统")

    add_body_text(doc,
        "监控与告警系统为分布式推理集群提供全方位的可观测性能力，包含指标采集、时序存储、"
        "告警规则引擎与数据查询接口四个子系统，帮助运维人员实时掌握系统运行状态。"
    )

    add_heading3(doc, "4.5.1 指标采集器")

    add_body_text(doc,
        "指标采集器（monitoring/app/collector.py，84行）以后台异步任务形式运行，以15秒为"
        "采集间隔（SCRAPE_INTERVAL_S配置）拉取各服务的/metrics/json端点数据。采集目标"
        "包括Gateway与Scheduler两个固定服务，以及通过配置文件与动态发现获取的推理节点列表。"
        "动态节点发现机制在每次采集周期末尾，向调度器发送GET /api/nodes请求获取当前在线"
        "节点列表，将发现的节点URL缓存至_known_node_urls列表，下次采集时自动纳入采集范围。"
        "采集到的指标数据（QPS、延迟分位数、成功率、GPU利用率、显存用量等）写入SQLite"
        "数据库的metrics_snapshot表，每条记录包含数据源标识与时间戳。"
    )

    add_heading3(doc, "4.5.2 告警规则引擎")

    add_body_text(doc,
        "告警引擎（monitoring/app/alerts.py，81行）以15秒为评估周期，逐条检查数据库中"
        "已激活的告警规则。每条规则由四个要素构成：监控指标（metric，如latency_p95）、"
        "比较运算符（operator，支持gt/lt/eq）、阈值（threshold）与时间窗口（window_s）。"
        "评估时，引擎在指定时间窗口内查询metrics_snapshot表，计算目标指标的滑动窗口"
        "平均值，与阈值进行比较判定是否触发告警。"
    )

    add_body_text(doc,
        "为避免告警风暴，引擎实现了去重触发机制：在插入新告警记录前，先查询alert_history"
        "表中是否存在同一规则的未解决（resolved=0）告警，若存在则跳过插入，确保每条规则"
        "在解决前仅触发一次告警。告警记录包含触发时的实际指标值与格式化的告警消息，"
        "为运维人员提供精确的故障诊断信息。"
    )

    add_heading3(doc, "4.5.3 时序数据聚合与查询")

    add_body_text(doc,
        "监控模块（monitoring/app/routers/metrics.py，105行）提供了RESTful查询接口，"
        "支持按时间范围聚合查看历史指标数据。系统预定义了15m（15分钟）、1h（1小时）、"
        "6h（6小时）、24h（24小时）和7d（7天）五种查询范围，分别对应900至604800秒的"
        "时间窗口。时序数据采用按分钟分桶聚合策略，利用SQLite的strftime函数将时间戳"
        "截断至分钟精度后分组求均值，在保证数据趋势准确的前提下有效降低传输与渲染开销。"
        "接口返回包含聚合统计量与按分钟粒度的时间序列数据，供前端绘制实时趋势图。"
    )

    add_figure_placeholder(doc,
        "图4-5 监控告警系统架构图",
        "监控系统数据流：各服务/metrics/json -> Collector(15s拉取) -> SQLite(metrics_snapshot) -> 告警引擎(15s评估) -> alert_history；前端通过/api/metrics/summary查询时序数据"
    )

    # ── 4.6 Frontend Visualization ──────────────────────────────────────────
    add_heading2(doc, "4.6 前端可视化实现")

    add_body_text(doc,
        "系统前端基于Vue.js 3框架与Element Plus组件库构建，采用单页面应用（SPA）架构，"
        "为四个后端微服务分别提供独立的Web管理界面。四个前端应用分别为：Gateway管理端"
        "（提供Chat对话界面、请求历史查询与用户管理功能）、Scheduler管理端（提供节点管理、"
        "策略配置与调度日志查看功能）、Monitoring监控端（提供实时仪表盘、趋势图、节点对比"
        "与告警管理功能）以及Inference Node管理端（提供模型测试、节点状态与请求日志功能）。"
    )

    add_body_text(doc,
        "各前端应用的构建产物通过Vite打包后嵌入对应FastAPI服务的静态资源目录，利用"
        "FastAPI的StaticFiles中间件挂载/assets路径提供JS与CSS等静态资源服务。同时，"
        "各服务实现了SPA fallback路由：对于未匹配到静态文件的请求路径，统一返回"
        "index.html文件，将路由解析交由前端Vue Router处理，实现前端路由的HTML5 History"
        "模式支持。该部署策略避免了独立Web服务器的额外运维开销，实现了前后端一体化部署。"
    )

    add_figure_placeholder(doc,
        "图4-6 前端SPA部署架构图",
        "四套Vue.js 3 SPA架构：Gateway-SPA(Chat/用户管理) / Scheduler-SPA(节点/策略管理) / Monitoring-SPA(仪表盘/告警) / Inference-SPA(模型测试/状态) -- 各自嵌入对应FastAPI服务的static目录，SPA fallback路由支持前端路由"
    )

    add_page_break(doc)
