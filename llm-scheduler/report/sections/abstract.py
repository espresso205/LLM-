"""Abstract section for Chinese academic mid-term report."""

from report.styles import (
    add_body_text, add_abstract_title,
    add_keyword_line, add_page_break,
)


def add_abstract(doc):
    """Add Chinese and English abstracts to the document."""

    # ── 中文摘要 ──────────────────────────────────────────────────────────────
    add_abstract_title(doc, "摘  要")

    add_body_text(doc,
        "近年来，以GPT-4、LLaMA为代表的大语言模型在自然语言处理领域取得了突破性进展，"
        "其参数规模已达数十亿至数千亿量级。然而，大语言模型的推理过程需要消耗大量GPU"
        "计算与显存资源，单节点部署难以满足高并发、低延迟的实际业务需求，GPU资源瓶颈与"
        "单节点扩展困难成为制约大语言模型规模化落地的核心问题。"
    )

    add_body_text(doc,
        "针对上述问题，本文设计并实现了基于微服务架构的大语言模型云原生分布式推理调度"
        "引擎。系统采用API网关模式统一请求入口并实现JWT身份认证与指数退避重试机制；设计"
        "集中式调度器管理推理节点生命周期；采用代理式推理节点对接vLLM推理框架，实现大语言"
        "模型的高效推理服务。在负载均衡方面，系统实现了轮询（Round Robin）、最少连接"
        "（Least Connections）和加权轮询（Weighted Round Robin）三种调度策略，并支持"
        "运行时热切换，可根据实际负载动态选择最优策略。"
    )

    add_body_text(doc,
        "在容错机制方面，系统采用基于心跳信号的健康监测机制，实时感知推理节点状态，当节点"
        "发生故障时自动触发故障转移，将请求调度至健康的推理节点，结合指数退避重试策略保障"
        "服务的连续性与可靠性。在可观测性方面，系统构建了实时监控模块，实现推理延迟、吞吐量、"
        "GPU利用率等关键指标的采集与可视化展示，并设计了可配置的告警规则引擎，支持阈值触发"
        "与等级划分的告警通知机制。"
    )

    add_body_text(doc,
        "最后，本文基于Docker容器化技术完成了系统的部署与测试，通过多组对比实验验证了系统"
        "的可用性、三种负载均衡策略的调度效果以及容错机制的有效性。实验结果表明，该系统能够"
        "有效提升GPU资源利用率，实现推理请求的合理分配，为大规模语言模型的工程化部署提供了"
        "可行的技术方案。"
    )

    add_keyword_line(doc, "大语言模型；分布式推理；负载均衡；微服务架构；云原生")

    # ── English Abstract ──────────────────────────────────────────────────────
    add_abstract_title(doc, "Abstract")

    add_body_text(doc,
        "In recent years, large language models (LLMs) represented by GPT-4 and LLaMA have achieved "
        "breakthrough progress in the field of natural language processing, with parameter scales "
        "reaching tens to hundreds of billions. However, the inference process of large language "
        "models demands substantial GPU computing and memory resources. Single-node deployment "
        "struggles to meet the practical requirements of high concurrency and low latency, making "
        "GPU resource bottlenecks and single-node scalability limitations the core challenges "
        "constraining the large-scale deployment of LLMs."
    )

    add_body_text(doc,
        "To address these challenges, this paper designs and implements a cloud-native distributed "
        "inference scheduling engine for large language models based on a microservice architecture. "
        "The system employs an API Gateway pattern to unify the request entry point, incorporating "
        "JWT authentication and an exponential backoff retry mechanism. A centralized scheduler is "
        "designed to manage the lifecycle of inference nodes, while proxy-based inference nodes "
        "interface with the vLLM inference framework to enable efficient LLM inference services. "
        "For load balancing, the system implements three scheduling strategies: Round Robin, Least "
        "Connections, and Weighted Round Robin, with runtime hot-swapping support for dynamic "
        "strategy selection based on actual workload conditions."
    )

    add_body_text(doc,
        "In terms of fault tolerance, the system adopts a heartbeat-based health monitoring mechanism "
        "to detect inference node status in real time. Upon node failure, automatic failover is "
        "triggered to redirect requests to healthy nodes, and the exponential backoff retry strategy "
        "ensures service continuity and reliability. Regarding observability, the system constructs "
        "a real-time monitoring module that collects and visualizes key metrics such as inference "
        "latency, throughput, and GPU utilization. A configurable alert rule engine is also designed, "
        "supporting threshold-triggered alert notifications with severity level classification."
    )

    add_body_text(doc,
        "Finally, the system is deployed and tested using Docker containerization technology. Multiple "
        "comparative experiments are conducted to validate the system's availability, the scheduling "
        "effectiveness of the three load balancing strategies, and the efficacy of the fault tolerance "
        "mechanisms. Experimental results demonstrate that the system effectively improves GPU resource "
        "utilization, achieves rational allocation of inference requests, and provides a viable "
        "technical solution for the engineering deployment of large-scale language models."
    )

    # English Keywords line
    add_body_text(doc, "Keywords: Large Language Model; Distributed Inference; Load Balancing; "
                       "Microservice Architecture; Cloud-Native", indent=False)

    add_page_break(doc)
