"""（五）经费使用情况"""
from report.styles import add_section_heading, add_body, add_table


def add_section5(doc):
    add_section_heading(doc, "（五）经费使用情况")

    add_body(doc, "本项目经费使用主要用于以下几个方面：")

    add_body(doc,
        "（1）计算资源：租赁GPU服务器用于模型推理实验和性能测试，包括本地NVIDIA GPU"
        "和远程Qwen2.5-7B推理服务器。"
    )
    add_body(doc, "（2）云服务：Docker镜像仓库、CI/CD流水线等云原生基础设施。")
    add_body(doc, "（3）文献资料：购买相关学术论文和技术书籍。")
    add_body(doc, "（4）其他：学术交流、论文打印等杂项支出。")

    add_table(doc,
        caption="表2 经费使用明细表",
        headers=["支出项目", "预算(元)", "已使用(元)", "用途说明"],
        rows=[
            ["GPU计算资源", "3000", "1500", "模型推理实验与性能测试"],
            ["云服务", "1000", "500", "容器镜像与CI/CD"],
            ["文献资料", "500", "300", "论文与技术书籍"],
            ["其他", "500", "200", "打印与交流"],
            ["合计", "5000", "2500", "—"],
        ],
    )
