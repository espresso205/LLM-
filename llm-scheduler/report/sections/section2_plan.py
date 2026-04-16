"""（二）项目研究内容及实施方案"""
from report.styles import add_section_heading, add_subheading, add_body, add_figure


def add_section2(doc):
    add_section_heading(doc, "（二）项目研究内容及实施方案")

    # ── 1. 研究内容 ────────────────────────────────────────────────────────────
    add_subheading(doc, "1. 研究内容")

    add_body(doc,
        "本项目以LLM分布式推理为研究对象，以云原生微服务架构为技术路线，设计并实现一个"
        "支持多策略负载均衡、自动故障转移和实时监控的分布式推理调度引擎。研究内容主要"
        "包括以下四个方面："
    )

    add_body(doc,
        "（1）分布式推理架构设计：采用微服务架构，将系统拆分为API网关（Gateway）、"
        "调度器（Scheduler）、推理节点（Inference Node）和监控服务（Monitoring）四个"
        "核心服务，通过RESTful API进行服务间通信，使用统一Pydantic数据模型（20余个Schema）"
        "实现跨服务数据校验，实现松耦合的系统设计。"
    )

    add_body(doc,
        "（2）多策略负载均衡调度：设计并实现轮询（Round Robin）、最少连接（Least Connections）"
        "和加权轮询（Weighted Round Robin）三种负载均衡策略，采用策略模式（Strategy Pattern）"
        "实现策略的运行时热切换，满足不同负载场景下的调度需求。"
    )

    add_body(doc,
        "（3）容错与高可用机制：基于心跳机制实现节点健康监测，当节点故障时自动将其标记为不可用"
        "并将请求路由到健康节点；在网关层实现带指数退避的重试机制（最多3次重试，等待时间按"
        "0.1×2^n秒递增），确保请求的可靠处理。"
    )

    add_body(doc,
        "（4）可观测性体系构建：实现轻量级的指标采集与告警系统，以15秒间隔采集各服务的QPS、"
        "延迟、成功率等关键指标，支持基于规则的可配置告警；同时集成Prometheus+Grafana监控"
        "栈，提供更丰富的可视化能力。"
    )

    # ── 2. 实施方案 ────────────────────────────────────────────────────────────
    add_subheading(doc, "2. 实施方案")

    add_body(doc,
        "项目采用Python技术栈，后端基于FastAPI框架构建异步RESTful服务，数据模型使用Pydantic"
        "进行统一校验，持久化层采用SQLite WAL模式配合aiosqlite异步驱动。推理节点通过HTTP代理"
        "对接vLLM推理引擎，支持OpenAI兼容的/v1/chat/completions接口。前端采用Vue.js 3 "
        "+ Element Plus构建四套独立管理界面。部署方面，采用Docker Compose进行多容器编排，"
        "并配置Prometheus+Grafana监控栈。整体实施路线为：需求分析与架构设计→核心模块开发→"
        "前端界面开发→集成测试→性能优化→文档撰写。"
    )

    add_figure(doc, caption="图1 系统总体架构图", desc="系统总体架构示意图")
