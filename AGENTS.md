# Repository Guidelines

## 项目结构与模块组织
仓库入口位于 `main.py`，展示如何使用 `py_clob_client` 在 Polymarket 下单。
可复用逻辑请放入 `src/`，建议按照职责拆分如 `src/clients/`（API 封装）与 `src/services/`（策略与业务流程）。
图表、流程文档等资料放入 `docs/`。
自动化测试统一置于 `test/`，并与运行时代码同名映射，例如 `src/services/order_flow.py` 对应 `test/test_order_flow.py`。

## 开发本系统主要使用的的py包，py-clob-client：
py-clob-client包的源码参考资料在 "py_package/py-clob-client" 文件夹下
py-clob-client的安装之类为 "pip install py-clob-client"

## 构建、测试与开发命令
使用 Python 3.14 anaconda虚拟环境：`conda activate polymarket`。

## 代码风格与命名约定
遵循 PEP 8，保持 4 空格缩进，函数与变量使用蛇形命名（`snake_case`），测试文件命名为 `test_*.py`。尽量补充类型标注以提升可读性，并对调用外部服务的关键函数写简短文档字符串。提交前运行 `black .`（88 字符行宽）与 `isort` 整理格式，同时确保注释聚焦在业务背景或外部接口假设。

## 文件实现

## 测试指引
统一使用 `pytest` 编写用例，共享准备逻辑可放在 `test/conftest.py`。建议每个运行模块配套一个测试模块，并按行为命名测试函数，如 `test_create_order_handles_invalid_price()`。对 Polymarket 的网络调用应通过 mock 隔离，保证离线可执行；重要路径需覆盖至少一个异常或失败场景，重点关注签名方式选择和凭证加载逻辑。

## 提交与合并请求规范
提交消息保持简洁、使用祈使句，可参考 `type: 简述` 格式（例如 `feat: 添加下注订单构建器`）。将同一逻辑修改放在单个提交中，便于回溯。发起 Pull Request 时需概述改动、列出本地或 CI 测试结果，并关联相关 issue；如涉及命令行交互变化，请附上示例输出或截图以便评审。

## 安全与配置提示
严禁将真实私钥或代理地址硬编码在仓库内；请使用环境变量（如 `export POLY_KEY=0x...`），代码中通过 `os.getenv` 读取。将 `.env` 等本地配置加入 `.gitignore`，并定期轮换自动化测试使用的凭证，避免泄露或过期。
