## Polymark 预测市场自动操作

### 关于Polymark的相关资料
官方X/twitter：https://x.com/Polymarket

官网：https://polymarket.com/

官方资料：https://docs.polymarket.com/polymarket-learn/get-started/what-is-polymarket

### 关于工程的设计构想
1. 获取当前的预测市场都有哪些预测条目
2. 通过AI分析每个预测条目的可行性（时间短-胜率可能性高）
3. 通过API接口，对所选定的条目进行开单
    a. 先检测市场网站的连接性是否稳定
    b. 检测余额是否充足
    c. 开单