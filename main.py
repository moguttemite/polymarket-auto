# Polymarket 交易客户端示例
# 本文件演示如何使用 py_clob_client 在 Polymarket 上创建和提交订单

import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

# ==================== 配置参数 ====================

# Polymarket CLOB 服务器地址
host: str = "https://clob.polymarket.com"

# 私钥：从环境变量中读取，确保安全性
key: str = os.getenv("POLYMARKET_PRIVATE_KEY", "")  # 从环境变量读取私钥

# 链 ID：137 代表 Polygon 网络（Polymarket 使用的网络）
chain_id: int = 137  # 无需调整此值

# Polymarket 代理地址：在 Polymarket 网站上，您的个人资料图片下方列出的地址
POLYMARKET_PROXY_ADDRESS: str = os.getenv("POLYMARKET_PROXY_ADDRESS", "")  # 从环境变量读取代理地址

# ==================== 客户端初始化 ====================
# 根据您的登录方式，选择以下三种初始化客户端的方式之一，并删除未使用的行，确保仅初始化一个客户端。

# 1. 使用与 Email/Magic 账户关联的 Polymarket 代理进行客户端初始化
# 如果您使用电子邮件登录，请使用此示例
client = ClobClient(host, key=key, chain_id=chain_id, signature_type=1, funder=POLYMARKET_PROXY_ADDRESS)

# 2. 使用与浏览器钱包（如 Metamask、Coinbase Wallet 等）关联的 Polymarket 代理进行客户端初始化
# 如果您使用浏览器钱包登录，请使用此示例
# client = ClobClient(host, key=key, chain_id=chain_id, signature_type=2, funder=POLYMARKET_PROXY_ADDRESS)

# 3. 直接从 EOA（外部拥有账户）进行交易的客户端初始化
# 如果您直接使用钱包地址进行交易，请使用此示例
# client = ClobClient(host, key=key, chain_id=chain_id)

# ==================== 设置 API 凭证 ====================
# 创建或派生 API 凭证，用于与 Polymarket API 进行交互
client.set_api_creds(client.create_or_derive_api_creds())

# ==================== 创建订单 ====================
# 创建并签署一个限价订单，以每个 0.010 美分的价格购买 5 个代币
# 请参考 Markets API 文档以获取 tokenID：https://docs.polymarket.com/developers/gamma-markets-api/get-markets

order_args = OrderArgs(
    price=0.01,      # 每个代币的价格（以美元为单位）
    size=5.0,        # 购买的代币数量
    side=BUY,        # 订单方向：购买
    token_id=os.getenv("POLYMARKET_TOKEN_ID", ""),     # 要购买的代币的 Token ID，从环境变量读取
)

# 创建并签署订单
signed_order = client.create_order(order_args)

# ==================== 提交订单 ====================
# 提交 GTC（Good-Till-Cancelled，长期有效）订单到 Polymarket
# GTC 订单会一直保持活跃状态，直到被成交或手动取消
resp = client.post_order(signed_order, OrderType.GTC)

# 打印订单提交结果
print("订单提交结果：", resp)